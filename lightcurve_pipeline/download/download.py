#! /usr/bin/env python

import datetime
import httplib
import os
import string
import urllib

from lightcurve_pipeline.download.SignStsciRequest import SignStsciRequest

from lightcurve_pipeline.settings.settings import SETTINGS
from lightcurve_pipeline.settings.settings import set_permissions
from lightcurve_pipeline.database.database_interface import engine
from lightcurve_pipeline.database.database_interface import session
from lightcurve_pipeline.database.database_interface import BadData
from lightcurve_pipeline.database.database_interface import Metadata
from lightcurve_pipeline.database.database_interface import Outputs

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
           <suffix name=\"*\" />\n\
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

    request_string = REQUEST_TEMPLATE.safe_substitute(
        archive_user=SETTINGS['archive_user'],
        archiveUserEmail=SETTINGS['email'],
        ftpHost=SETTINGS['host'],
        ftpDir=SETTINGS['ingest_dir'],
        fptUser=SETTINGS['ftp_user'],
        datasets=datasets)

    xml_request = string.Template(request_string)
    xml_request = xml_request.template

    return xml_request

# -----------------------------------------------------------------------------

def get_filesystem_rootnames():
    """Return a list of the rootnames in the hstlc filesystem.

    Returns
    -------
    filesystem_rootnames : list
        A list of rootnames that are in the hstlc filesystem.
    """

    filesystem = session.query(Metadata.filename, Metadata.instrume).all()
    filesystem_rootnames = [item[0].split('_')[0] for item in filesystem \
        if item[1] == 'STIS']
    filesystem_rootnames.extend([item[0].split('_')[0] for item in filesystem \
        if item[1] == 'COS'])

    return filesystem_rootnames

# -----------------------------------------------------------------------------

def get_mast_rootnames():
    """Return a list of rootnames of all COS/STIS data in MAST.

    Returns
    -------
    mast_rootnames : list
        A list of rootnames of COS/STIS data in the MAST archive.
    """

    # Gather configuration settings
    mast_server = SETTINGS['mast_server']
    mast_database = SETTINGS['mast_database']
    mast_account = SETTINGS['mast_account']
    mast_password = SETTINGS['mast_password']

    # Connect to server
    transmit, receive = os.popen2("~/freetds/bin/tsql -S {} -D '{}' -U '{}' -P '{}' -t '|'".format(mast_server, mast_database, mast_account, mast_password))

    # Build query
    query = ("SELECT ads_data_set_name "
             "FROM archive_data_set_all "
             "WHERE ads_instrument = 'STIS' "
             "OR ads_instrument = 'COS'"
             "\ngo\n")

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

    Parameters
    ----------
    submission_results : httplib object
        The submission results returned by MAST after the XML request
        is submitted.
    """

    today = datetime.datetime.strftime(datetime.datetime.now(), '%Y_%m_%d')
    xml_filename = 'result_{}.xml'.format(today)
    xml_output_file = os.path.join(SETTINGS['download_dir'], xml_filename)
    with open(xml_output_file, 'w') as f:
        f.write(submission_results)
    set_permissions(xml_output_file)
    logging.info('\tXML file saved to: {}'.format(xml_output_file))

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
    request_xml_str = signer.signRequest('{}/.ssh/privkey.pem'.format(home), xml_file)
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

if __name__ == '__main__':

    # Build list of files in filesystem
    filesystem_rootnames = set(get_filesystem_rootnames())
    print '{} rootnames in filesystem'.format(len(filesystem_rootnames))

    # Query MAST for datasets
    mast_rootnames = set(get_mast_rootnames())
    print '{} rootnames in MAST'.format(len(mast_rootnames))

    # Compare lists
    files_to_download = mast_rootnames - filesystem_rootnames
    print '{} new rootnames'.format(len(files_to_download))

    # Build XML request
    xml_request = build_xml_request(files_to_download)
    print xml_request

    # Send request
    #submission_results = submit_xml_request(xml_request)

    # Save submission results
    save_submission_results(submission_results)
