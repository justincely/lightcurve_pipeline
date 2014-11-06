"""Ingestion script to move files into hstlc filesystem and update the
hstlc database.
"""

from __future__ import print_function

import datetime
import glob
import grp
import os
import shutil

from astropy.io import fits

from lightcurve_pipeline.settings.settings import SETTINGS
from lightcurve_pipeline.settings.settings import set_permissions
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
    file_dict['path'] = os.path.join(root_dst, file_dict['targname'])
    today = datetime.datetime.today()
    file_dict['ingest_date'] = datetime.datetime.strftime(today, '%Y-%m-%d')

    return file_dict

# -----------------------------------------------------------------------------

def move_file(file_dict):
    """Move the file from the ingest directory into the filesystem.

    Parameters
    ----------
    file_dict : dict
        A dictionary containing metadata of the file.

    Notes
    -----
    The parent directory to the file is named afer the file's TARGNAME.
    """

    # Create parent directory if necessary
    if not os.path.exists(file_dict['path']):
        print('\tCreating directory {}'.format(file_dict['path']))
        os.mkdir(file_dict['path'])
        set_permissions(file_dict['path'])

    # Move the file from ingest directory into filesystem
    # Using shutil.copyfile instead of shutil.move for testing purposes
    src = os.path.join(SETTINGS['ingest_dir'], file_dict['filename'])
    dst = os.path.join(file_dict['path'], file_dict['filename'])
    print('\tMoving file.')
    shutil.copyfile(src, dst)

    # Set permissions
    print('\tSetting permissions.')
    set_permissions(dst)

# -----------------------------------------------------------------------------

def update_database(file_dict):
    """Insert or update a record in the database containing the
    file_dict information.

    Parameters
    ----------
    file_dict : dict
        A dictionary containing metadata of the file.  Each key of the
        file_dict corresponds to a column in the database.
    """

    print('\tUpdating database.')

    # Get the id of the record, if it exists
    query = session.query(Metadata.id)\
        .filter(Metadata.filename == file_dict['filename']).all()
    if query == []:
        id_test = ''
    else:
        id_test = query[0][0]

    # If id doesn't exist then insert. If id exsits, then update
    if id_test == '':
        engine.execute(Metadata.__table__.insert(), file_dict)
    else:
        session.query(Metadata)\
            .filter(Metadata.id == id_test)\
            .update(file_dict)

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------

if __name__ == '__main__':

    filelist = glob.glob(os.path.join(SETTINGS['ingest_dir'], '*.fits*'))

    for file_to_ingest in filelist[0:4]:

        print('Ingesting {}'.format(file_to_ingest))

        file_dict = make_file_dict(file_to_ingest)
        update_database(file_dict)
        move_file(file_dict)
