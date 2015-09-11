"""Resolve the targname to a better option, if available.
"""

import urllib2
from xml.dom import minidom

from lightcurve_pipeline.utils.utils import SETTINGS
from lightcurve_pipeline.utils.targname_dict import targname_dict
from lightcurve_pipeline.database.database_interface import session
from lightcurve_pipeline.database.database_interface import Metadata

#------------------------------------------------------------------------------

def get_targname(targname):
    """Resolve the targname to a better option, if available.  If the
    targname cannot be resolved, the original targname is returned.

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
        targnames_in_db = session.query(Metadata.targname).all()
        targnames_in_db = [item[0] for item in targnames_in_db]
        for item in targname_set:
            if item in targnames_in_db:
                new_targname = item

    return new_targname

#------------------------------------------------------------------------------

def resolve(targname):
    """Resolve target name accross databases

    Names resolved via http://cds.u-strasbg.fr/cgi-bin/Sesame

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

#------------------------------------------------------------------------------
