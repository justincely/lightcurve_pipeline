"""Ingestion script to move files into hstlc filesystem and update the
hstlc database.
"""

from __future__ import print_function

import datetime
import glob
import os

from astropy.io import fits

from lightcurve_pipeline.settings.settings import SETTINGS
from lightcurve_pipeline.database.database_interface import engine
from lightcurve_pipeline.database.database_interface import session
from lightcurve_pipeline.database.database_interface import Metadata

# -----------------------------------------------------------------------------

def make_file_dict(filename):
    """Return a dictionary containing file metadata.

    Parameters
    ----------
    filename : string
        The absolute path to the file.

    Returns
    -------
    file_dict : dict
        A dictionary containing metadata of the file.
    """

    file_dict = {}

    # Open image
    with fits.open(filename, 'readonly') as hdulist:
        header = hdulist[0].header

    # Set header keys
    file_dict['telescop'] = header['TELESCOP']
    file_dict['instrume'] = header['INSTRUME']
    file_dict['targname'] = header['TARGNAME']
    file_dict['cal_ver'] = header['CAL_VER']
    file_dict['obstype'] = header['OBSTYPE']
    file_dict['aperture'] = header['APERTURE']
    file_dict['detector'] = header['DETECTOR']
    file_dict['opt_elem'] = header['OPT_ELEM']

    if header['OBSTYPE'] == 'SPECTROSCOPIC':
        file_dict['cenwave'] = header['CENWAVE']
    elif header['OBSTYPE'] == 'IMAGING':
        file_dict['cenwave'] = 0

    if header['INSTRUME'] == 'COS':
        file_dict['fppos'] = header['FPPOS']
    elif header['INSTRUME'] == 'STIS':
        file_dict['fppos'] = 0

    # Set image metadata keys
    file_dict['filename'] = os.path.basename(filename)
    root_dst = SETTINGS['filesystem_dir']
    file_dict['src'] = filename
    file_dict['path'] = os.path.join(root_dst, file_dict['targname'])
    today = datetime.datetime.today()
    file_dict['ingest_date'] = datetime.datetime.strftime(today, '%Y-%m-%d')

    return file_dict

# -----------------------------------------------------------------------------

def move_file(file_dict):
    """

    """

    pass

# -----------------------------------------------------------------------------

def update_database(file_dict):
    """

    """

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------

if __name__ == '__main__':

    filelist = glob.glob(os.path.join(SETTINGS['ingest_dir'], '*.fits*'))

    for file_to_ingest in filelist[0:1]:

        print('Ingesting {}'.format(file_to_ingest))

        file_dict = make_file_dict(file_to_ingest)
        update_database(file_dict)
        move_file(file_dict)
