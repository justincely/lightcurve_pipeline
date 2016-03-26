Overview
--------

The Cosmic Origins Spectrograph (COS) and the Space Telescope Imaging Spectrograph (STIS) on board the Hubble Space Telescope (HST) continue to capture spectroscopic observations and deliver them to a steadily-growing archive. Observation products are primarily in the form of time-average spectra, however there exist many COS and STIS observations taken in the TIME-TAG observing mode wherein the position and time of each incoming photon is recorded. This results in an observation product in the form of a list of detected events, which can in turn be transformed into a lightcurve that can be used to discover and characterize unique phenomena in scientific observations.

The hstlc project aims to gather TIME-TAG observations and transform them into High Level Science Products (HLSPs) in the form of lightcurves in an automated way for all publicly available COS and STIS TIME-TAG observations. The project software is written in Python, and uses many supporting materials, including a `pipeline <http://pythonhosted.org/lightcurve-pipeline/readme.html#id1>`_, `database <http://pythonhosted.org/lightcurve-pipeline/readme.html#id3>`_, `filesystem <http://pythonhosted.org/lightcurve-pipeline/readme.html#id5>`_, `downloading platform <http://pythonhosted.org/lightcurve-pipeline/readme.html#downloads>`_, and a `lightcurve code library <http://justincely.github.io/lightcurve/>`_.

This project is supported by the `Hubble Archival Research program 13902 <http://www.stsci.edu/cgi-bin/get-proposal-info?id=13902&submit=Go&observatory=HST>`_. (P.I. Justin Ely)


Filetypes
---------

TIME-TAG observations are stored in FITS binary tables.  Depending on the instrument and detector of the observation, the FITS files can have several different naming conventions, as describe below:

(1) ``<rootname>_tag.fits`` - STIS TIME-TAG observation
(2) ``<rootname>_corrtag.fits`` - COS TIME-TAG observation taken with the NUV detector
(3) ``<rootname>_corrtag_a.fits`` - COS TIME-TAG observation taken with the FUV-A detector
(4) ``<rootname>_corrtag_b.fits``- COS TIME-TAG observation taken with the FUV-B detector

Additionally, ``<rootname>_x1d.fits`` files, which store the 1-dimensional extracted spectra, are used by various routines in the ``lightcurve`` library to perform extraction.  Thus, these filetypes are also downloaded and ingested by the hstlc pipeline.

Further details about these filetypes and TIME-TAG observations in general can be found in the `COS Data Handbook <http://www.stsci.edu/hst/cos/documents/handbooks/datahandbook/COS_cover.html>`_ and the `STIS Data Handbook <http://www.stsci.edu/hst/stis/documents/handbooks/currentDHB/stis_cover.html>`_.


Pipeline
--------

The hstlc pipeline is a series of scripts, executed sequentially, that ingests raw TIME-TAG observations and produces lightcurves as well as various plots that analyze them.  The pipeline consists of three scripts:
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
      (f) Create the lightcurve using the `lightcurve <http://justincely.github.io/lightcurve/>`_ library code and place the output product in the appropriate ``outputs`` directory based on the file's ``TARGNAME``.
      (g) Set the correct permissions of the output directory and/or files.
      (h) Update the ``outputs`` table of the hstlc Database with output location information.
      (i) Create a quicklook image for the observation and save it in the appropriate ``outputs`` directory.
      (j) Move the file (and its accompanying ``x1d`` file) from the ``ingest`` directory to the appropriate directory in the filesystem.
    (3) Use the ``metadata`` table to query for datasets that require (re)processing of composite lightcurves based on if new files have been ingested.
    (4) (re)Create a composite lightcurve for each dataset that requires (re)processing and save the composite lightcurve in the appropriate ``outputs`` directory.
    (5) Update the ``outputs`` table of the ``hstlc Database`` with composite lightcurve output location information.

**build_stats_table**

After the TIME-TAG observations are ingested and output lightcurves are produced, the ``build_stats_table`` script calculates various statistics for each individual and composite lightcurve and stores the statistics in the ``stats`` table in the hstlc database.  The following statistics are calculated:

    (1) ``total`` - The total number of counts in the lightcurve
    (2) ``mean`` The mean number of counts in the lightcurve
    (3) ``mu`` - The square root of the mean number of counts
    (4) ``stdev`` - The standard deviation of the counts in the lightcurve
    (5) ``poisson_factor`` - The ``stdev``/``mu`` of the lightcurve.  The greater the ``poisson_factor``, the less likely that noise in the lightcurve is due to Poisson noise.
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

The hstlc project uses a MySQL database to store useful data.  The database schema is defined by the Object-Relational Mappings (ORMs) contained in the `database_interface <https://github.com/justincely/lightcurve_pipeline/blob/master/lightcurve_pipeline/database/database_interface.py>`_ module.  The database is populated by the ``ingest_hstlc`` and ``build_stats_table`` scripts.  The database can also easily be reset by the `reset_hstlc_database <http://pythonhosted.org/lightcurve-pipeline/hstlc_scripts.html#module-lightcurve_pipeline.scripts.reset_hstlc_database`_ script.  Below is a description of each table.

**Metadata Table**

The ``metadata`` table stores information about each observations location in the hstlc filesystem as well as useful header keyword values.  The table contains the following columns:

    +-----------------+--------------+------+-----+---------+----------------+
    | Field           | Type         | Null | Key | Default | Extra          |
    +=================+==============+======+=====+=========+================+
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

- ``id`` - A unique integer ID number that serves as primary key.
- ``filename`` - The filename of the observation.
- ``path`` - The location of the file in the HSTLC filesystem.
- ``ingest_date`` - The date of which the file was last ingested.
- ``telescop`` - The value of the observation's ``TELESCOP`` header keyword.  Currently, this is always ``HST``.
- ``instrume`` - The value of the observation's  ``INSTRUME`` header keyword. This is either ``COS`` or ``STIS``.
- ``targname`` - The value of the observation's ``TARGNAME`` header keyword (i.e. the target name of the                   observation).
- ``cal_ver`` - The value of the observation's ``CAL_VER`` header keyword (i.e. the version of the calibration pipeline that was used to calibrate the observation).
- ``obstype`` - The value of the observation's ``OBSTYPE`` header keyword.  This is either ``SPECTROSCOPIC`` or ``IMAGING``.
- ``cenwave`` - The value of the observation's ``CENWAVE`` header keyword (i.e. the central wavelength of the observation).
- ``aperture`` - The value of the observation's ``APERTURE`` header keyword (i.e. the aperture name).
- ``detector`` - The value of the observation's ``DETECTOR`` header keyword.  This is either ``FUV-MAMA`` or ``NUV-MAMA`` for STIS, or ``FUV`` or ``NUV`` for COS.
- ``opt_elem`` - The value of the observation's ``OPT_ELEM`` header keyword (i.e. the optical element used).
- ``fppos`` - The value of the observation's ``FPPOS`` header keyword (i.e. the grating offset index).


**Outputs Table**

The ``outputs`` table stores information about the output products associated with each filename from the ``metadata`` table. The table contains the following columns:

    +---------------------+--------------+------+-----+---------+----------------+
    | Field               | Type         | Null | Key | Default | Extra          |
    +=====================+==============+======+=====+=========+================+
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

- ``id`` - A unique integer ID number that serves as primary key.
- ``metadata_id`` - A foreign key that points to the primary ID of the ``metadata`` table. This will allow for the ``outputs`` table and the ``metadata`` table to join.
- ``individual_path`` - The path to the individual lightcurve output file.
- ``individual_filename`` - The filename of the individual lightcurve output file.
- ``composite_path`` - The path to the composite lightcurve output file.
- ``composite_filename`` - The filename of the composite lightcurve output file.


**Bad Data Table**

The ``bad_data`` table stores information about files that could not be ingested.  The table contains the following columns:

    +-------------+----------------------------------------------------------------------------------------------------+------+-----+---------+----------------+
    | Field       | Type                                                                                               | Null | Key | Default | Extra          |
    +=============+====================================================================================================+======+=====+=========+================+
    | id          | int(11)                                                                                            | NO   | PRI | NULL    | auto_increment |
    +-------------+----------------------------------------------------------------------------------------------------+------+-----+---------+----------------+
    | filename    | varchar(30)                                                                                        | NO   | UNI | NULL    |                |
    +-------------+----------------------------------------------------------------------------------------------------+------+-----+---------+----------------+
    | ingest_date | date                                                                                               | NO   |     | NULL    |                |
    +-------------+----------------------------------------------------------------------------------------------------+------+-----+---------+----------------+
    | reason      | enum('Bad EXPFLAG','Non-linear time','No events','Singular event','Bad Proposal','Short Exposure') | NO   |     | NULL    |                |
    +-------------+----------------------------------------------------------------------------------------------------+------+-----+---------+----------------+

- ``id`` - A unique integer ID number that serves as the primary key.
- ``filename`` - The filename of the observation that couldn't be ingested.
- ``ingest_date`` - The date in which the file was attempted to be ingested.
- ``reason`` - The reason why the file was not ingested.  Can either be:
   - ``Bad EXPFLAG``, which corresponds to observations that have an ``EXPFLAG`` header keyword that is not ``NORMAL``
   - ``Non-linear time``, which indicates that time does not progress linearly through the ``TIME`` column of the dataset
   - ``No events``, which corresponds to an observation with no observed signal
   - ``Singular event``, which indicates that all events a dataset occur at a single time
   - ``Bad Proposal``, which indicates that the dataset is part of a problematic proposal
   - ``Short Exposure``, which indicates that the exposure time of the dataset is too short

**Stats Table**

The ``stats`` table stores useful statistics for each individual and composite lightcurve.  The table contains the following columns:

    +---------------------+--------------+------+-----+---------+----------------+
    | Field               | Type         | Null | Key | Default | Extra          |
    +=====================+==============+======+=====+=========+================+
    | id                  | int(11)      | NO   | PRI | NULL    | auto_increment |
    +---------------------+--------------+------+-----+---------+----------------+
    | lightcurve_path     | varchar(100) | NO   |     | NULL    |                |
    +---------------------+--------------+------+-----+---------+----------------+
    | lightcurve_filename | varchar(100) | NO   |     | NULL    |                |
    +---------------------+--------------+------+-----+---------+----------------+
    | total               | int(11)      | NO   |     | NULL    |                |
    +---------------------+--------------+------+-----+---------+----------------+
    | mean                | float        | YES  |     | NULL    |                |
    +---------------------+--------------+------+-----+---------+----------------+
    | mu                  | float        | YES  |     | NULL    |                |
    +---------------------+--------------+------+-----+---------+----------------+
    | stdev               | float        | YES  |     | NULL    |                |
    +---------------------+--------------+------+-----+---------+----------------+
    | poisson_factor      | float        | YES  |     | NULL    |                |
    +---------------------+--------------+------+-----+---------+----------------+
    | pearson_r           | float        | YES  |     | NULL    |                |
    +---------------------+--------------+------+-----+---------+----------------+
    | pearson_p           | float        | YES  |     | NULL    |                |
    +---------------------+--------------+------+-----+---------+----------------+
    | periodogram         | tinyint(1)   | NO   |     | NULL    |                |
    +---------------------+--------------+------+-----+---------+----------------+
    | deliver             | tinyint(1)   | NO   |     | NULL    |                |
    +---------------------+--------------+------+-----+---------+----------------+


Filesystem
----------

The hstlc filesystem has several top-level directories:

(1) ``ingest/`` - Stores files that are to be ingested
(2) ``bad_data/`` - Stores the files that do not pass the quality checks during ingestion
(3) ``filesystem/`` - Stores the ingested data based on ``TARGNAME`` (see notes below)
(4) ``outputs/`` - Stores the individual and composite lightcurves, as well as the quicklook PNG plots
(5) ``plots/`` - Stores the various plots created from the ``make_hstlc_plots`` script
(6) ``download/`` - Stores the returned XML request files from MAST indicating success or failure
(7) ``logs/`` - Stores the log files that log the execution of the hstlc scripts

The various TIME-TAG files are stored in a directory structure located in the ``filesystem/`` directory.  The files are stored in a subdirectory associated with their ``TARGNAME`` header keyword.  For example:

::

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


Files are moved from the ``ingest`` directory to their appropriate subdirectory in ``filesystem`` as determined by the logic in the ``ingest_hstlc`` script.  A similar structure is used for the ``outputs`` directory, with the exception of the ``composite`` subdirectory, which stores composite lightcurves:

::

    outputs/
        TARGNAME1/
            file1_curve.fits
            file2_curve.fits
            file3_curve.fits
        TARGNAME2/
            ...
        TARGNAME3/
            ...
        composite/
            composite_file1_curve.fits
            composite_file2_curve.fits
            composite_file3_curve.fits
            ...


The ``filesystem`` and ``outputs`` directories can be 'reset' by the `reset_hstlc_filesystem <http://pythonhosted.org/lightcurve-pipeline/hstlc_scripts.html#module-lightcurve_pipeline.scripts.reset_hstlc_filesystem>`_ script. This will move files from the ``filesystem`` directory back to the ``ingest`` directory and remove the subdirectories under ``filesystem``, as well as remove all of the files are subdirectories from the ``outputs`` directory.


Permissions
-----------

The permissions of hstlc data files, directories, subdirectories, logs, and output products are all uniformly set.  The permissions are governed by the ``set_permissions`` function of the `utils <http://pythonhosted.org/lightcurve-pipeline/hstlc_modules.html#module-lightcurve_pipeline.utils.utils>`_ module.

All permissions are set to ``rwxrwx---`` with ``STSCI/hstlc`` group permissions.


Downloads
---------

New COS and STIS TIME-TAG observations are retrieved from the MAST archive on a periodic basis.  This is done by the `download_hstlc <http://pythonhosted.org/lightcurve-pipeline/hstlc_scripts.html#module-lightcurve_pipeline.scripts.download_hstlc>`_ script.  The script queries the ``dadsops_rep`` table in the MAST archive for new datasets based on the following query:

.. code-block:: sql

    SELECT asm_member_name
    FROM assoc_member
    WHERE asm_member_type IN ('EXP-FP', 'SCIENCE')
    AND asm_asn_id IN (SELECT sci_data_set_name
                       FROM science
                       WHERE sci_instrume IN ('COS', 'STIS')
                       AND sci_operating_mode = 'TIME-TAG'
                       AND sci_targname NOT IN ('DARK', 'BIAS', 'DEUTERIUM', 'WAVE', 'ANY', 'NONE')
                       AND sci_release_date < <today>)

As you can see, the query avoids certain targets that do not contain any useful data (e.g. ``DARK``, ``BIAS``, etc.).  The query also uses the ``assoc_member`` table to determine individual association members.


High Level Science Products
---------------------------

The composite lightcurves that are created by the hstlc pipeline are delivered to MAST as High Level Science Products (HLSPs).  A composite lightcurve is comprised of one or more individual lightcurves, all having the same configuration of ``TARGNAME``, ``DETECTOR``, ``OPT_ELEM``, and ``CENWAVE``.  In other words, all datasets taken under the same observing conditions are aggregated together to form a composite lightcurve.

The composite lightcurves are FITS binary tables consisting of the following columns:

(1) ``bins`` - the stepsize in which events are binned, in seconds (i.e. a bin of 1 means that all events are binned into 1-second intervals)
(2) ``times`` - the times of each event in the dataset, relative the the start of the observation
(3) ``mjd`` - the Modified Julian Date of each event in the dataset
(4) ``gross`` - the total number of counts in the dataset
(5) ``counts`` - calculated as the ``gross - background``
(6) ``net`` - calculated as ``counts / time``
(7) ``flux`` - the flux of each event in ergs/s
(8) ``flux_error`` - the error of each flux measurement, in ergs/s
(9) ``background`` - the background measurement for each event, in counts
(10) ``error`` - calculated as the ``sqrt(gross + background)``
(11) ``dataset`` - the dataset that the event corresponds to (i.e. dataset=2 corresponds to the second individual lightcurve that comprises the composite lightcurve)

As to adhere to the `MAST HSLP contribution guidelines for times-series/lightcurves <https://archive.stsci.edu/hlsp/hlsp_guidelines_timeseries.html>`_, the following naming convention is used for the composite lightcurves:

::

    hlsp_hstlc_hst_<instrument>-<detector>_<targname>_<opt_elem>_<cenwave>_v1_sci.fits

where:
    - ``instrument`` is the instrument (``cos`` or ``stis``)
    - ``detector`` is the detector (``nuv-mama`` or ``fuv-mama`` for STIS, ``nuv`` or ``fuv`` for COS)
    - ``targname`` is the target name (e.g. ``ngc6905``)
    - ``opt_elem`` is the filter (e.g. ``e230m``)
    - ``cenwave`` is the central wavelength (e.g. ``2561``)


Installation
============

Users must first install the `lightcurve <http://justincely.github.io/lightcurve/>`_ package.  Users can obtain the latest release using pip:

::

    >>> pip install lightcurve

or by downloading/cloning the code from `GitHub <https://github.com/justincely/lightcurve>`_ and running ``setup.py``:

::

    >>> git clone https://github.com/justincely/lightcurve.git
    >>> python setup.py install


Similarly, users can install the ``lightcurve_pipeline`` package via ``pip``:

::

    >>> pip install lightcurve_pipeline

or by downloading/cloning from `GitHub <https://github.com/justincely/lightcurve_pipeline>`_ and running ``setup.py``:

::

    >>> git clone https://github.com/justincely/lightcurve_pipeline
    >>> python setup.py install


Package Structure
=================

The ``lightcurve_pipeline`` package has the following structure:

::

    lightcurve_pipeline/
        database/
            database_interface.py
        download/
            SignStsciRequest.py
        ingest/
            make_lightcurve.py
            resolve_target.py
        quality/
            data_checks.py
        scripts/
            build_stats_table.py
            download_hstlc.py
            ingest_hstlc.py
            make_hstlc_plots.py
            reset_hstlc_database.py
            reset_hstlc_filesystem.py
        utils/
            config.yaml
            periodogram_stats.py
            targname_dict.py
            utils.py
    scripts/
        hsltc_pipeline
    setup.py

Note that the ``hstlc_pipeline`` exists outside of the package itself.  Additionally, the ``setup.py`` module defines the scripts under the ``lightcurve_pipeline.scripts`` directory as ``entry_points``, so that these scripts can be executed from the command line.


System Requirements
===================

The hstlc software requires Python 2.7 and the following external libraries:

    - ``astropy``
    - ``bokeh``
    - ``lightcurve``
    - ``matplotlib``
    - ``numpy``
    - ``pyyaml``
    - ``scipy``
    - ``sqlalchmy``

Also required is a configuration files named ``config.yaml`` placed in the ``lightcurve_pipeline.utils`` directory.  This config file holds the hard-coded paths that determine the various hstlc directories (e.g. ``filesystem/``, ``outputs/``, etc.) as well as the connection credentials to the hstlc database.  Thus, a ``config.yaml`` file presumably looks like:

.. code-block:: sql

    'db_connection_string' : 'mysql+pymysql://username:password@hostname:port/hstlc'
    'home_dir' : '/mydir/'
    'ingest_dir' : '/mydir/ingest/'
    'filesystem_dir' : '/mydir/filesystem/'
    'outputs_dir' : '/mydir/outputs/'
    'composite_dir' : '/mydir/outputs/composite/'
    'log_dir' : '/mydir/logs/'
    'download_dir' : '/mydir/download/'
    'plot_dir' : '/mydir/plots/'
    'bad_data_dir' : '/mydir/bad_data/'

Users wishing to run the pipeline must ensure that these directories exist, and have proper `hstlc permissions <file:///user/bourque/repositories/lightcurve_pipeline/docs/build/html/readme.html#permissions>`_.

Useage
======

Users can run the pipeline by simply executing the ``hstlc_pipeline`` script:

::

    >>> hstlc_pipeline [-corrtag_extract]

Supplying the ``-corrtag_extract`` parameter is optional, and will cause the extraction of corrtag data to be performed.

Users can also execute individual parts of the pipeline, as such:

::

    >>> ingest_hstlc [-corrtag_extract]
    >>> build_stats_table
    >>> make_hstlc_plots

Users wishing to download new TIME-TAG data can execute the ``download_hstlc`` script:

::

    >>> download_hstlc

Users wishing to reset the hstlc filesystem or database can execute the ``reset_hstlc_filesytem`` and ``reset_hstlc_database`` scripts, respectively:

    >>> reset_hstlc_filesystem
    >>> reset_hstlc_database [table]

See the `rest_hstlc_database documentation <http://pythonhosted.org/lightcurve-pipeline/hstlc_scripts.html#module-lightcurve_pipeline.scripts.reset_hstlc_database>`_ for further details on the use of the ``table`` parameter.