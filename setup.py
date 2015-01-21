from distutils.core import setup
from setuptools import find_packages

setup(
    name = 'lightcurve_pipeline',
    description = 'Create lightcurves from HST/COS and HST/STIS data',
    url = 'https://github.com/justincely/lightcurve_pipeline.git',
    author = 'Justin Ely',
    author_email = 'ely@stsci.edu',
    keywords = ['astronomy'],
    classifiers = ['Programming Language :: Python',
                   'Development Status :: 1 - Planning',
                   'Intended Audience :: Science/Research',
                   'Topic :: Scientific/Engineering :: Astronomy',
                   'Topic :: Scientific/Engineering :: Physics',
                   'Topic :: Software Development :: Libraries :: Python Modules'],
    packages = find_packages(),
    requires = ['numpy', 'astropy', 'sqlalchemy', 'pyyaml'],
    data_files = [('lightcurve_pipeline/settings/', ['lightcurve_pipeline/settings/config.yaml'])]
    )