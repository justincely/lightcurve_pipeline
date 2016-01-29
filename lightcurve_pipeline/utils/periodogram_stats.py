"""Generate lomb-scargle periodogram statistics for use in the stats
database table and the periodogram plots
"""

from astropy.io import fits
import numpy as np
from scipy import signal

# -----------------------------------------------------------------------------

def get_periodogram_stats(dataset, freq_space):
    """Find significant periods from the given dataset and frequency
    space using a lomb-scargle periodogram.

    Parameters
    ----------
    dataset : string
        The path to the lightcurve product.
    freq_space : string
        Can either be 'short', 'med', or 'long'.  This defines the
        frequency space to look for significant periods.  'short' is
        defined as the range (STEPSIZE, 10 minutes), 'med' is
        (10 minutes, 1 hour), and 'long' is (1 hour, 10 hours).

    Returns
    -------
    periods : numpy array
        An array of the periods to check
    power : numpy array
        An array of the lomb-scargle powers corresponding to each
        period
    mean : float
        The mean of the lomb-scargle powers
    std : float
        The standard deviation of the lomb-scargle powers
    three_sigma : float
        Three standard deviations above the mean of the lomb-scargle
        powers
    significant_periods : list
        A list of the periods that have powers greater than 3-sigma
        about the mean
    significant_powers : list
        A list of the lomb-scargle powers that are greater than 3-sigma
        about the mean
    """

    # Get the data
    hdulist = fits.open(dataset, mode='readonly')
    counts = hdulist[1].data['net']
    times = hdulist[1].data['mjd']

    # Make sure the byte-order is native
    counts = counts.byteswap().newbyteorder()
    times = times.byteswap().newbyteorder()

    # Define frequency space (in days)
    short_freq = (hdulist[0].header['STEPSIZE'] / (60. * 60. * 24.)) # Step size
    med_freq = (10. / (60. * 24.)) # 10 minutes
    long_freq = 1. / 24. # 1 hour
    max_freq = 10. / 24. # 10 hours

    if freq_space == 'short':
        periods = np.linspace(short_freq, med_freq, len(times))
    elif freq_space == 'med':
        periods = np.linspace(med_freq, long_freq, len(times))
    elif freq_space == 'long':
        periods = np.linspace(long_freq, max_freq, len(times))

    ang_freqs = 2 * np.pi / periods
    power = signal.lombscargle(np.asarray(times), np.asarray(counts) - np.asarray(counts).mean(), ang_freqs)
    power *= 2 / (len(times) * np.asarray(counts).std() ** 2)
    maxima = signal.argrelextrema(data=power, comparator=np.greater, order=1)[0]
    mean = np.mean(power)
    std = np.std(power)
    three_sigma = mean + (3 * std)
    above_three_sigma = np.where(power > three_sigma)[0]
    significant_indices = [index for index in maxima if index in above_three_sigma]
    significant_periods = periods[significant_indices]
    significant_powers = power[significant_indices]

    return periods, power, mean, three_sigma, significant_periods, significant_powers