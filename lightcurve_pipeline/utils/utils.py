"""
Various utilities needed by the lightcurve_pipeline package.
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
    located in the settings/ directory.
    """

    config_file = os.path.join(os.path.dirname(__file__), 'config.yaml')
    with open(config_file, 'r') as f:
        data = yaml.load(f)

    return data

SETTINGS = get_settings()

# -----------------------------------------------------------------------------

from lightcurve_pipeline.database.database_interface import engine
from lightcurve_pipeline.database.database_interface import session

def insert_or_update(table, data, id_num):
    """
    Insert or update the table with information in the record_dict.

    Parameters
    ----------
    table :
        The table of the database to update.
    data : dict
        A dictionary of the information to update.  Each key of the
        dictionary must be a column in the Table.
    id_num : string
        The row ID to update.  If id_test is blank, then a new row is
        inserted.
    """

    if id_num == '':
        engine.execute(table.__table__.insert(), data)
    else:
        session.query(table)\
            .filter(table.id == id_num)\
            .update(data)
        session.commit()

# -----------------------------------------------------------------------------

def set_permissions(path):
    """
    Set the permissions of the file path to hstlc settings.
    """

    uid = os.stat(path).st_uid
    gid = grp.getgrnam("hstlc").gr_gid

    if uid == os.getuid():
        os.chown(path, uid, gid)
        os.chmod(path, 0770)

# -----------------------------------------------------------------------------

def setup_logging(module):
    """
    Configures and initializes a log to store program execution
    information.
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
    """Create a directory if it doesn't already exist and set the HSTLC
    permissions.

    Parameters
    ----------
    directory : string
        The path to the directory.
    """

    if not os.path.exists(directory):
        try:
            logging.info('\tCreating directory {}'.format(directory))
            os.mkdir(directory)
            set_permissions(directory)
        except OSError:
            pass
