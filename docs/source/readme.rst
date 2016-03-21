About hstlc
===========

Welcome to the hstlc (**H**\ubble **S**\pace **T**\elescope **L**\ight **C**\urve) project

The hstlc project aims to produce high level science products in the form of flux calibrated, UV lightcurves for all publicly available HST/COS and HST/STIS TIME-TAG datasets. This documenation provides an overview to the project, details about the implemented software systems, and a description of the output products.


Overview
--------

The Cosmic Origins Spectrograph (COS) and the Space Telescope Imaging Spectrograph (STIS) on board the Hubble Space Telescope (HST) continue to capture spectroscopic observations and deliver them to a steadily-growing archive. Observation products are primarily in the form of time-average spectra, however there exist many COS and STIS observations taken in the TIME-TAG observing mode wherein the position and time of each incoming photon is recorded. This results in an observation product in the form of a list of detected events, which can in turn be transformed into a lightcurve that can be used to discover and characterize unique phenomena in scientific observations.

The hstlc project aims to gather TIME-TAG observations and transform them into High Level Science Products (HLSPs) in the form of lightcurves in an automated way for all publicly available COS and STIS TIME-TAG observations. The project software is written in Python, and uses many supporting materials, including a `pipeline <http://pythonhosted.org/lightcurve-pipeline/readme.html#id1>`_, `database <http://pythonhosted.org/lightcurve-pipeline/readme.html#id3>`_, `filesystem <http://pythonhosted.org/lightcurve-pipeline/readme.html#id5>`_, `downloading platform <http://pythonhosted.org/lightcurve-pipeline/readme.html#downloads>`_, and a `lightcurve code library <https://github.com/justincely/lightcurve_pipeline>`_.

This project is supported by the `Hubble Archival Research program 13902 <http://www.stsci.edu/cgi-bin/get-proposal-info?id=13902&submit=Go&observatory=HST>`_. (P.I. Justin Ely)

Filetypes
---------


Pipeline
--------

The hstlc pipeline is a series of scripts, executed sequentially, that ingests raw TIME-TAG observations and produces lightcurves as well as various plots that analyze them.  The pipeline consits of three scripts:
    (1) `ingest_hstlc <http://pythonhosted.org/lightcurve-pipeline/hstlc_scripts.html#module-lightcurve_pipeline.scripts.ingest_hstlc>`_
    (2) `build_stats_table <http://pythonhosted.org/lightcurve-pipeline/hstlc_scripts.html#module-lightcurve_pipeline.scripts.build_stats_table>`_
    (3) `make_hstlc_plots <http://pythonhosted.org/lightcurve-pipeline/hstlc_scripts.html#module-lightcurve_pipeline.scripts.make_hstlc_plots>`_

The pipeline is further described below:

**ingest_hstlc**

The conversion of raw TIME-TAG observations to high-level science products (lightcurves) is performed by the `ingest_hstlc <http://pythonhosted.org/lightcurve-pipeline/hstlc_scripts.html#module-lightcurve_pipeline.scripts.ingest_hstlc>`_ script.  The following algorithm is employed by ``ingest_hstlc``:

    (1) Gather ``x1d``, ``tag``, and ``corrtag`` files from an ``ingest`` directory to build a list of files to ingest.
    (2) For each ``tag`` or ``corrtag`` file:
      (a) Open the file and retrieve the header and data.
      (b) Perform various `quality checks <http://pythonhosted.org/lightcurve-pipeline/hstlc_modules.html#module-lightcurve_pipeline.quality.data_checks>`_ on the data.  If the data is deemed to be bad, then update the ``bad_data`` table in the hstlc database and remove the file from the ``ingest`` directory.
      (c) Gather metadata and output location information from the file.
      (d) If the file is a ``STIS`` dataset, then convert the ``tag`` file into a ``corrtag`` file by calling the ``stis_corrtag`` function of the `lightcurve.stis <https://github.com/justincely/lightcurve/blob/master/lightcurve/stis.py>`_ module.
      (e) Update the ``metadata`` table in the hstlc Database with the metadata of the file.
      (f) Create the lightcurve using the `lightcurve <https://github.com/justincely/lightcurve>`_ library code and place the output product in the appropriate ``outputs`` directory based on the file's ``TARGNAME``.
      (g) Set the correct permissions of the output directory and/or files.
      (h) Update the ``outputs`` table of the hstlc Database with output location information.
      (i) Create a quicklook image for the observation and save it in the appropriate ``outputs`` directory.
      (j) Move the file (and its accompanying ``x1d`` file) from the ``ingest`` directory to the appropriate directory in the filesystem.
    (3) Use the ``metadata`` table to query for datasets that require (re)processing of composite lightcurves based on if new files have been ingested.
    (4) (re)Create a composite lightcurve for each dataset that requires (re)processing and save the composite lightcurve in the appropriate ``outputs`` directory.
    (5) Update the ``outputs`` table of the ``hstlc Database`` with composite lightcurve output location information.

**build_stats_table**

After the TIME-TAG observations are ingested and output lightcurves are produced, the ``build_stats_table`` script calculates various statistics for each individual and composite lightcurve and stores the statistics in the ``stats`` table in the hstlc database.  The following statistics are calculated:

    (1) ``total`` - The total number of counts in the lighcurve
    (2) ``mean`` The mean number of counts in the lightcurve
    (3) ``mu`` - The square root of the mean number of counts
    (4) ``stdev`` - The standard deviation of the counts in the lighcturve
    (5) ``poisson_factor`` - The ``stdev``/``mu`` of the lightcurve.  The greater the ``poisson_factor``, the less likely that noise in the lightcurve is due to poisson noise.
    (6) ``pearson_r`` - The Pearson R value for the correlation between time and counts.  A positive value (close to 1.0) indicates a positive correlation, a negative value (close to -1.0) indicates a negative correlation, and a near-zero value indicates no correlation.
    (7) ``pearson_p`` - The Pearson P value for the correlations between time and counts.  A low value (close to 0.0) indicates that the null-hypothesis that "counts and time are not correlated" can be rejected (i.e. the idea that the correlation is due to random sampling can be rejected -- there is reason to beleive that the correlation is real).  A high value (close to 1.0) indicates the opposite -- that the data do not give reason to believe that the correlation is real.
    (8) ``periodogram`` - A true/false value indicating if the lightcurve has an 'interesting' Lomb-Scargle periodogram.  A lightcurve is deemed to have an 'interesting' periodogram if there exists a period in which the Lomb-Scargle power exceeds 0.30 and the peak power exceeds three sigma about the mean.

**make_hstlc_plots**

Lastly, various plots that analyze and describe the individual and composite lightcurves are created in the ``make_hstlc_plots`` script.  The following plots are created:

    (1) Static lightcurve plots for each individual and composite lightcurve in the form of a PNG.
    (2) Interactive lightcurve plots for each individual and composite lightcurve in the form of a Bokeh/HTML plot.
    (3) Interactive, sortable 'exploratory' tables that display the various statistics and plots for each individual and composite lightcurve.
    (4) A histogram showing the cumulative exposure time for each target.
    (5) 'Configuration' pie charts showing the breakdown of lightcurves by grating/cenwave for each instrument/detector combination.
    (6) A histrogram showing the number of lightcurves for each filter.
    (7) Lomb-Scargle periodograms for each lightcurve.


Database
--------

The ``hstlc`` pipeline uses a MySQL database to store useful metadata and file location information for each dataset.  The database schema is defined by the Object-Relational Mappings (ORMs) contained in `database_interface <https://github.com/justincely/lightcurve_pipeline/blob/master/lightcurve_pipeline/database/database_interface.py>`_ module.  Below is a description of each table.  The database is populated by the `ingest_hstlc <https://github.com/justincely/lightcurve_pipeline/blob/master/scripts/ingest_hstlc>`_ script.  The database can also easily be reset by the `reset_hstlc_database <https://github.com/justincely/lightcurve_pipeline/blob/master/scripts/reset_hstlc_database>`_ script.

**Metadata Table**

The ``metadata`` table stores information about each observations location in the HSTLC filesystem as well as useful header keyword values.  The table contains the following columns:

    +-----------------+--------------+------+-----+---------+----------------+
    | Field           | Type         | Null | Key | Default | Extra          |
    +-----------------+--------------+------+-----+---------+----------------+
    | id              | int(11)      | NO   | PRI | NULL    | auto_increment |
    +-----------------+--------------+------+-----+---------+----------------+
    | filename        | varchar(30)  | NO   | UNI | NULL    |                |
    +-----------------+--------------+------+-----+---------+----------------+
    | path            | varchar(100) | NO   |     | NULL    |                |
    +-----------------+--------------+------+-----+---------+----------------+
    | ingest_date     | date         | NO   |     | NULL    |                |
    +-----------------+--------------+------+-----+---------+----------------+
    | telescop        | varchar(10)  | NO   |     | NULL    |                |
    +-----------------+--------------+------+-----+---------+----------------+
    | instrume        | varchar(10)  | NO   |     | NULL    |                |
    +-----------------+--------------+------+-----+---------+----------------+
    | targname        | varchar(30)  | NO   |     | NULL    |                |
    +-----------------+--------------+------+-----+---------+----------------+
    | cal_ver         | varchar(30)  | NO   |     | NULL    |                |
    +-----------------+--------------+------+-----+---------+----------------+
    | obstype         | varchar(30)  | NO   |     | NULL    |                |
    +-----------------+--------------+------+-----+---------+----------------+
    | cenwave         | int(11)      | NO   |     | NULL    |                |
    +-----------------+--------------+------+-----+---------+----------------+
    | aperture        | varchar(30)  | NO   |     | NULL    |                |
    +-----------------+--------------+------+-----+---------+----------------+
    | detector        | varchar(30)  | NO   |     | NULL    |                |
    +-----------------+--------------+------+-----+---------+----------------+
    | opt_elem        | varchar(30)  | NO   |     | NULL    |                |
    +-----------------+--------------+------+-----+---------+----------------+
    | fppos           | int(11)      | NO   |     | NULL    |                |
    +-----------------+--------------+------+-----+---------+----------------+

- **id** - A unique integer ID number that serves as primary key.
- **filename** - The filename of the observation.
- **path** - The location of the file in the HSTLC filesystem.
- **ingest_date** - The date of which the file was last ingested.
- **telescop** - The value of the observation's ``TELESCOP`` header keyword.  Currently, this is always ``HST``.
- **instrume** - The value of the observation's  ``INSTRUME`` header keyword. This is either ``COS`` or ``STIS``.
- **targname** - The value of the observation's ``TARGNAME`` header keyword (i.e. the target name of the                   observation).
- **cal_ver** - The value of the observation's ``CAL_VER`` header keyword (i.e. the version of the calibration pipeline that was used to calibrate the observation).
- **obstype** - The value of the observation's ``OBSTYPE`` header keyword.  This is either ``SPECTROSCOPIC`` or ``IMAGING``.
- **cenwave** - The value of the observation's ``CENWAVE`` header keyword (i.e. the central wavelength of the observation).
- **aperture** - The value of the observation's ``APERTURE`` header keyword (i.e. the aperture name).
- **detector** - The value of the observation's ``DETECTOR`` header keyword.  This is either ``FUV-MAMA`` or ``NUV-MAMA`` for STIS, or ``FUV`` or ``NUV`` for COS.
- **opt_elem** - The value of the observation's ``OPT_ELEM`` header keyword (i.e. the optical element used).
- **fppos** - The value of the observation's ``FPPOS`` header keyword (i.e. the grating offset index).


**Outputs Table**

The ``outputs`` table stores information about the output products associated with each filename from the ``metadata`` table. The table contains the following columns:

    +---------------------+--------------+------+-----+---------+----------------+
    | Field               | Type         | Null | Key | Default | Extra          |
    +---------------------+--------------+------+-----+---------+----------------+
    | id                  | int(11)      | NO   | PRI | NULL    | auto_increment |
    +---------------------+--------------+------+-----+---------+----------------+
    | metadata_id         | int(11)      | NO   | UNI | NULL    |                |
    +---------------------+--------------+------+-----+---------+----------------+
    | individual_path     | varchar(100) | YES  |     | NULL    |                |
    +---------------------+--------------+------+-----+---------+----------------+
    | individual_filename | varchar(30)  | YES  |     | NULL    |                |
    +---------------------+--------------+------+-----+---------+----------------+
    | composite_path      | varchar(100) | YES  |     | NULL    |                |
    +---------------------+--------------+------+-----+---------+----------------+
    | composite_filename  | varchar(30)  | YES  |     | NULL    |                |
    +---------------------+--------------+------+-----+---------+----------------+

1. **id** - A unique integer ID number that serves as primary key.
2. **metadata_id** - A foreign key that points to the primary ID of the ``metadata`` table. This will allow for the ``outputs`` table and the ``metadata`` table to join.
3. **individual_path** - The path to the individual lightcurve output file.
4. **individual_filename** - The filename of the individual lightcurve output file.
5. **composite_path** - The path to the composite lightcurve output file.
6. **composite_filename** - The filename of the composite lightcurve output file.


**Bad Data Table**

The ``bad_data`` table stores information about files that could not be ingested.  The table contains the following columns:

    +-------------+---------------------------------+------+-----+---------+----------------+
    | Field       | Type                            | Null | Key | Default | Extra          |
    +-------------+---------------------------------+------+-----+---------+----------------+
    | id          | int(11)                         | NO   | PRI | NULL    | auto_increment |
    +-------------+---------------------------------+------+-----+---------+----------------+
    | filename    | varchar(30)                     | NO   | UNI | NULL    |                |
    +-------------+---------------------------------+------+-----+---------+----------------+
    | ingest_date | date                            | NO   |     | NULL    |                |
    +-------------+---------------------------------+------+-----+---------+----------------+
    | reason      | enum('No events','Bad EXPFLAG') | NO   |     | NULL    |                |
    +-------------+---------------------------------+------+-----+---------+----------------+

1. **id** - A unique integer ID number that serves as the primary key.
2. **filename** - The filename of the observation that couldn't be ingested.
3. **ingest_date** - The date in which the file was attempted to be ingested.
4. **reason** - The reason why the file was not ingested.  Can either be ``No events`` (which corresponds to an observation with no observed signal) or ``Bad EXPFLAG`` (which corresponds to observations that have an ``EXPFLAG`` header keyword that is not ``NORMAL``).


Filesystem
----------

The ``corrtag``, and ``x1d`` files are stored in a directory structure located in the ``filesystem/`` directory on central storage.  The files are stored in a subdirectory associated with their ``TARGNAME`` header keyword.  For example:

```
filesystem/
    TARGNAME1/
        file1_corrtag.fits
        file1_x1d.fits
        file2_corrtag.fits
        file2_x1d.fits
    TARGNAME2/
        ...
    TARGNAME3/
        ...
    ...
```

Files are moved from the ``ingest/`` directory to their appropriate subdirectory in ``filesystem/`` as determined by the logic in the [ingest_hstlc](https://github.com/justincely/lightcurve_pipeline/blob/master/scripts/ingest_hstlc) script.  The permissions of the directories and files are governed by ``set_permissions`` function in the [utils](https://github.com/justincely/lightcurve_pipeline/blob/master/lightcurve_pipeline/utils/utils.py) module.

The filesystem can be "reset" by the [reset_hstlc_filesystem](https://github.com/justincely/lightcurve_pipeline/blob/master/scripts/reset_hstlc_filesystem) script. This will move files from the ``filesystem/`` directory back to the ``ingest/`` directory and remove the subdirectories under ``filesystem/``.


Permissions
-----------

Downloads
---------

High Level Science Products
---------------------------

System Requirements
===================

System requirements


Installation
============

installation


Package Structure
=================

Package structure


Useage
======

Usage