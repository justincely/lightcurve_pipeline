from distutils.core import setup
from setuptools import find_packages

setup(
    name = 'lightcurve_pipeline',
    description = 'Create lightcurves from HST/COS and HST/STIS data',
    url = 'https://github.com/justincely/lightcurve_pipeline.git',
    author = 'Matthew Bourque',
    author_email = 'bourque@stsci.edu',
    keywords = ['astronomy'],
    classifiers = ['Programming Language :: Python',
                   'Development Status :: 1 - Planning',
                   'Intended Audience :: Science/Research',
                   'Topic :: Scientific/Engineering :: Astronomy',
                   'Topic :: Scientific/Engineering :: Physics',
                   'Topic :: Software Development :: Libraries :: Python Modules'],
    packages = find_packages(),
    requires = ['numpy', 'astropy', 'sqlalchemy', 'pyyaml'],
    scripts = ['scripts/download_hstlc',
               'scripts/ingest_hstlc',
               'scripts/reset_hstlc_database',
               'scripts/reset_hstlc_filesystem',
               'scripts/build_stats_table',
               'scripts/make_hstlc_plots',
               'scripts/hstlc_pipeline'],
    data_files = [('lightcurve_pipeline/utils/', ['lightcurve_pipeline/utils/config.yaml'])]
    )
