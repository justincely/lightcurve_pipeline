#! /usr/bin/python

"""Download all COS & STIS TIMETAG data that do not already exist in the hstlc
filesystem/database.

This script retreives COS & STIS TIMETAG data from the MAST archive by
submitting XML requests.  The datasets to download is determined by
comparing the contents of the hstlc database to the contents of the
MAST database; any COS/STIS TIMETAG data that exists in MAST but does
not exist in the hstlc database is retreived.  Data is downloaded to
the 'ingest_dir' directory determine by the config file (see below).

Authors:
    Matthew Bourque, 2015

Use:
    This script is intended to be executed via the command line as
    such:

    >>> download_hstlc

    The script can also be placed into a cron job for periodic
    execution.

Outputs:
    The following filetypes are retreived (if available) and placed
    in the 'ingest_dir' directory:

    *_x1d.fits - 1 dimensional extracted spectra
    *_tag.fits - STIS TIMETAG data
    *_corrtag.fits - COS NUV TIMETAG data
    *_corrtag_<a or b>.fits - COS FUV TIMETAG data

    Submission results are also saved to an XML file and stored in the
    'download_dir' directory determined by the config file (see below).
    The submission results indicate if the XML request was sucessful or
    if there were errors.

    Executing this script creates a log file in the 'log_dir' directory
    as determined by the config file (see below).

Dependencies:
    As of early 2016, submission of XML requests to the MAST archive
    requires a special Python 2.6 environemnt with specific XML
    libraries installed.  More information can be found here:

    https://confluence.stsci.edu/display/STScISSOPublic/ArchiveXMLsubmitPKImaterial

    Additionally, tsql must be installed and the tsql executable must
    be placed in the directory ~/freetds/bin/tsql.  tsql can be
    downloaded using freetds (http://www.freetds.org/).

    Users must have access to the hstlc database.

    Users must also have a config.yaml file located in the
    lightcurve_pipeline/utils/ directory with the following keys:

    (1) db_connection_string - The hstlc database connection string
    (2) ingest_dir - The path to where the files will be stored after
        retreival
    (3) log_dir - The path to where the log file will be stored
    (4) download_dir - the path to where XML submission results will be
        stored
    (5) mast_server - The MAST server hostname
    (6) mast_database - The name of the MAST database
    (7) mast_account - The MAST account username
    (8) mast_password - The MAST account password
    (9) archive_user - The requester username
    (10) email - the requester email address
    (11) host - The hostname of the machine used for ftp
    (12) ftp_user - The username of the account of the machine used for
         ftp
    (13) dads_host - The hostname of the machine on which the MAST
         database resides
    (14) archive - The HTTPs connection hostname

    Other external library dependencies include:
        lightcurve_pipeline
"""

import glob
import datetime
import httplib
import logging
import os
import string
import urllib

from lightcurve_pipeline.download.SignStsciRequest import SignStsciRequest

from lightcurve_pipeline.utils.utils import SETTINGS
from lightcurve_pipeline.utils.utils import set_permissions
from lightcurve_pipeline.utils.utils import setup_logging
from lightcurve_pipeline.database.database_interface import engine
from lightcurve_pipeline.database.database_interface import session
from lightcurve_pipeline.database.database_interface import BadData
from lightcurve_pipeline.database.database_interface import Metadata

REQUEST_TEMPLATE = string.Template('\
<?xml version="1.0"?>\
 <!DOCTYPE distributionRequest SYSTEM "http://dmswww.stsci.edu/dtd/sso/distribution.dtd">\n\
   <distributionRequest Id=\'distributionRequest\'>\n\
     <head>\n\
       <requester userId="$archive_user" email="$archiveUserEmail"  source="starview"/>\n\
       <delivery>\n\
         <ftp hostName= "$ftpHost" loginName="$ftpUser" directory="$ftpDir" secure="true"/>\n\
       </delivery>\n\
       <process compression="none"/> \n\
     </head>\n\
     <body>\n\
       <include>\n\
         <select>\n\
           <suffix name=\"X1D\" />\n\
           <suffix name=\"TAG\" />\n\
           <suffix name=\"CTG\" />\n\
           <suffix name=\"CTA\" />\n\
           <suffix name=\"CTB\" />\n\
        </select> \n\
        $datasets \n\
       </include>\n\
     </body>\n\
   </distributionRequest>\n')

# -----------------------------------------------------------------------------

def build_xml_request(datasets):
    """Build the XML request for the given datasets

    Parameters
    ----------
    datasets : list
        A list of rootnames to download from MAST.

    Returns
    -------
    xml_request : string
        The XML request string.
    """

    # The list of datasets must be one string
    datasets = ''.join(['<rootname>{0}</rootname>\n'.format(rootname) for rootname in datasets])

    request_string = REQUEST_TEMPLATE.safe_substitute(
        archive_user=SETTINGS['archive_user'],
        archiveUserEmail=SETTINGS['email'],
        ftpHost=SETTINGS['host'],
        ftpDir=SETTINGS['ingest_dir'],
        ftpUser=SETTINGS['ftp_user'],
        datasets=datasets)

    xml_request = string.Template(request_string)
    xml_request = xml_request.template

    return xml_request

# -----------------------------------------------------------------------------

def get_filesystem_rootnames():
    """Return a list of the rootnames in the hstlc database.

    This list is compared to the MAST database to determine which
    datasets to download.

    Returns
    -------
    filesystem_rootnames : list
        A list of rootnames that are in the hstlc filesystem.
    """

    filesystem = session.query(Metadata.filename).all()
    filesystem_rootnames = [item[0].split('_')[0] for item in filesystem]

    return filesystem_rootnames

# -----------------------------------------------------------------------------

def get_mast_rootnames():
    """Return a list of rootnames of all COS & STIS TIMETAGE data in
    MAST.

    The following target names are ignored:
        DARK
        BIAS
        DEUTERIUM
        WAVE
        ANY
        NONE

    Returns
    -------
    mast_rootnames : list
        A list of rootnames of COS/STIS TIMETAG data in the MAST
        archive.
    """

    # Gather configuration settings
    mast_server = SETTINGS['mast_server']
    mast_database = SETTINGS['mast_database']
    mast_account = SETTINGS['mast_account']
    mast_password = SETTINGS['mast_password']

    # Build comparison date
    today = datetime.datetime.utcnow()
    today = today.strftime('%Y-%m-%d')

    # Connect to server
    transmit, receive = os.popen2("~/freetds/bin/tsql -S {0} -D '{1}' -U '{2}' -P '{3}' -t '|'".format(mast_server, mast_database, mast_account, mast_password))

    # Build query
    query = ("SELECT sci_data_set_name "
             "FROM science "
             "WHERE (sci_instrume = 'COS' OR sci_instrume = 'STIS') "
             "AND sci_operating_mode = 'TIME-TAG' "
             "AND sci_release_date < '{0}' "
             "AND sci_targname NOT IN ('DARK', 'BIAS', 'DEUTERIUM', 'WAVE', 'ANY', 'NONE') "
             "\ngo\n".format(today))
    print query

    # Perform query and capture results
    transmit.write(query)
    transmit.close()
    mast_results = receive.readlines()
    receive.close()

    # Prune mast_results of unwanted information
    mast_results = mast_results[7:-2]
    mast_rootnames = [item.lower().strip() for item in mast_results]

    return mast_rootnames

# -----------------------------------------------------------------------------

def save_submission_results(submission_results):
    """Save the submission results to an XML file.

    Submission results are saved in a separate XML file and stored in
    the 'download_dir' directory as determine by the config file.

    Parameters
    ----------
    submission_results : httplib object
        The submission results returned by MAST after the XML request
        is submitted.
    """

    today = datetime.datetime.strftime(datetime.datetime.now(), '%Y_%m_%d')
    xml_filename = 'result_{0}.xml'.format(today)
    xml_output_file = os.path.join(SETTINGS['download_dir'], xml_filename)
    with open(xml_output_file, 'w') as f:
        f.write(submission_results)
    set_permissions(xml_output_file)
    logging.info('\tXML file saved to: {0}'.format(xml_output_file))

# -----------------------------------------------------------------------------

def submit_xml_request(xml_request):
    """Submit the XML request to the MAST archive.

    Parameters
    ----------
    xml_request : string
        The request XML string.

    Returns
    -------
    submission_results : httplib object
        The XML request submission results.
    """

    user = os.environ.get("USER")
    home = os.environ.get("HOME")

    signer = SignStsciRequest()
    request_xml_str = signer.signRequest('{0}/.ssh/privkey.pem'.format(home), xml_request)
    params = urllib.urlencode({
        'dadshost': SETTINGS['dads_host'],
        'dadsport': 4703,
        'mission':'HST',
        'request': request_xml_str})
    headers = {"Accept": "text/html", "User-Agent":"{0}PythonScript".format(user)}
    req = httplib.HTTPSConnection(SETTINGS['archive'])
    req.request("POST", "/cgi-bin/dads.cgi", params, headers)
    response = req.getresponse().read()
    req.close()

    return response

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------

def main():

    # Set up logging
    module = os.path.basename(__file__).strip('.py')
    setup_logging(module)

    # Build list of files in filesystem
    filesystem_rootnames = set(get_filesystem_rootnames())
    logging.info('{0} rootnames in filesystem.'.format(len(filesystem_rootnames)))

    # Query MAST for datasets
    mast_rootnames = set(get_mast_rootnames())
    logging.info('{0} rootnames in MAST.'.format(len(mast_rootnames)))

    # Compare lists
    files_to_download = mast_rootnames - filesystem_rootnames
    logging.info('{0} new rootnames.'.format(len(files_to_download)))

    # Remove bad data rootnames
    bad_rootnames = session.query(BadData.filename).all()
    bad_rootnames = set([item[0][0:9] for item in bad_rootnames])
    files_to_download = files_to_download - bad_rootnames

    # Remove rootnames that already exist in ingest queue
    files_in_ingest = glob.glob(os.path.join(SETTINGS['ingest_dir'], '*_corrtag.fits'))
    files_in_ingest.extend(glob.glob(os.path.join(SETTINGS['ingest_dir'], '*_corrtag_?.fits')))
    files_in_ingest.extend(glob.glob(os.path.join(SETTINGS['ingest_dir'], '*_tag.fits')))
    rootnames_in_ingest = set([os.path.basename(item).split('_')[0] for item in files_in_ingest])
    files_to_download = files_to_download - rootnames_in_ingest

    # Limit number of requests to 100
    if len(files_to_download) > 100:
        files_to_download = list(files_to_download)[0:100]

    # Build XML request
    logging.info('Building XML request.')
    xml_request = build_xml_request(files_to_download)

    # Send request
    logging.info('Submitting XML request.')
    submission_results = submit_xml_request(xml_request)

    # Save submission results
    save_submission_results(submission_results)

# -----------------------------------------------------------------------------

if __name__ == '__main__':

    main()
