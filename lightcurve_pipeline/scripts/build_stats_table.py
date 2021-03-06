#! /usr/bin/env python

"""
Generate the ``stats`` table in the hstlc database, which stores
statistics for every lightcurve (both individual and composite).
Several statistics and flags are computed for every lightcurve
generated by ingest_hstlc, including statistics on counts, primitive
data quality statistics, and flags to indicate interesting datasets.

**Authors:**

    Matthew Bourque

**Use:**

    This script is intended to be executed as part of the
    hstlc_pipeline shell script.  However, users can also execute this
    script via the command line as such:

    >>> build_stats_table [product_type]

    ``product_type`` (*required*) - The type of lightcurves to process.
    Can be *individual* for individual lightcurves, *composite* for
    composite lightcurves, or *both* for both types.

**Outputs:**

    (1) New and/or updated entries in the ``stats`` table in the hstlc
        database
    (2) a log file in the ``log_dir`` directory as determined by the
        config file (see below)

**Dependencies:**

    (1) Users must have access to the hstlc database.

    (2) Users must also have a ``config.yaml`` file located in the
        ``lightcurve_pipeline/utils/`` directory with the following
        keys:

        - ``db_connection_string`` - The hstlc database connection
          string
        - ``log_dir`` - The path to where the log file will be stored

    Other external library dependencies include:
        - ``astropy``
        - ``lightcurve``
        - ``lightcurve_pipeline``
        - ``numpy``
        - ``pymysql``
        - ``scipy``
        - ``sqlalchemy``
"""

import argparse
import logging
import os

from astropy.io import fits
import lightcurve
import numpy as np
from scipy import signal
from scipy.stats.stats import pearsonr

from lightcurve_pipeline.utils.periodogram_stats import get_periodogram_stats
from lightcurve_pipeline.utils.utils import insert_or_update
from lightcurve_pipeline.utils.utils import setup_logging
from lightcurve_pipeline.database import database_interface
from lightcurve_pipeline.database.database_interface import engine
from lightcurve_pipeline.database.database_interface import session
from lightcurve_pipeline.database.database_interface import Stats
from lightcurve_pipeline.database.database_interface import Outputs
from lightcurve_pipeline.database.update_database import update_stats_table

# -----------------------------------------------------------------------------

def get_lightcurves(product_type):
    """Queries the ``outputs`` table to build a list of lightcurves to
    get stats from

    Parameters
    ----------
    product_type : string
        The type of lightcurves to process. Can either be
        ``individual``, ``composite``, or ``both``

    Returns
    -------
    lightcurves : list
        A list of paths to lightcurve products
    """

    # Build lists of paths to lightcurves
    results = session.query(Outputs).all()
    individual_lightcurves = set([os.path.join(result.individual_path, result.individual_filename) for result in results])
    composite_lightcurves = set([os.path.join(result.composite_path, result.composite_filename) for result in results if result.composite_filename != None])

    # Return appropriate list based on product_type
    if product_type == 'individual':
        lightcurves = individual_lightcurves
    elif product_type == 'composite':
        lightcurves = composite_lightcurves
    elif product_type == 'both':
        lightcurves = individual_lightcurves | composite_lightcurves

    return lightcurves

# -----------------------------------------------------------------------------

def get_stats(dataset):
    """Gathers various statistics for the given lightcurve product

    Parameters
    ----------
    dataset : string
        The path to the lightcurve product

    Returns
    -------
    stats_dict : dictionary
        A dictionary whose keys are column names of the ``stats``
        table and whose values are the corresponding statistics
    """

    # Initialize dictionary
    stats_dict = {}

    # Add path information
    stats_dict['lightcurve_path'] = os.path.dirname(dataset)
    stats_dict['lightcurve_filename'] = os.path.basename(dataset)

    # Open lightcurve and extract information
    hdulist = fits.open(dataset, mode='readonly')
    counts = hdulist[1].data.counts
    mjd = hdulist[1].data.mjd

    # Populate stats_dict with counts information
    stats_dict['total'] = int(np.sum(counts))

    # If total counts is zero, there is nothing else to compute
    # If there are counts, then populate the rest of stats_dict
    if stats_dict['total'] > 0:

        # Populate stats dict with count stats
        stats_dict['mean'] = float(np.mean(counts))
        stats_dict['mu'] = float(np.sqrt(stats_dict['mean']))
        stats_dict['stdev'] = float(np.std(counts))

        # Populate stats_dict with poisson information
        try:
            stats_dict['poisson_factor'] = float(stats_dict['stdev'] / stats_dict['mu'])
        except ZeroDivisionError:
            stats_dict['poisson_factor'] = 9999999.

        # Populate stats_dict with pearson information
        pearson_results = pearsonr(mjd, counts)
        stats_dict['pearson_r'] = float(pearson_results[0])
        stats_dict['pearson_p'] = float(pearson_results[1])

        # Set 'interesting periodogram' flag
        interesting_periodogram = False
        significant_threshold = 0.30
        for freq_space in ['short', 'med', 'long']:
            periods, power, mean, three_sigma, significant_periods, significant_powers = get_periodogram_stats(dataset, freq_space)
            if len(significant_powers) > 0:
                if max(significant_powers) >= significant_threshold:
                    interesting_periodogram = True
        stats_dict['periodogram'] = interesting_periodogram

    return stats_dict

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------

def parse_args():
    """Parse command line arguments

    Returns
    -------
    args : argparse object
        An argparse object containing the arguments
    """

    product_help = ('The type of output products to process.  Can be '
        '"individual", "composite", or "both".')

    parser = argparse.ArgumentParser()
    parser.add_argument('product_type', action='store', type=str, help=product_help)
    args = parser.parse_args()

    # Make sure the argument is a valid option
    valid_options = ['individual', 'composite', 'both']
    explanation = '{} is not a valid option.  Please choose "individual", "composite", or "both".'.format(args.product_type)
    assert args.product_type in valid_options, explanation

    return args

# -----------------------------------------------------------------------------

def main():
    """The main function of the ``build_stats_table`` script
    """

    # Configure logging
    module = os.path.basename(__file__).strip('.py')
    setup_logging(module)

    # Parse arguments
    args = parse_args()

    database_interface.base.metadata.create_all()

    # Query the outputs table for a list of lightcurves
    lightcurves = get_lightcurves(args.product_type)

    # For each lightcurve, compute statistics and update the database
    logging.info('{} datasets to process'.format(len(lightcurves)))
    for dataset in lightcurves:
        logging.info('Processing {}'.format(dataset))
        stats_dict = get_stats(dataset)
        update_stats_table(stats_dict, dataset)

    logging.info('Processing complete')

# -----------------------------------------------------------------------------
