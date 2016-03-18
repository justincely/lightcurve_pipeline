#! /usr/bin/env python

"""Reset all or specific tables in the hstlc database

**Authors:**

    Matthew Bourque

**Use:**

    This script is intended to be executed via the command line as
    such:

    >>> reset_hstlc_database [table]

    ``table`` (*optional*) - Reset the specific table given. Can be any
    valid table that exists in the hstlc database, ``all`` in which all
    tables will be reset, or ``production`` in which only the
    ``metadata``, ``outputs``, and ``stats`` tables will be reset.  If
    an argument is not provided, the default value of ``production`` is
    used.

**Dependencies:**

    (1) Users must have access to the hstlc database
    (2) Users must also have a ``config.yaml`` file located in the
        ``lightcurve_pipeline/utils/`` directory with the following
        keys:

        - ``db_connection_string`` - The hstlc database connection
          string
        - ``home_dir`` - The home hstlc directory, where the
          ``bad_data`` table will be stored in a text file

    Other external library dependencies include:
        - ``lightcurve_pipeline``
        - ``pymysql``
        - ``sqlalchemy``
"""

from __future__ import print_function

import argparse
import inspect
import os
import pickle
import sys

from lightcurve_pipeline.utils.utils import SETTINGS
from lightcurve_pipeline.database import database_interface
from lightcurve_pipeline.database.database_interface import session
from lightcurve_pipeline.database.database_interface import engine
from lightcurve_pipeline.database.database_interface import BadData

# -----------------------------------------------------------------------------

def get_valid_tables():
    """Return a list of table names in the hstlc database

    Returns
    -------
    tables : list
        A list of hstlc table names
    """

    tables = []
    classmembers = inspect.getmembers(database_interface, inspect.isclass)
    for classmember in classmembers:
        try:
            tables.append(classmember[1].__tablename__)
        except AttributeError:
            pass

    return tables

# -----------------------------------------------------------------------------

def parse_args():
    """Parse command line arguments

    Returns
    -------
    args : argparse object
        An argparse object containing the arguments
    """

    reset_table_help = ('The table to reset. Can be any valid database table,'
        '"all" to reset all tables, or "production" to reset only the '
        'production tables.  The default option is "production".  The '
        'production tables constsit of: Metadata, Outputs, and Stats.')

    parser = argparse.ArgumentParser()
    parser.add_argument('reset_table', action='store', nargs='?', type=str,
        default='production', help=reset_table_help)
    args = parser.parse_args()

    # Make sure the argument is a valid option
    valid_options = get_valid_tables()
    valid_options.append('all')
    valid_options.append('production')
    explanation = '{} is not a valid table.'.format(args.reset_table)
    args.reset_table = args.reset_table.lower()
    assert args.reset_table in valid_options, explanation

    return args

# -----------------------------------------------------------------------------

def rebuild_production_tables():
    """Rebuild the ``prodction`` tables of the hstlc database, which
    consist of the ``metadata``, ``outputs``, and ``stats`` tables.
    The ``bad_data`` table is treated separately;  Since the
    ``bad_data`` table cannot easily be reconstructed (since bad data
    is not necessarily re-ingested), the data within the table is
    written out to a text file and re-ingested after the database is
    reset.  This essentially results in a reset database for the
    production tables, but the bad data table effectively remains
    untouched.
    """

    # # Write the contents of the bad_data table out to a text file
    pickle_file = os.path.join(SETTINGS['home_dir'], 'bad_data.pck')
    query = session.query(BadData).all()
    session.close()
    dict_list = [result.__dict__ for result in query]
    with open(pickle_file, 'w') as f:
        pickle.dump(dict_list, f)

    # Reset the database
    database_interface.base.metadata.drop_all()
    database_interface.base.metadata.create_all()

    # Rebuild the bad_data table
    with open(pickle_file, 'rb') as f:
        dict_list = pickle.load(f)
    for row in dict_list:
        engine.execute(BadData.__table__.insert(), row)

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------

def main():
    """The main function of the ``reset_hstlc_database`` script
    """

    # Parse arguments
    args = parse_args()

    # Give user a second chance
    prompt = ('About to reset {} table(s) for database instance {}. '
        'Do you wish to proceed? (y/n)\n'.format(args.reset_table,
        SETTINGS['db_connection_string']))

    response = raw_input(prompt)

    if response.lower() == 'y':
        print('Resetting {} table(s)'.format(args.reset_table))

        if args.reset_table == 'all':
            database_interface.base.metadata.drop_all()
            database_interface.base.metadata.create_all()

        elif args.reset_table == 'production':
            rebuild_production_tables()

        else:
            database_interface.base.metadata.tables[args.reset_table].drop()
            database_interface.base.metadata.tables[args.reset_table].create()

# -----------------------------------------------------------------------------

if __name__ == '__main__':

    main()
