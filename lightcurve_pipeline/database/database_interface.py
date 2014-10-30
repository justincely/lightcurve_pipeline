"""Connection module for the hstlc database
"""

from lightcurve_pipeline.settings.settings import SETTINGS

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from sqlalchemy import Column
from sqlalchemy import Date
from sqlalchemy import Float
from sqlalchemy import Integer
from sqlalchemy import String

# -----------------------------------------------------------------------------

def load_connection(connection_string, echo=False):
    """Create and return a connection to the database given in the
    connection string.

    Parameters
    ----------
    connection_string : str
        A string that points to the database conenction.  The
        connection string is in the following form:
        dialect+driver://username:password@host:port/database
    echo : bool
        Show all SQL produced.

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
    centrwv = Column(Float(), nullable=False)
    aperture = Column(String(30), nullbale=False)
    detector = Column(String(30), nullable=False)
    opt_elem = Column(String(30), nullable=False)
    ffpos = Column(Integer(), nullable=False)
    output_filename = Column(String(30))
    output_path = Column(String(100))

# -----------------------------------------------------------------------------

if __name__ == '__main__':

    base.metadata.create_all()
