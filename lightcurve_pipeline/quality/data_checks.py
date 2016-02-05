from astropy.io import fits
import inspect

#-------------------------------------------------------------------------------

def dataset_ok(filename):
    """Test whether the current datasets should be extracted"""

    all_functions = [value for key, value in inspect.currentframe().f_globals.iteritems() if key.startswith('check_')]

    with fits.open(filename) as hdu:
        time = hdu[1].data['time']

    for func in all_functions:
        if not func(time):
            return False

    return True

#-------------------------------------------------------------------------------

def check_linear(time_data):
    """Verify that the time column linearly progresses

    """

    last = time_data[0]
    for val in time_data[1:]:
        if not val >= last:
            return False

    return True

#-------------------------------------------------------------------------------

def check_not_singular(time_data):
    if len(set(time_data)) == 1:
        return False

    return True

#-------------------------------------------------------------------------------
