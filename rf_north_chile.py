# Receiver Fuction Calculation
## Recalculation of the results from https://nbviewer.jupyter.org/github/trichter/notebooks/blob/master/receiver_function_profile_chile.ipynb


import os.path
import matplotlib.pyplot as plt
import numpy as np
from obspy import read_inventory, read_events, UTCDateTime as UTC
from obspy.clients.fdsn import Client
from rf import read_rf, RFStream
from rf import get_profile_boxes, iter_event_data, IterMultipleComponents
from rf.imaging import plot_profile_map
from rf.profile import profile
from tqdm import tqdm

# data = os.path.join('data', '')
invfile = 'rf_profile_stations.xml'
catfile = 'rf_profile_events.xml'
datafile = 'rf_profile_data.h5'
rffile = 'rf_profile_rfs.h5'
profilefile = 'rf_profile_profile.h5'

if not os.path.exists(invfile):
    client = Client('GFZ')
    inventory = client.get_stations(network='CX', channel='BH?', level='channel',
                                    minlatitude=-24, maxlatitude=-19)
    inventory.write(invfile, 'STATIONXML')
inventory = read_inventory(invfile)
# inventory.plot(label=False)
# fig = inventory.plot('local', color_per_network=True)
# plt.savefig("inventory_data_events.png")


coords = inventory.get_coordinates('CX.PB01..BHZ')

print(coords)

lonlat = (coords['longitude'], coords['latitude'])
if not os.path.exists(catfile):
    client = Client()
    kwargs = {'starttime': UTC('2010-01-01'), 'endtime': UTC('2011-01-01'), 
              'latitude': lonlat[1], 'longitude': lonlat[0],
              'minradius': 30, 'maxradius': 90,
              'minmagnitude': 5.5, 'maxmagnitude': 6.5}
    catalog = client.get_events(**kwargs)
    catalog.write(catfile, 'QUAKEML')
catalog = read_events(catfile)


if not os.path.exists(datafile):
    client = Client('GFZ')
    stream = RFStream()
    with tqdm() as pbar:
        for s in iter_event_data(catalog, inventory, client.get_waveforms, pbar=pbar):
            stream.extend(s)
    stream.write(datafile, 'H5')


if not os.path.exists(rffile):
    data = read_rf(datafile, 'H5')
    stream = RFStream()
    for stream3c in tqdm(IterMultipleComponents(data, 'onset', 3)):
        stream3c.filter('bandpass', freqmin=0.5, freqmax=2)
        stream3c.trim2(-25, 75, 'onset')
        if len(stream3c) != 3:
            continue
        stream3c.rf()
        stream3c.moveout()
        stream.extend(stream3c)
    stream.write(rffile, 'H5')
    print(stream)


## Plot receiver function
plot_rf=0
if plot_rf:
    stream = read_rf(rffile, 'H5')
    kw = {'trim': (-5, 20), 'fillcolors': ('black', 'gray'), 'trace_height': 0.1}
    stream.select(component='L', station='PB01').sort(['back_azimuth']).plot_rf(**kw)
    plt.savefig('PB01'+'_L_RF.png')
    for sta in ('PB01', 'PB04'):
        stream.select(component='Q', station=sta).sort(['back_azimuth']).plot_rf(**kw)
        plt.savefig(sta+'_Q_RF.png')


if not os.path.exists(profilefile):
    stream = read_rf(rffile, 'H5')
    ppoints = stream.ppoints(70)
    boxes = get_profile_boxes((-21.3, -70.7), 90, np.linspace(0, 180, 73), width=530)
    plt.figure(figsize=(10, 10))
    plot_profile_map(boxes, inventory=inventory, ppoints=ppoints)
    pstream = profile(tqdm(stream), boxes)
    pstream.write(profilefile, 'H5')
    plt.savefig('profilefile.png')


if not os.path.exists('profile_plot.png'):
    pstream = read_rf(profilefile)
    pstream.trim2(-5, 20, 'onset')
    pstream.select(channel='??Q').normalize().plot_profile(scale=1.5, top='hist')
    plt.gcf().set_size_inches(15, 10)
    plt.savefig('profile_plot.png')