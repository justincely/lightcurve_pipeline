"""This module houses several functions that are key to several modules
and scripts within the hstlc package.  Please see the individual
function documentation for more information.

**Authors:**

    Matthew Bourque

**Use:**

    This functions within this module are intended to be imported by
    the various hstlc scripts and modules, as such:

::

    from lightcurve_pipeline.utils.utils import SETTINGS
    from lightcurve_pipeline.utils.utils import insert_or_update
    from lightcurve_pipeline.utils.utils import set_permissions
    from lightcurve_pipeline.utils.utils import setup_logging
    from lightcurve_pipeline.utils.utils import make_directory

**Dependencies:**

    External library dependencies include:
        - ``astropy``
        - ``lightcurve_pipeline``
        - ``numpy``
        - ``pymyslq``
        - ``sqlalchemy``
"""

import datetime
import getpass
import grp
import logging
import os
import socket
import sys
import yaml

import astropy
import numpy
import sqlalchemy

# -----------------------------------------------------------------------------

def get_settings():
    """Return the setting information located in the configuration file
    located in the ``lightcurve_pipeline/utils/`` directory

    Returns
    -------
    data : dict
        A dictionary containing the settings present in the config.yaml
        configuration file.  Thus, the keys of this dictionary
        presumably are:

            (1) ``db_connection_string``
            (2) ``ingest_dir``
            (3) ``filesystem_dir``
            (4) ``outputs_dir``
            (5) ``composite_dir``
            (6) ``log_dir``
            (7) ``download_dir``
            (8) ``plot_dir``
            (9) ``bad_data_dir``
            (10) ``home_dir``

        The values of the keys are the user-supplied configurations
    """

    config_file = os.path.join(os.path.dirname(__file__), 'config.yaml')
    with open(config_file, 'r') as f:
        data = yaml.load(f)

    return data

SETTINGS = get_settings()

# -----------------------------------------------------------------------------

def insert_or_update(table, data, id_num):
    """
    Insert or update the given database table with the given data.
    This function performs the logic of inserting or updating an
    entry into the hstlc database; if an entry with the given
    ``id_num`` already exists, then the entry is updated, otherwise a
    new entry is inserted.

    Parameters
    ----------
    table : sqlalchemy.ext.declarative.api.DeclarativeMeta
        The table of the database to update
    data : dict
        A dictionary of the information to update.  Each key of the
        dictionary must be a column in the given table
    id_num : string
        The row ID to update.  If ``id_num`` is blank, then a new row
        is inserted instead.
    """

    from lightcurve_pipeline.database.database_interface import engine
    from lightcurve_pipeline.database.database_interface import get_session

    session = get_session()
    if id_num == '':
        engine.execute(table.__table__.insert(), data)
    else:
        session.query(table)\
            .filter(table.id == id_num)\
            .update(data)
        session.commit()
    session.close()

# -----------------------------------------------------------------------------

def set_permissions(path):
    """
    Set the permissions of the file path to hstlc permissions settings.
    The hstlc permissions settings are groupID = ``hstlc`` and
    permissions of ``rwxrwx---``.

    Parameters
    ----------
    path : string
        The path to the file
    """

    uid = os.stat(path).st_uid
    gid = grp.getgrnam("hstlc").gr_gid

    if uid == os.getuid():
        os.chown(path, uid, gid)
        os.chmod(path, 0770)

# -----------------------------------------------------------------------------

def setup_logging(module):
    """
    This function will configure the logging for the execution of the
    given module.  Logs are written out to the ``log_dir`` directory
    (as determined by the ``config.yaml`` file) with the filename
    ``<module>_<timestamp>.log``.

    Parameters
    ----------
    module : string
        The name of the module to log
    """

    # Configure logging
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d-%H-%M')
    filename = '{0}_{1}.log'.format(module, timestamp)
    logfile = os.path.join(SETTINGS['log_dir'], filename)
    logging.basicConfig(
        filename=logfile,
        format='%(asctime)s %(levelname)s: %(message)s',
        datefmt='%m/%d/%Y %H:%M:%S',
        level=logging.INFO)

    # Log environment information
    logging.info('User: {0}'.format(getpass.getuser()))
    logging.info('System: {0}'.format(socket.gethostname()))
    logging.info('Python Version: {0}'.format(sys.version.replace('\n', '')))
    logging.info('Python Path: {0}'.format(sys.executable))
    logging.info('Numpy Version: {0}'.format(numpy.__version__))
    logging.info('Numpy Path: {0}'.format(numpy.__path__[0]))
    logging.info('Astropy Version: {0}'.format(astropy.__version__))
    logging.info('Astropy Path: {0}'.format(astropy.__path__[0]))
    logging.info('SQLAlchemy Version: {0}'.format(sqlalchemy.__version__))
    logging.info('SQLAlchemy Path: {0}'.format(sqlalchemy.__path__[0]))

    set_permissions(logfile)

# -----------------------------------------------------------------------------

def make_directory(directory):
    """Create a directory if it doesn't already exist and set the hstlc
    permissions

    Parameters
    ----------
    directory : string
        The path to the directory
    """

    if not os.path.exists(directory):
        try:
            os.mkdir(directory)
            set_permissions(directory)
        except OSError:
            pass
