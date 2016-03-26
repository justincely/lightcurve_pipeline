from setuptools import setup
from setuptools import find_packages

# Command line scripts
scripts = ['reset_hstlc_filesystem = lightcurve_pipeline.scripts.reset_hstlc_filesystem:main',
           'reset_hstlc_database = lightcurve_pipeline.scripts.reset_hstlc_database:main',
           'download_hstlc = lightcurve_pipeline.scripts.download_hstlc:main',
           'ingest_hstlc = lightcurve_pipeline.scripts.ingest_hstlc:main',
           'build_stats_table = lightcurve_pipeline.scripts.build_stats_table:main',
           'make_hstlc_plots = lightcurve_pipeline.scripts.make_hstlc_plots:main']
entry_points = {}
entry_points['console_scripts'] = scripts

setup(
    name = 'lightcurve-pipeline',
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
    requires = ['numpy', 'scipy', 'astropy', 'sqlalchemy', 'pyyaml', 'matplotlib', 'bokeh'],
    data_files = [('lightcurve_pipeline/utils/', ['lightcurve_pipeline/utils/config.yaml'])],
    scripts = ['scripts/hstlc_pipeline'],
    entry_points = entry_points,
    version = 1.0
    )
