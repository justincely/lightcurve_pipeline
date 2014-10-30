"""Ingestion script to move files into hstlc filesystem and update the
hstlc database.
"""

from __future__ import print_function

import glob
import os
import yaml

from astropy.io import fits
from lightcurve_pipeline.settings.settings import SETTINGS

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
    hdulist = fits.open(filename, 'readonly')
    header = hdulist[0].header

    # Set header keys
    file_dict['TELESCOP'] = header['TELESCOP']
    file_dict['INSTRUME'] = header['INSTRUME']
    file_dict['TARGNAME'] = header['TARGNAME']
    file_dict['CAL_VER'] = header['CAL_VER']
    file_dict['OBSTYPE'] = header['OBSTYPE']
    file_dict['CENTRWV'] = header['CENTRWV']
    file_dict['APERTURE'] = header['APERTURE']
    file_dict['DETECTOR'] = header['DETECTOR']
    file_dict['OPT_ELEM'] = header['OPT_ELEM']

    if header['INSTRUME'] == 'COS':
        file_dict['FPPOS'] = header['FPPOS']
    elif header['INSTRUME'] == 'STIS':
        file_dict['FPPOS'] = 0

    # Set path keys
    root_dst = SETTINGS['filesystem_dir']
    file_dict['src'] = filename
    file_dict['dst'] = os.path.join(root_dst, file_dict['TARGNAME'])

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

    pass

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------

if __name__ == '__main__':

    filelist = glob.glob(os.path.join(SETTINGS['ingest_dir'], '*.fits*'))

    for file_to_ingest in filelist:

        print('Ingesting {}'.format(file_to_ingest))

        file_dict = make_file_dict(file_to_ingest)
        update_database(file_dict)
        move_file(file_dict)
