"""
This module contains functions that attempt to resolve target names
(i.e. ``TARGNAME``) to a more common option, if possible.  The method
for doing this is as follows:

    (1) Look up the ``targname`` from the hard-coded ``targname_dict``
        dictionary. If it exists, then use that ``targname``
    (2) If no dictionary entry exists, look up the ``targname`` in the
        CDS web service[1]
    (3) If the CDS web service returns resolved target names, and one
        of those target names already exists in the ``metadata`` table,
        then use that ``targname``
    (4) If the ``targname`` cannot be resolved through any of these
        steps, then use the original ``targname``

The hard-coded ``targname_dict`` dictionary resides in the
``utils.targname_dict`` module.

**Authors:**

    Justin Ely, Matthew Bourque

**Use:**

    This module is intended to be imported from and used by the
    ``ingest_hstlc`` script as such:

::

    from lightcurve_pipeline.ingest.resolve_target import get_targname
    get_targname(targname)

**Dependencies:**

    (1) Users must have access to the CDS web service
    (2) Users must have access to the hstlc database
    (3) Users must have a ``config.yaml`` file located in the
        ``lightcurve_pipeline/utils/`` directory with the following
        keys:

        - ``db_connection_string`` - The hstlc database connection
          string

    Other external library dependencies include:
        - ``pymysql``
        - ``sqlalchemy``
        - ``lightcurve``
        - ``lightcurve_pipeline``

**References:**

    [1] Centre de Donnees astronomiques de Strasbourg
    (http://cdsweb.u-strasbg.fr/)
"""

import urllib2
from xml.dom import minidom

from lightcurve_pipeline.utils.utils import SETTINGS
from lightcurve_pipeline.utils.targname_dict import targname_dict
from lightcurve_pipeline.database.database_interface import get_session
from lightcurve_pipeline.database.database_interface import Metadata

#------------------------------------------------------------------------------

def get_targname(targname):
    """Resolve the ``targname`` to a better option, if available.  If
    the ``targname`` cannot be resolved, the original ``targname`` is
    returned.

    Parameters
    ----------
    targname : str
        The name of the target

    Returns
    -------
    new_targname: str
        The resolved target name
    """

    # Assume at first that the targname can't be resolved
    new_targname = targname

    # Try to resolve the target via the target_dict
    if targname in targname_dict.keys():
        if len(targname_dict[targname]):
            new_targname = targname_dict[targname]

    # Try to resolve the target name with the online service
    try:
        targname_set = resolve(targname)
    except:
        targname_set = set()

    if len(targname_set):

        # For each resolved target name, check to see if it's already
        # in the database.  If it is, then use that one.
        session = get_session()
        targnames_in_db = session.query(Metadata.targname).all()
        targnames_in_db = [item[0] for item in targnames_in_db]
        for item in targname_set:
            if item in targnames_in_db:
                new_targname = item
        session.close()

    return new_targname

#------------------------------------------------------------------------------

def resolve(targname):
    """Resolve target name via the CDS web service

    Parameters
    ----------
    targname : str
        The name of the target

    Returns
    -------
    other_names : set
        set of resolved other names
    """

    web_string = 'http://cdsweb.u-strasbg.fr/cgi-bin/nph-sesame/-oxpI?{}'.format(targname)

    xmldoc = minidom.parse(urllib2.urlopen(web_string))
    itemlist = xmldoc.getElementsByTagName('alias')

    other_names = [str(item.childNodes[0].data) for item in itemlist]

    return set(other_names)
