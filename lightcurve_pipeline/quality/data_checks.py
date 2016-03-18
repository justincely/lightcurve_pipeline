"""
Perform data quality checks for the given dataset.  The dataset is
checked for a number of issues, which include:

(1) A non-normal ``EXPFLAG`` - indicating that something went wrong
    during the observation
(2) A non-linear time column in which time does not progress linearly
    through the ``TIME`` column in the dataset
(3) A dataset not having any events
(4) A dataset in which all events occur at a single time
(5) A dataset that is part of a problematic proposal
(6) A dataset with an exposure time that is too short

Datasets that do not pass these checks are moved to the
``bad_data_dir``, as determined by the config file (see below)

**Authors:**

    Justin Ely, Matthew Bourque

**Use:**

    This module is intended to be imported and used by the
    ``ingest_hstlc`` script as such:

::

    from lightcurve_pipeline.quality.data_checks import dataset_ok
    dataset_ok(dataset)

**Dependencies:**

    (1) Users must have access to the hstlc database
    (2) Users must also have a ``config.yaml`` file located in the
        ``lightcurve_pipeline/utils/`` directory with the following
        keys:

        - ``db_connection_string`` - The hstlc database connection
          string
        - ``bad_data_dir`` - The directory in which bad data files are
          stored

    Other external library dependencies include:
        - ``astropy``
        - ``lightcurve_pipeline``
        - ``pymysql``
        - ``sqlalchemy``
"""

import inspect
import logging
import os
import shutil

from astropy.io import fits

from lightcurve_pipeline.utils.utils import SETTINGS
from lightcurve_pipeline.utils.utils import set_permissions
from lightcurve_pipeline.database.update_database import update_bad_data_table

#-------------------------------------------------------------------------------

def dataset_ok(filename, move=True):
    """Perform quality check on the given dataset, and update the
    ``bad_data`` table and move the dataset to the ``bad_data``
    directory if it doesn't pass

    Parameters
    ----------
    filename : string
        The full path to the dataset
    move : bool, optional
        Whether or not to update the ``bad_data`` table and move the
        file

    Returns
    -------
    ``True`` if the dataset passes all of the quality checks, ``False``
    if it doesn't.
    """

    all_functions = [value for key, value in inspect.currentframe().f_globals.iteritems() if key.startswith('check_')]

    with fits.open(filename) as hdu:

        for func in all_functions:
            success, reason = func(hdu)
            if not success:
                if move:
                    logging.info('\tBad data for {}: {}'.format(filename, reason))
                    update_bad_data_table(os.path.basename(filename), reason)
                    move_file(filename)
                return False

    return True

#-------------------------------------------------------------------------------

def move_file(filename):
    """Move the given dataset to the ``bad_data`` directory

    Parameters
    ----------
    filename : string
        The full path to the dataset
    """

    dst = os.path.join(SETTINGS['bad_data_dir'], os.path.basename(filename))
    if os.path.exists(dst):
        os.remove(dst)
    shutil.move(filename, dst)
    set_permissions(dst)

#-------------------------------------------------------------------------------

def check_expflag(hdu):
    """Check that the ``EXPFLAG`` keyword is ``NORMAL``

    Parameters
    ----------
    hdu : astropy.io.fits.hdu.hdulist.HDUList
        The hdulist of the dataset

    Returns
    -------
    success : boolean
        ``True`` if the ``EXPFLAG`` is ``NORMAL``, ``False`` otherwise
    reason : string
        An empty string if success is ``True``, ``Bad EXPFLAG``
        otherwise
    """

    if hdu[1].header['EXPFLAG'] != 'NORMAL':
        return False, 'Bad EXPFLAG'

    return True, ''

#-------------------------------------------------------------------------------

def check_linear(hdu):
    """Check that the time column linearly progresses

    Parameters
    ----------
    hdu : astropy.io.fits.hdu.hdulist.HDUList
        The hdulist of the dataset

    Returns
    -------
    success : boolean
        ``True`` if time progressing linearly, ``False`` otherwise
    reason : string
        An empty string if success is ``True``, ``Non-linear time``
        otherwise
    """

    time_data = hdu[1].data['time']
    last = time_data[0]
    for val in time_data[1:]:
        if not val >= last:
            return False, 'Non-linear time'
        last = val

    return True, ''

#-------------------------------------------------------------------------------

def check_no_events(hdu):
    """Check that the dataset has events

    Parameters
    ----------
    hdu : astropy.io.fits.hdu.hdulist.HDUList
        The hdulist of the dataset

    Returns
    -------
    success : boolean
        ``True`` if the dataset has events, ``False`` otherwise
    reason : string
        An empty string if success is ``True``, ``No events``
        otherwise
    """

    if len(hdu[1].data) == 0:
        return False, 'No events'

    return True, ''

#-------------------------------------------------------------------------------

def check_not_singular(hdu):
    """Check that the events in the dataset are not from a single time

    Parameters
    ----------
    hdu : astropy.io.fits.hdu.hdulist.HDUList
        The hdulist of the dataset

    Returns
    -------
    success : boolean
        ``True`` if events are not from a single time, ``False``
        otherwise
    reason : string
        An empty string if success is ``True``, ``Singular event``
        otherwise
    """

    time_data = hdu[1].data['time']
    if len(set(time_data)) == 1:
        return False, 'Singular event'

    return True, ''

#-------------------------------------------------------------------------------

def check_bad_proposal(hdu):
    """Check that the proposal ID is not in a list of known 'bad'
    programs.  Programs can be bad for a number of reasons, typically
    because of specialized calibration purposes like focus sweeps or
    high-voltage tests.

    Parameters
    ----------
    hdu : astropy.io.fits.hdu.hdulist.HDUList
        The hdulist of the dataset

    Returns
    -------
    success : boolean
        ``True`` if events are not from a known bad proposal, ``False``
        otherwise
    reason : string
        An empty string if success is ``True``, ``Bad Proposal``
        otherwise
    """

    #-- 13635, 'FUV Focus Sweep Enabling Program for COS at LP3 (LENA2)  ???
    known_issue_proposals = {}

    if hdu[0].header['PROPOSID'] in known_issue_proposals:
        return False, 'Bad Proposal'

    return True, ''

#-------------------------------------------------------------------------------

def check_exptime(hdu):
    """Check that the dataset exptime is not too short.  The threshold
    is initially set to 1 second to filter out a small subset of very
    short exposures.

    Parameters
    ----------
    hdu : astropy.io.fits.hdu.hdulist.HDUList
        The hdulist of the dataset

    Returns
    -------
    success : boolean
        ``True`` if exptime greater than threshold, ``False`` otherwise
    reason : string
        An empty string if success is ``True``, ``Short Exposure``
        otherwise
    """

    if hdu[1].header['EXPTIME'] < 1:
        return False, 'Short Exposure'

    return True, ''

#-------------------------------------------------------------------------------
