#! /usr/bin/env python

"""
Reset all tables in the database.
"""

from lightcurve_pipeline.database.database_interface import base

if __name__ == '__main__':

    base.metadata.drop_all()
    base.metadata.create_all()
