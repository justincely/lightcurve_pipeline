About HSTLC
===========

Welcome to the HSTLC (**H**\ubble **S**\pace **T**\elescope **L**\ight **C**\urve) project

The HSTLC project aims to produce high level science products in the form of flux calibrated, UV lightcurves for all publicly available HST/COS and HST/STIS TIME-TAG datasets. This documenation provides an overview to the project, details about the implemented software systems, and a description of the output products.


Overview
--------

The Cosmic Origins Spectrograph (COS) and the Space Telescope Imaging Spectrograph (STIS) on board the Hubble Space Telescope (HST) continue to capture spectroscopic observations and deliver them to a steadily-growing archive. Observation products are primarily in the form of time-average spectra, however there exist many COS and STIS observations taken in the TIME-TAG observing mode wherein the position and time of each incoming photon is recorded. This results is an observation product in the form of a list of detected events, which can in turn be transformed into a lightcurve that can be used to discover and characterize unique phenomena in scientific observations.

The Hubble Space Telescope Light Curve (HSTLC) project aims to gather TIME-TAG observations and transform them into High Level Science Products (HLSPs) in the form of lightcurves in an automated way for all publicly available COS and STIS TIME-TAG observations. The project software is written in Python, and uses many supporting materials, including a `pipeline <file:///user/bourque/repositories/lightcurve_pipeline/docs/build/html/readme.html#pipeline>`_, `filesystem <file:///user/bourque/repositories/lightcurve_pipeline/docs/build/html/readme.html#filesystem>`_, `database <file:///user/bourque/repositories/lightcurve_pipeline/docs/build/html/readme.html#database>`_, `downloading platform <file:///user/bourque/repositories/lightcurve_pipeline/docs/build/html/readme.html#downloads>`_, and a `lightcurve code library <https://github.com/justincely/lightcurve_pipeline>`_.

This project is supported by the `Hubble Archival Research program 13902 <http://www.stsci.edu/cgi-bin/get-proposal-info?id=13902&submit=Go&observatory=HST>`_. (P.I. Justin Ely)


Pipeline
--------

The conversion of raw TIME-TAG observations to high-level science products (lightcurves) is mainly performed by the `ingest_hstlc <https://github.com/justincely/lightcurve_pipeline/blob/master/scripts/ingest_hstlc>`_ script.  The following algorithm is employed by ``ingest_hstlc``:

1. Gather ``x1d``, ``tag``, and ``corrtag`` files from the ``ingest directory`` to build a list of files to ingest.
2. For each ``tag`` or ``corrtag`` file:
  a. Open the file to retrieve the header and data.
  b. If there is no data in the file, update the ``bad_data`` table in the `hstlc Database <file:///user/bourque/repositories/lightcurve_pipeline/docs/build/html/readme.html#database>`_ and remove the file from the ``ingest`` directory.
  c. Check the ``EXPFLAG`` header keyword.  If the value is not ``NORMAL``, then update the ``bad_data`` table and remove the file from the ``ingest`` directory.
  d. Gather metadata and output location information from the file.
  e. If the file is a ``STIS`` dataset, then convert the ``tag`` file into a ``corrtag`` file by calling the ``stis_corrtag`` function of the `lightcurve <https://github.com/justincely/lightcurve>`_ library.
  f. Update the ``metadata`` table in the ``hstlc Database`` with the metadata of the file.
  g. Create the lightcurve using the `lightcurve <https://github.com/justincely/lightcurve>`_ library code and place the output product in the appropriate ``outputs`` directory based on the file's ``TARGNAME``.
  h. Set the correct permissions of the output directory and/or files.
  i. Update the ``outputs`` table of the ``hstlc Database`` with output location information.
  j. Create a quicklook image for the observation and save it in the appropriate ``outputs`` directory.
  k. Move the file from the ``ingest`` directory to the appropriate directory in the filesystem.
3. Use the ``metadata`` table to query for datasets that require (re)processing of composite lightcurves based on if new files have been ingested.
4. (re)Create a composite lightcurve for each dataset that requires (re)processing and save the composite lightcurve in the appropriate ``outputs`` directory.
5. Update the ``outputs`` table of the ``hstlc Database`` with composite lightcurve output location information.


Database
--------

The ``hstlc`` pipeline uses a MySQL database to store useful metadata and file location information for each dataset.  The database schema is defined by the Object-Relational Mappings (ORMs) contained in `database_interface <https://github.com/justincely/lightcurve_pipeline/blob/master/lightcurve_pipeline/database/database_interface.py>`_ module.  Below is a description of each table.  The database is populated by the `ingest_hstlc <https://github.com/justincely/lightcurve_pipeline/blob/master/scripts/ingest_hstlc>`_ script.  The database can also easily be reset by the `reset_hstlc_database <https://github.com/justincely/lightcurve_pipeline/blob/master/scripts/reset_hstlc_database>`_ script.

**Metadata Table**

The ``metadata`` table stores information about each observations location in the HSTLC filesystem as well as useful header keyword values.  The table contains the following columns:


Filesystem
----------

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