"""Module for updating databases by ingest
"""

import datetime
import logging

from lightcurve_pipeline.database.database_interface import engine
from lightcurve_pipeline.database.database_interface import session
from lightcurve_pipeline.database.database_interface import Metadata
from lightcurve_pipeline.database.database_interface import Outputs
from lightcurve_pipeline.database.database_interface import BadData
from lightcurve_pipeline.utils.utils import insert_or_update

# -----------------------------------------------------------------------------

def update_bad_data_table(filename, reason):
    """Insert or update a record pertaining to the filename in the
    bad_data table.

    Parameters
    ----------
    filename : string
        The filename of the file.
    reason : string
        The reason that the data is bad. Can either be 'No events' or
        'Bad EXPFLAG'.
    """

    # Build dictionary containing data to store
    bad_data_dict = {}
    bad_data_dict['filename'] = filename
    bad_data_dict['ingest_date'] = datetime.datetime.strftime(
        datetime.datetime.today(), '%Y-%m-%d')
    bad_data_dict['reason'] = reason

    # The the id of the record, if it exists
    query = session.query(BadData.id)\
        .filter(BadData.filename == filename).all()
    if query == []:
        id_num = ''
    else:
        id_num = query[0][0]

    # If id doesn't exist then instert.  If id exists, then update
    insert_or_update(BadData, bad_data_dict, id_num)

# -----------------------------------------------------------------------------

def update_metadata_table(metadata_dict):
    """Insert or update a record in the metadata table containing the
    metadata_dict information.

    Parameters
    ----------
    metadata_dict : dict
        A dictionary containing metadata of the file.  Each key of the
        metadata_dict corresponds to a column in the matadata table of the
        database.
    """

    logging.info('\tUpdating metadata table.')

    # Get the id of the record, if it exists
    query = session.query(Metadata.id)\
        .filter(Metadata.filename == metadata_dict['filename']).all()
    if query == []:
        id_num = ''
    else:
        id_num = query[0][0]

    # If id doesn't exist then insert. If id exsits, then update
    insert_or_update(Metadata, metadata_dict, id_num)

# -----------------------------------------------------------------------------

def update_outputs_table(metadata_dict, outputs_dict):
    """Insert or update a record in the outputs table containing
    output product information.

    Parameters
    ----------
    metadata_dict : dict
        A dictionary containing metadata of the file.
    outputs_dict : dict
        A dictionary containing output product information.
    """

    logging.info('\tUpdating outputs table.')

    # Get the metadata_id
    session.rollback()
    metadata_id_query = session.query(Metadata.id)\
        .filter(Metadata.filename == metadata_dict['filename']).all()
    metadata_id = metadata_id_query[0][0]
    outputs_dict['metadata_id'] = metadata_id

    # Get the id of the outputs record, if it exists
    id_query = session.query(Outputs.id)\
        .join(Metadata)\
        .filter(Metadata.filename == metadata_dict['filename']).all()
    if id_query == []:
        id_num = ''
    else:
        id_num = id_query[0][0]

    # If id doesn't exist then insert. If id exsits, then update
    insert_or_update(Outputs, outputs_dict, id_num)
