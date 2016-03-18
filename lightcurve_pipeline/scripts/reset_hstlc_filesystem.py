#! /usr/bin/env python

"""
Reset the hstlc filesystem by moving files back into the ingestion
directory.  Files are moved from the ``filesystem_dir`` directory to
the ``ingest_dir`` directory, as determined by the config file (see
below).  Additionally, output products located in the ``outputs_dir``
directory, as determined by the config file (see below) are removed.

**Authors:**

    Matthew Bourque

**Use:**

    This script is intended to be executed via the command line as
    such:

    >>> reset_hstlc_filesystem

**Dependencies:**

    Users must have a ``config.yaml`` file located in the
    ``lightcurve_pipeline/utils/`` directory with the following
    keys:

        - ``ingest_dir`` - The path to where files to be ingested are
          stored
        - ``filesystem_dir`` - The path to the hstlc filesystem
        - ``outputs_dir`` - The path to where hstlc output products are
          stored

    Other external library dependencies include:
        - ``lightcurve_pipeline``
"""

from __future__ import print_function

import glob
import os
import shutil

from lightcurve_pipeline.utils.utils import SETTINGS

# -----------------------------------------------------------------------------

def move_files_to_ingest():
    """
    Move files from filesystem back to the ingestion directory. If the
    file already exists in the ingest directory, the file is removed
    rather than moved.
    """

    # Gather files in the filesystem directory
    filelist = glob.glob(os.path.join(SETTINGS['filesystem_dir'], '*/*.fits'))
    for filename in filelist:

        dst = os.path.join(SETTINGS['ingest_dir'], os.path.basename(filename))

        # Move the file if it doesn't already exist, otherwise simply remove it
        if not os.path.exists(dst):
            shutil.move(filename, SETTINGS['ingest_dir'])
            print('\tMoved {} to {}'.format(filename, SETTINGS['ingest_dir']))
        else:
            os.remove(filename)

# -----------------------------------------------------------------------------

def remove_output_directories():
    """
    Remove all output products and output directories
    """

    directories = glob.glob(os.path.join(SETTINGS['outputs_dir'], '*'))
    for directory in directories:
        try:
            shutil.rmtree(directory)
            print('\tRemoved directory {}'.format(directory))
        except:
            print('Could not remove {}'.format(directory))

# -----------------------------------------------------------------------------

def remove_filesystem_directories():
    """
    Remove parent directories from the filesystem if they are empty
    """

    dirlist = glob.glob(os.path.join(SETTINGS['filesystem_dir'], '*'))
    for directory in dirlist:
        try:
            os.rmdir(directory)
            print('\tRemoved directory {}'.format(directory))
        except OSError:
            print('Could not remove {}'.format(directory))

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------

def main():
    """The main function of the ``reset_hstlc_filesystem`` script
    """

    # Give the user a second chance
    prompt = 'About to reset filesystem {}. '.format(SETTINGS['filesystem_dir'])
    prompt += 'Do you wish to proceed? (y/n)'
    response = raw_input(prompt)

    if response.lower() == 'y':
        print('Resetting filesystem')
        move_files_to_ingest()
        remove_filesystem_directories()
        remove_output_directories()

# -----------------------------------------------------------------------------

if __name__ == '__main__':

    main()
