#! /usr/bin/env python

"""
Create various plots that deal with the hstlc filesystem, database,
and output products. This script uses multiprocessing.  Users can set
the number of cores used via the ``num_cores`` setting in the config
file (see below).

**Authors:**

    Justin Ely, Matthew Bourque

**Use:**

    This script is intended to be executed as part of the
    ``hstlc_pipeline`` shell script.  However, users can also execute
    this script via the command line as such:

    >>> make_hstlc_plots

**Outputs:**

    (1) ``hlsp_hstlc_*.png`` static lightcurve plots for each composite
        lightcurve, placed in the ``composite_dir`` directory, as
        determined by the config file (see below)
    (2) ``hlsp_hstlc_*.html`` bokeh plots showing a 'dashboard' of
        various plots for each composite lightcurve, placed in the
        ``composite_dir`` directory, as determined by the config file
        (see below)
    (3) ``interesting_hstlc.html``, ``boring_hstlc.html``, and
        ``null_hstlc.html`` 'exploratory' tables, which are sortable
        tables that display statistics and plots for each dataset,
        placed in the ``plot_dir`` directory, as determined by the
        config file (see below)
    (4) ``exptime_histogram.html`` - A histrogram showing the
        cumulative exposure time by target in the form of a bokeh plot,
        placed in the ``plot_dir`` directory, as determined by the
        config file (see below)
    (5) ``pie_config_cos_fuv.html``, ``pie_config_cos_nuv.html``,
        ``pie_config_stis_fuv.html``, and ``pie_config_stis_nuv.html``
        'configuration' pie charts that show the breakdown of datasets
        by grating/cenwave for each instrument/detector combination,
        placed in the ``plot_dir`` directory, as determined by the
        config file (see below)
    (6) ``opt_elem.html`` - a historgram showing the number of datasets
        for each filter, placed in the ``plot_dir`` directory, as
        determined by the config file (see below)
    (7) ``<dataset name>_periodgram.png`` - Lomb-Scargle periodograms
        for each dataset (both individual and composite), placed in the
        ``plot_dir`` directory, as determined by the config file (see
        below). Additionally, periodograms that are deemed interesting
        are saved in a separate ``periodogram_subset`` directory under
        the ``plot_dir`` directory.
    (8) a log file in the ``log_dir`` directory as determined by the
        config file (see below)

**Dependencies:**

    (1) Users must have access to the hstlc database
    (2) Users must also have a ``config.yaml`` file located in the
        ``lightcurve_pipeline/utils/`` directory with the following
        keys:

        - ``db_connection_string`` - The hstlc database connection
          string
        - ``plot_dir`` - The path to where hstlc output plots are
          stored
        - ``composite_dir`` - The path to where hstlc composite output
          products are stored
        - ``log_dir`` - The path to where the log file will be stored
        - ``num_cores`` - The number of cores to use during
          multiprocessing

    Other external library dependencies include:
        - ``astropy``
        - ``bokeh``
        - ``lightcurve_pipeline``
        - ``matplotlib``
        - ``numpy``
        - ``pymysql``
        - ``sqlalchemy``
"""

from collections import Counter
from collections import OrderedDict
import glob
import itertools
import logging
import multiprocessing as mp
import os
import platform

from astropy.io import fits
from astropy.table import Table
import bokeh
from bokeh import charts
from bokeh.io import gridplot
from bokeh.plotting import figure
from bokeh.embed import components
from bokeh import palettes
import numpy as np

import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['axes.formatter.useoffset'] = False

#import seaborn as sns
#sns.set(style="dark")

from lightcurve_pipeline.utils.periodogram_stats import get_periodogram_stats
from lightcurve_pipeline.utils.utils import SETTINGS
from lightcurve_pipeline.utils.utils import set_permissions
from lightcurve_pipeline.utils.utils import setup_logging
from lightcurve_pipeline.database.database_interface import engine
from lightcurve_pipeline.database.database_interface import session
from lightcurve_pipeline.database.database_interface import Metadata
from lightcurve_pipeline.database.database_interface import Stats

#-------------------------------------------------------------------------------

def bar_opt_elem():
    """
    Create a bar chart showing the number of composite lightcurves
    for each COS & STIS optical element
    """

    logging.info('Creating optical element bar chart')

    # Query for data
    query = session.query(Metadata.instrume, Metadata.opt_elem).all()
    instrumes = [result[0] for result in query]
    opt_elems = [result[1] for result in query]
    opt_elems_set = sorted(list(set(opt_elems)))

    # Initialize dictionaries that store all optical elements
    cos_dict, stis_dict = {}, {}
    for opt_elem in opt_elems_set:
        cos_dict[opt_elem] = 0
        stis_dict[opt_elem] = 0

    # Count number of opt_elems
    for instrument, opt_elem in zip(instrumes, opt_elems):
        if instrument == 'COS':
            cos_dict[opt_elem] += 1
        elif instrument == 'STIS':
            stis_dict[opt_elem] += 1

    # Determine plotting values
    cat = list(opt_elems_set)
    xyvalues = OrderedDict()
    xyvalues['COS'] = [cos_dict[opt_elem] for opt_elem in opt_elems_set]
    xyvalues['STIS'] = [stis_dict[opt_elem] for opt_elem in opt_elems_set]

    # Make plots
    bar = charts.Bar(xyvalues,
        cat,
        xlabel='Optical Element',
        ylabel='# of Lightcurves',
        stacked=True,
        legend = 'top_right')
    bar.background_fill = '#cccccc'
    bar.outline_line_color = 'black'
    charts.output_file(os.path.join(SETTINGS['plot_dir'], 'opt_elem.html'))
    plot_file = os.path.join(SETTINGS['plot_dir'], 'opt_elem.html')
    charts.save(obj=bar, filename=plot_file)
    set_permissions(plot_file)

#-------------------------------------------------------------------------------

def configuration_piechart():
    """
    Create a piechart showing distribution of configurations for each
    imstrument/detector combination
    """

    logging.info('Creating target piechart')

    data_dir = SETTINGS['composite_dir']

    configs = {}
    for dataset in glob.glob(os.path.join(data_dir, '*.fits')):

        instrument = os.path.split(dataset)[1].split('_')[3]
        grating = os.path.split(dataset)[1].split('_')[5]
        cenwave = os.path.split(dataset)[1].split('_')[6]

        if not instrument in configs:
            configs[instrument] = ['{}/{}'.format(grating, cenwave)]
        else:
            configs[instrument].append('{}/{}'.format(grating,cenwave))

    # COS FUV
    try:
        settings = Counter(configs['cos-fuv'])
        charts.output_file(os.path.join(SETTINGS['plot_dir'], 'pie_config_cos_fuv.html'))
        plot = charts.Donut(settings.values(),
                            settings.keys(),
                            width=1200,
                            height=600,
                            title='COS FUV breakdown')
        plot_file = os.path.join(SETTINGS['plot_dir'], 'pie_config_cos_fuv.html')
        charts.save(obj=plot, filename=plot_file)
        set_permissions(plot_file)
    except KeyError:
        logging.info('No COS FUV datasets')

    # COS NUV
    try:
        settings = Counter(configs['cos-nuv'])
        charts.output_file(os.path.join(SETTINGS['plot_dir'], 'pie_config_cos_nuv.html'))
        plot = charts.Donut(settings.values(),
                            settings.keys(),
                            width=1200,
                            height=600,
                            title='COS NUV breakdown')
        plot_file = os.path.join(SETTINGS['plot_dir'], 'pie_config_cos_nuv.html')
        charts.save(obj=plot, filename=plot_file)
        set_permissions(plot_file)
    except KeyError:
        logging.info('No COS NUV datasets')

    # STIS FUV
    try:
        settings = Counter(configs['stis-fuv-mama'])
        charts.output_file(os.path.join(SETTINGS['plot_dir'], 'pie_config_stis_fuv.html'))
        plot = charts.Donut(settings.values(),
                            settings.keys(),
                            width=1200,
                            height=600,
                            title='STIS FUV breakdown')
        plot_file = os.path.join(SETTINGS['plot_dir'], 'pie_config_stis_fuv.html')
        charts.save(obj=plot, filename=plot_file)
        set_permissions(plot_file)
    except KeyError:
        logging.info('No STIS FUV-MAMA datasets')

    # STIS NUV
    try:
        settings = Counter(configs['stis-nuv-mama'])
        charts.output_file(os.path.join(SETTINGS['plot_dir'], 'pie_config_stis_nuv.html'))
        plot = charts.Donut(settings.values(),
                            settings.keys(),
                            width=1200,
                            height=600,
                            title='STIS NUV breakdown')
        plot_file = os.path.join(SETTINGS['plot_dir'], 'pie_config_stis_nuv.html')
        charts.save(obj=plot, filename=plot_file)
        set_permissions(plot_file)
    except KeyError:
        logging.info('No STIS NUV datasets')


#-------------------------------------------------------------------------------

def dataset_dashboard(filename, plot_file=''):
    """
    Creates interactive bokeh 'dashboard' plot for the given filename

    Parameters
    ----------
    filename : str
        The path to the lightcurve
    plot_file : str
        The path to the PNG plot.  The user can supply this argument if
        they wish to update the plot or save to a specific location.
    """

    logging.info('Creating bokeh dashboard plots for {}'.format(filename))

    if not plot_file:
        plot_file = filename.replace('.fits', '.html')
    if os.path.exists(plot_file):
        os.remove(plot_file)

    bokeh.io.output_file(plot_file)
    TOOLS = 'pan,wheel_zoom,box_zoom,reset,resize,box_select,lasso_select,save'

    with fits.open(filename) as hdu:
        source = bokeh.models.ColumnDataSource(data={col : hdu[1].data[col] for col in hdu[1].data.names})

        endless_colors = itertools.cycle(palettes.Spectral6)
        colors = [endless_colors.next() for i in np.unique(hdu[1].data['dataset'])]

        dset_counts = Counter(hdu[1].data['dataset'])
        repeats = [dset_counts[key] for key in sorted(dset_counts.keys())]

        colors = np.repeat(colors, repeats)

        axes = []
        for key in ['gross', 'net', 'flux', 'error', 'background']:
            if len(axes) == 0:
                axes.append(figure(tools=TOOLS, plot_width=900, plot_height=350, title=key, toolbar_location='right'))
            else:
                axes.append(figure(tools=TOOLS, x_range=axes[0].x_range, plot_width=900, plot_height=350, title=key, toolbar_location='right'))
            axes[-1].circle('mjd',
                            key,
                            source=source,
                            size=12,
                            color=colors,
                            fill_alpha=1)


    # put all the plots in a grid layout
    p = bokeh.io.vplot(*axes)

    charts.save(obj=p, filename=plot_file)
    charts.reset_output()
    del p
    set_permissions(plot_file)

#-------------------------------------------------------------------------------

def exploratory_tables():
    """
    Create html tables containing data from the stats table as well as
    plots, broken down into interesting, boring, and null results
    """

    # Interesting results
    logging.info('Creating exploratory table for interesting datasets')
    interesting_query = session.query(Stats.lightcurve_path, Stats.lightcurve_filename).\
        filter(Stats.poisson_factor != 'NULL').\
        filter(Stats.poisson_factor >= 1.2).\
        filter(Stats.lightcurve_path.like('%composite%')).all()
    interesting_datasets = [os.path.join(item[0], item[1]) for item in interesting_query]
    make_exploratory_table(interesting_datasets, os.path.join(SETTINGS['plot_dir'], 'interesting_hstlc.html'))

    # Boring results
    logging.info('Creating exploratory table for boring datasets')
    boring_query = session.query(Stats.lightcurve_path, Stats.lightcurve_filename).\
        filter(Stats.poisson_factor != 'NULL').\
        filter(Stats.poisson_factor < 1.2).\
        filter(Stats.lightcurve_path.like('%composite%')).all()
    boring_datasets = [os.path.join(item[0], item[1]) for item in boring_query]
    make_exploratory_table(boring_datasets, os.path.join(SETTINGS['plot_dir'], 'boring_hstlc.html'))

    # NULL results
    logging.info('Creating exploratory table for NULL datasets')
    null_query = session.query(Stats.lightcurve_path, Stats.lightcurve_filename).\
        filter(Stats.poisson_factor == 'NULL').\
        filter(Stats.lightcurve_path.like('%composite%')).all()
    null_datasets = [os.path.join(item[0], item[1]) for item in null_query]
    make_exploratory_table(null_datasets, os.path.join(SETTINGS['plot_dir'], 'null_hstlc.html'))

#-------------------------------------------------------------------------------

def histogram_exptime():
    """
    Create a histogram showing the distribution of exposure times for
    the composite lightcurves
    """

    logging.info('Creating exposure time historgram')

    data_dir = SETTINGS['composite_dir']

    exptime_data = {}
    for dataset in glob.glob(os.path.join(data_dir, '*.fits')):
        with fits.open(dataset) as hdu:
            targname = os.path.split(dataset)[-1].split('_')[4]
            exptime = hdu[0].header['EXPTIME']

            if targname in exptime_data:
                exptime_data[targname] += exptime
            else:
                exptime_data[targname] = exptime

    charts.output_file(os.path.join(SETTINGS['plot_dir'], 'exptime_histogram.html'))

    times = np.array(exptime_data.values())
    names = np.array(exptime_data.keys())
    indx = np.argsort(times)

    times = list(times[indx])[::-1][:30]
    names = list(names[indx])[::-1][:30]

    bar = charts.Bar(times,
                     cat=names,
                     xlabel='Target',
                     ylabel='Exptime (s)',
                     width=700,
                     height=400,
                     title='Cumulative Exptime per Target')

    bar.background_fill = '#cccccc'
    bar.outline_line_color = 'black'

    # change just some things about the x-grid
    #bar.xgrid.grid_line_color = None

    # change just some things about the y-grid
    #bar.ygrid.band_fill_alpha = 0.1
    #bar.ygrid.band_fill_color = "navy"

    #bar.toolbar_location = None

    #charts.show(bar)

    script, div = components(bar)

    plot_file = os.path.join(SETTINGS['plot_dir'], 'exptime_histogram.html')
    charts.save(obj=bar, filename=plot_file)
    set_permissions(plot_file)

#-------------------------------------------------------------------------------

def make_exploratory_table(dataset_list, table_name):
    """
    Create html tables containing data from the stats table as well as
    plots

    Parameters
    ----------
    dataset_list : list
        A list of the paths to the datasets to process
    table_name : str
        The path to the output file
    """

    info = []

    if len(dataset_list) > 0:

        for dataset in dataset_list:
            path, name = os.path.split(dataset)

            with fits.open(dataset) as hdu:
                exptime = hdu[0].header['EXPTIME']

            targname = os.path.split(dataset)[1].split('_')[4]
            instrument = os.path.split(dataset)[1].split('_')[3].split('-')[0]
            grating = os.path.split(dataset)[1].split('_')[5]
            cenwave = os.path.split(dataset)[1].split('_')[6]
            aperture = os.path.split(dataset)[1].split('_')[7]

            results = session.query(Stats).filter(Stats.lightcurve_filename == name).all()
            total = results[0].total
            mean = results[0].mean
            poisson_f = results[0].poisson_factor
            pearson_r = results[0].pearson_r
            pearson_p = results[0].pearson_p

            plot_name = dataset.replace('.fits', '.html')
            plot_name_static = dataset.replace('.fits', '.png')

            plot_html = """<a href="{}" target="_blank"><img width="400" src="{}"><a>""".format(plot_name, plot_name_static)
            new_row = (targname, plot_html, instrument, grating, cenwave, aperture, exptime, total, mean, poisson_f, pearson_r, pearson_p, dataset)
            info.append(new_row)

        out_tab = Table(rows=info,
                        names=('target', 'plot', 'instrument', 'grating', 'cenwave', 'aperture', 'exptime', 'total', 'mean', 'poisson_f', 'pearson_r', 'pearson_p', 'filename'))
        out_tab.write(table_name, format='jsviewer')

        if platform.system() == 'Linux':
            os.system("""sed -i "s/&lt;/</g" {}""".format(table_name))
            os.system("""sed -i "s/&gt;/>/g" {}""".format(table_name))
        elif platform.system() == 'Darwin':
            os.system("""sed -i '' "s/&lt;/</g" {}""".format(table_name))
            os.system("""sed -i '' "s/&gt;/>/g" {}""".format(table_name))
        else:
            raise ValueError("OS {} is not supported for this operation".format(platform.system()))

#-------------------------------------------------------------------------------

def periodogram(dataset):
    """
    Create a Lomb-Scargle periodgram for the given dataset

    Parameters
    ----------
    dataset : string
        The path to the dataset
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

    # Get the periodogram information
    short_periods, short_power, short_mean, short_three_sigma, short_significant_periods, short_significant_powers = get_periodogram_stats(dataset, 'short')
    med_periods, med_power, med_mean, med_three_sigma, med_significant_periods, med_significant_powers = get_periodogram_stats(dataset, 'med')
    long_periods, long_power, long_mean, long_three_sigma, long_significant_periods, long_significant_powers = get_periodogram_stats(dataset, 'long')

    # Make plot if there are significant peaks above the threshold
    significant_threshold = 0.30
    all_significant_powers = list(short_significant_powers) + list(med_significant_powers) + list(long_significant_powers)
    if len(all_significant_powers) > 0:
        max_significant_power = max(all_significant_powers)
        if max_significant_power >= significant_threshold:

            logging.info('Creating periodogram for dataset {}'.format(dataset))

            fig = plt.figure(figsize=(10, 8))
            ax1 = fig.add_subplot(411)
            ax2 = fig.add_subplot(412)
            ax3 = fig.add_subplot(413)
            ax4 = fig.add_subplot(414)
            ax1.minorticks_on()

            # Top panel - the data
            ax1.plot(times, counts, 'b+')
            ax1.set(xlabel='MJD', ylabel='Net')

            # 2nd panel - short frequency space
            ax2.plot(short_periods, short_power)
            ax2.axhline(short_mean, color='r', linestyle='-')
            ax2.axhline(short_three_sigma, color='g', linestyle='-')
            for period in short_significant_periods:
                ax2.axvline(period, color='k', linestyle='--')
            ax2.set(xlim=(short_freq, med_freq), title='Short Frequency Space')

            # 3rd panal - medium frequency space
            ax3.plot(med_periods, med_power)
            ax3.axhline(med_mean, color='r', linestyle='-')
            ax3.axhline(med_three_sigma, color='g', linestyle='-')
            for period in med_significant_periods:
                ax3.axvline(period, color='k', linestyle='--')
            ax3.set(xlim=(med_freq, long_freq), ylabel='Lomb-Scargle Power', title='Medium Frequency Space')

            # bottom panel - long frequency space
            ax4.plot(long_periods, long_power)
            ax4.axhline(long_mean, color='r', linestyle='-')
            ax4.axhline(long_three_sigma, color='g', linestyle='-')
            for period in long_significant_periods:
                ax4.axvline(period, color='k', linestyle='--')
            ax4.set(xlim=(long_freq, max_freq), xlabel='Period (Days)', title='Long Frequency Space')

            # Save the plot
            fig.tight_layout()
            filename = '{}_periodogram.png'.format(os.path.basename(dataset).split('_curve.fits')[0])
            save_loc = os.path.join(SETTINGS['plot_dir'], 'periodogram_subset', filename)
            plt.savefig(save_loc)
            plt.close()
            set_permissions(save_loc)

#-------------------------------------------------------------------------------

def plot_dataset(filename, plot_file=''):
    """
    Create an interactive bokeh lightcurve plot for the given filename

    Parameters
    ----------
    filename : str
        The path to the lightcurve
    plot_file : str
        The path to the PNG plot.  The user can supply this argument if
        they wish to update the plot or save to a specific location
    """

    logging.info('Creating bokeh lightcurve for {}'.format(filename))

    path, name = os.path.split(filename)

    if not plot_file:
        plot_file = name.replace('.fits', '.html')
    if os.path.exists(plot_file):
        os.remove(plot_file)

    TOOLS = 'pan,wheel_zoom,box_zoom,box_select,lasso_select,reset,resize,save'

    charts.output_file(plot_file)
    p = figure(tools=TOOLS, toolbar_location='above', logo='grey', plot_width=700)
    p.background_fill= "#cccccc"

    with fits.open(filename) as hdu:
        p.circle(hdu[1].data['MJD'],
                 hdu[1].data['FLUX'],
                 size=12,
                 line_color="black",
                 fill_alpha=0.8)

    p.xaxis.axis_label='Time (MJD)'
    p.yaxis.axis_label='Net (cnts/sec)'
    p.grid.grid_line_color='white'

    charts.save(obj=p, filename=plot_file)
    charts.reset_output()
    del p
    set_permissions(plot_file)

#-------------------------------------------------------------------------------

def plot_dataset_static(filename, plot_file=''):
    """
    Creates static PNG lightcurve plot for the given filename

    Parameters
    ----------
    filename : str
        The path to the lightcurve
    plot_file : str
        The path to the PNG plot.  The user can supply this argument if
        they wish to update the plot or save to a specific location
    """

    logging.info('Creating static PNG for {}'.format(filename))

    if not plot_file:
        plot_file = filename.replace('.fits', '.png')
    if os.path.exists(plot_file):
        os.remove(plot_file)

    fig = plt.figure(figsize=(10, 1))
    ax = fig.add_subplot(1, 1, 1)

    with fits.open(filename) as hdu:
        indx = np.argsort(hdu[1].data['MJD'])
        xvals = np.arange(len(hdu[1].data['MJD']))
        yvals = hdu[1].data['FLUX']

        try:
            colors = hdu[1].data['dataset'][indx]
        except KeyError:
            colors = np.ones(xvals.shape)

        ax.scatter(xvals,
                   yvals[indx],
                   c=colors,
                   marker='o')

    ax.set_xlim(0, xvals.max())
    ax.set_ylim(yvals[indx].min(), yvals[indx].max())
    fig.savefig(plot_file, bbox_inches='tight')
    plt.close(fig)
    del fig
    set_permissions(plot_file)

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------

def main():
    """The main function of the ``make_hstlc_plots`` script
    """

    # Configure logging
    module = os.path.basename(__file__).strip('.py')
    setup_logging(module)

    # Make matplotlib and bokeh lightcurve plots
    composite_datasets = glob.glob(os.path.join(SETTINGS['composite_dir'], '*.fits'))
    logging.info('Creating matplotlib and bokeh lightcurve plots for {} datasets using {} cores'.format(len(composite_datasets), SETTINGS['num_cores']))
    pool = mp.Pool(processes=SETTINGS['num_cores'])
    pool.map(plot_dataset_static, composite_datasets)
    pool.map(dataset_dashboard, composite_datasets)
    pool.close()
    pool.join()

    # Make exploratory tables
    exploratory_tables()

    # Make exposure time histogram
    histogram_exptime()

    # Make configuration piechart
    configuration_piechart()

    # Make optical element bar chart
    bar_opt_elem()

    # Make individual bokeh plots for some examples
    #plot_dataset('/grp/hst/hstlc/hst13902/outputs/composite/V4046SGR_FUV_G130M_1300_curve.fits', os.path.join(SETTINGS['plot_dir'], 'example_flare.html'))
    #plot_dataset('/grp/hst/hstlc/hst13902/outputs/composite/IR-COM_FUV_G140L_1105_curve.fits', os.path.join(SETTINGS['plot_dir'], 'example_transit.html'))

    # Make periodograms
    results = session.query(Stats.lightcurve_path, Stats.lightcurve_filename).\
        filter(Stats.periodogram == True).all()
    datasets = [os.path.join(item.lightcurve_path, item.lightcurve_filename) for item in results]
    logging.info('Making periodograms for {} datasets over {} cores'.format(len(datasets), SETTINGS['num_cores']))
    pool = mp.Pool(processes=SETTINGS['num_cores'])
    pool.map(periodogram, datasets)
    pool.close()
    pool.join()

    logging.info('Processing complete')

#-------------------------------------------------------------------------------

if __name__ == '__main__':

    main()
