#! /usr/bin/env python

"""
This script performs the main ingestion of data into the hstlc
filesystem and database, as well as creates output lightcurves for both
individual observations as well as 'composite' (i.e. aggregate)
observations of the same target. This script employs the following
algorithm:

    1. Configure logging
    2. Parse command line arguments
    3. Gather ``*_x1d.fits``, ``*_tag.fits``, ``*_corrtag.fits``,
       ``*_corrtag_a.fits``, and ``*_corrtag_b.fits`` files from the
       ``ingest_dir`` directory, as determined by the config file (see
       below):
        a. If both a ``*_corrtag_a.fits`` and a ``*_corrtag_b.fits``
        file exists for a given dataset, ignore the
        ``*_corrtag_b.fits`` file (as to avoid redundant extraction).
    4. For each dataset to ingest:
        a. Perform data quality checks.  If the dataset is deemed bad:
            i. Update the ``bad_data`` table in database
            ii. Remove dataset
        b. Gather metadata
        c. If dataset is a STIS dataset:
            i. Extract spectra
            ii. Rename ``*_tag.fits`` to ``*_corrtag.fits``
        d. If dataset is a COS dataset:
            i. Extract spectra (both ``*_corrtag_a.fits`` and
            ``*_corrtag_b.fits``, if necessary)
        e. Update ``metadata`` table in database
        f. Create lightcurve
        g. Update ``outputs`` table in database
        h. Create `quicklook' image
        i. Move file to appropriate location in filesystem
    5. Create composite lightcurve for each dataset in unique
       detector-targname-opt_elem-cenwave configuration

The filenames and headers of the composite lightcurves are configured
such that they can be delivered to MAST as High Level Science Products
(HLSPs), though not all composite lightcurves are delivered.

This script uses multiprocessing.  Users can set the number of cores
used via the ``num_cores`` setting in the config file (see below)


**Authors:**

    Matthew Bourque, Justin Ely

**Use:**

    This script is intended to be executed as part of the
    ``hstlc_pipeline`` shell script.  However, users can also execute
    this script via the command line as such:

    >>> ingest_hstlc [-corrtag_extract]

    ``-corrtag_extract`` (*optional*) - (Re)extract corrtag data as it
    is ingested, if provided

**Outputs:**

    (1) New and/or updated entries in the ``metadata``, ``outputs``,
        and ``bad_data`` tables in the hstlc database
    (2) ``x1d``, ``tag``, and ``corrtag`` files are moved from the
        ``ingest_dir`` directory to the appropriate directory in the
        ``filesystem_dir`` directory, as determined by the config file
        (see below)
    (3) ``*_curve.fits`` lightcurves for individual observations,
        placed in the appropriate ``output_dir`` directory as
        determined by the config file (see below)
    (4) ``hlsp_hstlc_*.fits`` lightcurves for composite observations,
        placed in the ``composite_dir`` directory , as determined by
        the config file (see below)
    (5) a log file in the ``log_dir`` directory as determined by the
        config file (see below)

**Dependencies:**

    (1) Users must have access to the hstlc database
    (2) Users must also have access to the cdbs ``lref`` and ``oref``
        directories, which hold COS and STIS reference files,
        respectively
    (3) Users must also have a ``config.yaml`` file located in the
        ``lightcurve_pipeline/utils/`` directory with the following
        keys:

        - ``db_connection_string`` - The hstlc database connection
          string
        - ``ingest_dir`` - The path to where files to be ingested are
          stored
        - ``filesystem_dir`` - The path to the hstlc filesystem
        - ``outputs_dir`` - The path to where hstlc output products are
          stored
        - ``composite_dir`` - The path to where hstlc composite output
          products are stored.
        - ``log_dir`` - The path to where the log file will be stored
        - ``num_cores`` - The number of cores to use during
          multiprocessing

    Other external library dependencies include:
        - ``astropy``
        - ``lightcurve``
        - ``lightcurve_pipeline``
        - ``pymysql``
        - ``matplotlib``
        - ``sqlalchemy``
"""

import argparse
import datetime
import glob
import itertools
import logging
import multiprocessing
import os
import shutil
import traceback

from astropy.io import fits
import lightcurve

from lightcurve_pipeline.utils.utils import make_directory
from lightcurve_pipeline.utils.utils import SETTINGS
from lightcurve_pipeline.utils.utils import set_permissions
from lightcurve_pipeline.utils.utils import setup_logging
from lightcurve_pipeline.database.update_database import update_metadata_table
from lightcurve_pipeline.database.update_database import update_outputs_table
from lightcurve_pipeline.ingest.make_lightcurves import make_composite_lightcurves
from lightcurve_pipeline.ingest.make_lightcurves import make_individual_lightcurve
from lightcurve_pipeline.ingest.resolve_target import get_targname
from lightcurve_pipeline.quality.data_checks import dataset_ok

# Use matplotlib backend for quicklook images
import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt

# Set CRDS environement for reference files
os.environ['lref'] = '/grp/hst/cdbs/lref/'
os.environ['oref'] = '/grp/hst/cdbs/oref/'

# -----------------------------------------------------------------------------

def get_files_to_ingest():
    """
    Return a list of files to ingest.  Since ``corrtag_a`` and
    ``corrtab_b`` files are extracted together, the returned list must
    be void of duplicate ``corrtag`` files in order to avoid double
    extraction

    Returns
    -------
    files_to_ingest : list
        A list of full paths to files to ingest
    """

    logging.info('')
    logging.info('Gathering files to ingest')

    # Determine which files are corrtag_a or corrtag_b files
    files_to_ingest = glob.glob(os.path.join(SETTINGS['ingest_dir'], '*tag*.fits'))
    corrtag_ab_files = [item for item in files_to_ingest if 'corrtag_' in os.path.basename(item)]
    files_to_remove = []

    # Check to see if both a corrtag_a and corrtag_b file exists for a given rootname
    for corrtag_file in corrtag_ab_files:
        corrtag_dirname = os.path.dirname(corrtag_file)
        corrtag_rootname = os.path.basename(corrtag_file).split('_')[0]
        corrtag_a_file = '{}/{}_corrtag_a.fits'.format(corrtag_dirname, corrtag_rootname)
        corrtag_b_file = '{}/{}_corrtag_b.fits'.format(corrtag_dirname, corrtag_rootname)
        if os.path.exists(corrtag_a_file) and os.path.exists(corrtag_b_file):
            files_to_remove.append(corrtag_b_file)

    # If both a corrtag_a and a corrtag_b file exists, remove the corrtag_b
    for file_to_remove in set(files_to_remove):
        files_to_ingest.remove(file_to_remove)

    return files_to_ingest

# -----------------------------------------------------------------------------

def ingest(mp_args):
    """Ingests the file into the hstlc filesystem and database. Also
    produces output lightcurves

    Parameters
    ----------
    mp_args : tuple
        The multiprocessing arguments.  The zeroth value is the
        filename (i.e. the file to ingest), and the first value is the
        corrtag_extract switch (i.e. turn on/off stis corrtag
        re-extraction)
    """

    # Parse multiprocessing args
    filename = mp_args[0]
    corrtag_extract = mp_args[1]

    try:

        logging.info('Ingesting {}'.format(filename))

        # Open file
        with fits.open(filename, 'readonly') as hdulist:
            header = hdulist[0].header

            # Check that quality of the file before ingesting
            success = dataset_ok(filename)

            # Ingest the data if it is ok
            if success:
                metadata_dict, outputs_dict = make_file_dicts(filename, header)

                # If the file is a _tag STIS file, then make a corrtag
                if metadata_dict['instrume'] == 'STIS' and '_tag.fits' in filename:
                    lightcurve.stis.stis_corrtag(filename)
                    new_filename = filename.replace('_tag.fits', '_corrtag.fits')
                    metadata_dict['filename'] = os.path.basename(new_filename)

                # If the file is a corrtag STIS file, then re-extract if corrtag_extract is on
                elif metadata_dict['instrume'] == 'STIS' and '_corrtag.fits' in filename and corrtag_extract:
                    lightcurve.stis.stis_corrtag(filename)

                update_metadata_table(metadata_dict)

                success = make_individual_lightcurve(metadata_dict, outputs_dict)
                if success:
                    update_outputs_table(metadata_dict, outputs_dict)
                    #make_quicklook(outputs_dict)

                # Move file into the hstlc filesystem
                move_file(metadata_dict)

    # Track any errors that happen during processing
    except Exception as error:
        trace = 'Failed to ingest {}\n{}'.format(filename, traceback.format_exc())
        logging.critical(trace)

# -----------------------------------------------------------------------------

def make_file_dicts(filename, header):
    """Return a dictionary containing file metadata and a dictionary
    containing output product information

    Parameters
    ----------
    filename : string
        The absolute path to the file
    header : astropy.io.fits.header.Header
        The primary header of the file

    Returns
    -------
    metadata_dict : dict
        A dictionary containing metadata of the file
    outputs_dict : dict
        A dictionary containing output product information
    """

    metadata_dict = {}
    outputs_dict = {}

    # Set header keys
    metadata_dict['telescop'] = header['TELESCOP']
    metadata_dict['instrume'] = header['INSTRUME']
    metadata_dict['targname'] = get_targname(header['TARGNAME'])
    metadata_dict['cal_ver'] = header['CAL_VER']
    metadata_dict['obstype'] = header['OBSTYPE']
    metadata_dict['aperture'] = header['APERTURE']
    metadata_dict['detector'] = header['DETECTOR']
    metadata_dict['opt_elem'] = header['OPT_ELEM']

    # cenwave should be set to 0 for IMAGING OBSTYPE
    if header['OBSTYPE'] == 'SPECTROSCOPIC':
        metadata_dict['cenwave'] = header['CENWAVE']
    elif header['OBSTYPE'] == 'IMAGING':
        metadata_dict['cenwave'] = 0

    # fppos should be set to 0 for STIS data
    if header['INSTRUME'] == 'COS':
        metadata_dict['fppos'] = header['FPPOS']
    elif header['INSTRUME'] == 'STIS':
        metadata_dict['fppos'] = 0

    # Set image metadata keys
    metadata_dict['filename'] = os.path.basename(filename)
    metadata_dict['path'] = os.path.join(SETTINGS['filesystem_dir'], metadata_dict['targname'])
    metadata_dict['ingest_date'] = datetime.datetime.strftime(datetime.datetime.today(), '%Y-%m-%d')

    # Set outputs keys
    outputs_dict['individual_path'] = metadata_dict['path'].replace('filesystem', 'outputs')
    outputs_dict['individual_filename'] = '{}_curve.fits'.format(metadata_dict['filename'].split('_')[0])

    return metadata_dict, outputs_dict

# -----------------------------------------------------------------------------

def make_quicklook(outputs_dict):
    """Make a quicklook PNG of the lightcurve

    Parameters
    ----------
    outputs_dict : dict
        A dictionary containing output product information
    """

    lc_name = os.path.join(outputs_dict['individual_path'], outputs_dict['individual_filename'])
    lightcurve.io.quicklook(lc_name)
    set_permissions(lc_name.replace('.fits', '.png'))

# -----------------------------------------------------------------------------

def move_file(metadata_dict):
    """Move the file (and it's accompanying ``x1d`` file) from the
    ingest directory into the filesystem.  The parent directory to the
    ile is named afer the file's ``TARGNAME``

    Parameters
    ----------
    metadata_dict : dict
        A dictionary containing metadata of the file
    """

    # Create parent directory if necessary
    make_directory(metadata_dict['path'])

    # Move the file from ingest directory into filesystem
    src = os.path.join(SETTINGS['ingest_dir'], metadata_dict['filename'])

    # If the file is a corrtag_a/b file, then move any accompanying corrtag
    # file.  If not, move the file nominally
    src_list = []
    dst_list = []
    if 'corrtag_' in src:
        filelist = lightcurve.cos.get_both_filenames(src)
        for filename in filelist:
            src_list.append(filename)
            dst_list.append(os.path.join(metadata_dict['path'], os.path.basename(filename)))
    else:
        src_list.append(src)
        dst_list.append(os.path.join(metadata_dict['path'], metadata_dict['filename']))
    for src, dst in zip(src_list, dst_list):
        if os.path.exists(dst):
            os.remove(dst)
        if os.path.exists(src):
            shutil.move(src, dst)

    # Move the accompanying x1d file from ingest directory to filesystem
    x1d_file = '{}_x1d.fits'.format(metadata_dict['filename'].split('_')[0])
    src = os.path.join(SETTINGS['ingest_dir'], x1d_file)
    dst = os.path.join(metadata_dict['path'], x1d_file)
    if os.path.exists(src):
        if os.path.exists(dst):
            os.remove(dst)
        shutil.move(src, dst)

# -----------------------------------------------------------------------------
# ----------------------------------------------------------------------------

def parse_args():
    """Parse command line arguments. Returns ``args`` object

    Returns
    -------
    args : argparse.Namespace object
        An argparse object containing all of the added arguments
    """

    # Create help strings
    corrtag_extract_help = 'If provided, STIS corrtag re-extraction is performed.'

    # Add arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('-corrtag_extract',
        dest='corrtag_extract',
        action='store_true',
        help=corrtag_extract_help)

    # Set the defaults
    parser.set_defaults(corrtag_extract=False)

    # Parse args
    args = parser.parse_args()

    return args

# -----------------------------------------------------------------------------

def main():
    """The main function of the ``ingest_hstlc`` script
    """

    # Configure logging
    module = os.path.basename(__file__).strip('.py')
    setup_logging(module)

    # Parse arguments
    args = parse_args()

    # Get list of files to ingest
    files_to_ingest = get_files_to_ingest()

    # Ingest the files using multiprocessing
    logging.info('')
    logging.info('Ingesting {} files using {} core(s)'.format(len(files_to_ingest), SETTINGS['num_cores']))
    logging.info('')
    pool = multiprocessing.Pool(processes=SETTINGS['num_cores'])
    mp_args = itertools.izip(files_to_ingest, itertools.repeat(args.corrtag_extract))
    pool.map(ingest, mp_args)
    pool.close()
    pool.join()

    # Make composite lightcurves
    make_composite_lightcurves()

    logging.info('Processing complete.')

# -----------------------------------------------------------------------------

if __name__ == '__main__':

    main()
