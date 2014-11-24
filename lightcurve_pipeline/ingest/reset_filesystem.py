#! /usr/bin/env python

"""
Reset all filesystem by moving files back into the ingestion folder.
"""

from __future__ import print_function

import glob
import os
import shutil

from lightcurve_pipeline.settings.settings import SETTINGS

# -----------------------------------------------------------------------------

def move_files_to_ingest():
    """
    Move files from filesystem back to the ingestion directory.

    Notes
    -----
    If the file already exists in the ingest directory, the file is
    removed rather than moved.
    """

    filelist = glob.glob(os.path.join(SETTINGS['filesystem_dir'], '*/*.fits'))
    for filename in filelist:

        dst = os.path.join(SETTINGS['ingest_dir'], os.path.basename(filename))

        if not os.path.exists(dst):
            shutil.move(filename, SETTINGS['ingest_dir'])
            print('\tMoved {} to {}'.format(filename, SETTINGS['ingest_dir']))
        else:
            os.remove(filename)

# -----------------------------------------------------------------------------

def remove_directories():
    """
    Remove parent directories if they are empty
    """

    dirlist = glob.glob(os.path.join(SETTINGS['filesystem_dir'], '*'))
    for directory in dirlist:
        try:
            os.rmdir(directory)
            print('\tRemoved directory {}'.format(directory))
        except OSError:
            print('Could not remove {}'.format(directory))

# -----------------------------------------------------------------------------

if __name__ == '__main__':

    print('Resetting filesystem')

    move_files_to_ingest()
    remove_directories()
