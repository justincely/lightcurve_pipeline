import urllib2
from xml.dom import minidom

#-------------------------------------------------------------------------------

def resolve(targname):
    """Resolve target name accross databases

    Names resolved vie http://cds.u-strasbg.fr/cgi-bin/Sesame

    Parameters
    ----------
    targname : str
        name of the target

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

#-------------------------------------------------------------------------------

