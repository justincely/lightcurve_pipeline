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
    filename = '{}_{}.log'.format(module, timestamp)
    logfile = os.path.join(SETTINGS['log_dir'], filename)
    logging.basicConfig(
        filename=logfile,
        format='%(asctime)s %(levelname)s: %(message)s',
        datefmt='%m/%d/%Y %H:%M:%S',
        level=logging.INFO)

    # Log environment information
    logging.info('User: {}'.format(getpass.getuser()))
    logging.info('System: {}'.format(socket.gethostname()))
    logging.info('Python Version: {}'.format(sys.version.replace('\n', '')))
    logging.info('Python Path: {}'.format(sys.executable))
    logging.info('Numpy Version: {}'.format(numpy.__version__))
    logging.info('Numpy Path: {}'.format(numpy.__path__[0]))
    logging.info('Astropy Version: {}'.format(astropy.__version__))
    logging.info('Astropy Path: {}'.format(astropy.__path__[0]))
    logging.info('SQLAlchemy Version: {}'.format(sqlalchemy.__version__))
    logging.info('SQLAlchemy Path: {}'.format(sqlalchemy.__path__[0]))

    set_permissions(logfile)
