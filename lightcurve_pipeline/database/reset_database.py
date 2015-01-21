#! /usr/bin/env python

"""
Reset all tables in the database.
"""

from __future__ import print_function

from lightcurve_pipeline.database.database_interface import base
from lightcurve_pipeline.utils.utils import SETTINGS

if __name__ == '__main__':

    prompt = 'About to reset database instance {}. '.format(SETTINGS['db_connection_string'])
    prompt += 'Do you wish to proceed? (y/n)'

    response = raw_input(prompt)

    if response.lower() == 'y':
        print('Resetting database')
        base.metadata.drop_all()
        base.metadata.create_all()
