"""
This module serves as the interface and connection module to the hstlc
database.  The ``load_connection()`` function within allows the user
to conenct to the database via the ``session``, ``base``, and
``engine`` objects (described below).  The classes within serve as the
object-relational mappings (ORMs) that define the individual tables of
the database, and are used to build the tables via the ``base`` object.

The ``engine`` object serves as the low-level database API and perhaps
most importantly contains dialects which allows the sqlalchemy module
to communicate with the database.

The ``base`` object serves as a base class for class definitions.  It
produces ``Table`` objects and constructs ORMs.

The ``session`` object manages operations on ORM-mapped objects, as
construced by the ``base``.  These operations include querying, for
example.

**Authors:**

    Matthew Bourque

**Use:**

    This module is intended to be imported from various hstlc modules
    and scripts.  The objects that are importable from this module are
    as follows:

::

    from lightcurve_pipeline.database.database_interface import engine
    from lightcurve_pipeline.database.database_interface import base
    from lightcurve_pipeline.database.database_interface import session
    from lightcurve_pipeline.database.database_interface import Metadata
    from lightcurve_pipeline.database.database_interface import Outputs
    from lightcurve_pipeline.database.database_interface import BadData
    from lightcurve_pipeline.database.database_interface import Stats

**Dependencies:**

    (1) Users must have access to the hstlc database
    (2) Users must also have a ``config.yaml`` file located in the
        ``lightcurve_pipeline/utils/`` directory with the following
        keys:

        - ``db_connection_string`` - The hstlc database connection
          string

    Other external library dependencies include:
        - ``pymysql``
        - ``sqlalchemy``
        - ``lightcurve_pipeline``
"""

import pymysql
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import Date
from sqlalchemy import Enum
from sqlalchemy import Float
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String

from lightcurve_pipeline.utils.utils import SETTINGS

# -----------------------------------------------------------------------------

def get_session():
    """Return the ``session`` object of the database connection

    In many cases, all that is needed is the ``session`` object to
    interact with the database.  This function can be used just to
    establish a connection and retreive the ``session`` object.

    Returns
    -------
    session : sqlalchemy.orm.session.Session
        Provides a holding zone for all objects loaded or associated
        with the database.
    """

    session, base, engine = load_connection(SETTINGS['db_connection_string'])

    return session

# -----------------------------------------------------------------------------

def load_connection(connection_string, echo=False):
    """Create and return a connection to the database given in the
    connection string.

    Parameters
    ----------
    connection_string : str
        A string that points to the database conenction.  The
        connection string is in the following form:
        ``dialect+driver://username:password@host:port/database``
    echo : bool
        Show all SQL produced

    Returns
    -------
    session : sesson object
        Provides a holding zone for all objects loaded or associated
        with the database.
    base : base object
        Provides a base class for declarative class definitions.
    engine : engine object
        Provides a source of database connectivity and behavior.
    """

    engine = create_engine(connection_string, echo=echo)
    base = declarative_base(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    return session, base, engine

session, base, engine = load_connection(SETTINGS['db_connection_string'])

# -----------------------------------------------------------------------------
# Define ORMs
# -----------------------------------------------------------------------------

class Metadata(base):
    """ORM for the metadata table"""

    __tablename__ = 'metadata'
    id = Column(Integer(), nullable=False, primary_key=True)
    filename = Column(String(30), unique=True, nullable=False, index=True)
    path = Column(String(100), nullable=False)
    ingest_date = Column(Date, nullable=False)
    telescop = Column(String(10), nullable=False)
    instrume = Column(String(10), nullable=False)
    targname = Column(String(30), nullable=False)
    cal_ver = Column(String(30), nullable=False)
    obstype = Column(String(30), nullable=False)
    cenwave = Column(Integer(), nullable=False)
    aperture = Column(String(30), nullable=False)
    detector = Column(String(30), nullable=False)
    opt_elem = Column(String(30), nullable=False)
    fppos = Column(Integer(), nullable=False)


class Outputs(base):
    """ORM for the outputs table"""
    __tablename__ = 'outputs'
    id = Column(Integer(), nullable=False, primary_key=True)
    metadata_id = Column(Integer(), ForeignKey('metadata.id'), nullable=False,
        unique=True)
    individual_path = Column(String(100))
    individual_filename = Column(String(30))
    composite_path = Column(String(100))
    composite_filename = Column(String(100))


class BadData(base):
    """ORM for bad_data table"""
    __tablename__ = 'bad_data'
    id = Column(Integer(), nullable=False, primary_key=True)
    filename = Column(String(30), unique=True, nullable=False, index=True)
    ingest_date = Column(Date, nullable=False)
    reason = Column(Enum('Bad EXPFLAG', 'Non-linear time', 'No events', 'Singular event', 'Bad Proposal', 'Short Exposure'), nullable=False)


class Stats(base):
    """ORM for stats table"""
    __tablename__ = 'stats'
    id = Column(Integer(), nullable=False, primary_key=True)
    lightcurve_path = Column(String(100), nullable=False)
    lightcurve_filename = Column(String(100), nullable=False)
    total = Column(Integer(), nullable=False)
    mean = Column(Float(10), nullable=True)
    mu = Column(Float(10), nullable=True)
    stdev = Column(Float(10), nullable=True)
    poisson_factor = Column(Float(10), nullable=True)
    pearson_r = Column(Float(10), nullable=True)
    pearson_p = Column(Float(10), nullable=True)
    periodogram = Column(Boolean(), nullable=False, default=False)
    deliver = Column(Boolean(), nullable=False, default=False)
