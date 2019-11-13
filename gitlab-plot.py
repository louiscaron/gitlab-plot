import sys
import argparse
import requests
import pickle
import time
from datetime import datetime

import matplotlib.pyplot as plt
import matplotlib.dates as md
import matplotlib.lines as ml
from matplotlib.collections import PathCollection
import numpy as np


# start the execution
parser = argparse.ArgumentParser()
parser.add_argument('-u', '--url', help='gitlab API server api', default='http://gitlabee.dt.renault.com/api/v4')
parser.add_argument('-t', '--token', help='token to use to retrieve the data, if no toklen is provided, it will retrieve the data from last fetch')

args = parser.parse_args()



#21686 = Tresos11
#24789 = Tresos12
#28083 = Tresos13
#28078 = Tresos14
RUNNERS = (('Tresos11', 21686), ('Tresos12', 24789), ('Tresos13', 28083), ('Tresos14', 28078))


def save_obj(obj, name):
    with open(name + '.pkl', 'wb') as f:
        pickle.dump(obj, f, pickle.HIGHEST_PROTOCOL)

def load_obj(name):
    with open(name + '.pkl', 'rb') as f:
        return pickle.load(f)

if args.token:
    JOBSAPI = args.url + '/runners/{}/jobs'

    header = {'PRIVATE-TOKEN' : args.token}
    params = {
               'page' : 1,
               'per_page' : 50,
             }

    values = {}
    for (n,r) in RUNNERS:
        print('runner : ' + repr(r))
        values[r] = []
        params['page'] = 0
        while True:
            print(params)
            reply = requests.get(JOBSAPI.format(r), params=params, headers=header)
            print(reply)
            if reply.status_code != 200:
                break
            res = reply.json()
            #print(res)
            if res == []:
                break

            #print(len(res))
            values[r] += res
            params['page'] += 1

    # save in a file to be able to replay easily
    save_obj(values, 'values')
else:
    values = load_obj('values')

# values = {21686 : [ 
# {'id': 8840397, 
#  'status': 'canceled', 
#  'stage': 'generate', 
#  'name': 'cabin-master-bswgen', 
#  'ref': 'tag_a21f47101', 
#  'tag': True, 
#  'coverage': None, 
#  'allow_failure': False, 
#  'created_at': '2019-11-07T09:09:51.510Z', 
#  'started_at': 1573114193.0, 
#  'finished_at': '2019-11-07T09:13:03.008Z', 
#  'duration': 189.011409, 
#  'user': {
#      'id': 1111, 
#      'name': 'Louis Caron', 
#      'username': 'louis.caron', 
#      'state': 'active', 
#      'avatar_url': 'https://gitlabee.dt.renault.com/uploads/-/system/user/avatar/1111/avatar.png', 
#      'web_url': 'https://gitlabee.dt.renault.com/louis.caron', 
#      'created_at': '2018-07-07T07:04:37.576Z', 
#      'bio': '', 
#      'location': '', 
#      'public_email': '', 
#      'skype': '', 
#      'linkedin': '', 
#      'twitter': '', 
#      'website_url': '', 
#      'organization': ''},
#  'commit': {
#      'id': 'a21f47101f2e958f7378b05230eb8ddf84ee28c8', 
#      'short_id': 'a21f4710', 
#      'created_at': '2019-11-06T14:56:02.000Z', 
#      'parent_ids': ['ac7438c5b1cfe38e34e6cece43c04006008d3716'], 
#      'title': 'UI automation: add retry on CAN buffer assignment failure', 
#      'message': 'UI automation: add retry on CAN buffer assignment failure\n\ncloses FACEEXT-3831\n\nSigned-off-by: Louis Caron <louis.caron@renault.com>\n', 
#      'author_name': 'Louis Caron', 
#      'author_email': 'louis.caron@renault.com', 
#      'authored_date': '2019-11-06T13:56:51.000Z', 
#      'committer_name': 'Louis Caron', 
#      'committer_email': 'louis.caron@renault.com', 
#      'committed_date': '2019-11-06T14:56:02.000Z'}, 
#  'pipeline': {
#      'id': 1243271, 
#      'sha': 'a21f47101f2e958f7378b05230eb8ddf84ee28c8', 
#      'ref': 'tag_a21f47101', 
#      'status': 'canceled', 
#      'web_url': 'https://gitlabee.dt.renault.com/partners/colorado/cp/face-cp-bsw/pipelines/1243271'}, 
#  'web_url': 'https://gitlabee.dt.renault.com/partners/colorado/cp/face-cp-bsw/-/jobs/8840397', 
#  'project': {
#      'id': 16376, 
#      'description': 'Reference workspace for PIU', 
#      'name': 'face-cp-bsw', 
#      'name_with_namespace': 'partners / colorado / cp / face-cp-bsw', 
#      'path': 'face-cp-bsw', 
#      'path_with_namespace': 'partners/colorado/cp/face-cp-bsw', 
#      'created_at': '2018-12-12T18:19:17.494Z'}
# }


# keep only the jobs that are relevant
newvalues = {}
for k, v in values.items():
    newvalues[k] = list(filter(lambda x: (x['name'][-7:] == '-bswgen') and (x['status'] in ('success', 'failed')), v))

values = newvalues

# convert time string to unix timestamp (for easier)
for v in values.values():
    for e in v:
        e['started_at'] = time.mktime(datetime.strptime(e['started_at'], "%Y-%m-%dT%H:%M:%S.%fZ").timetuple())

# find the highest latest time
#last = max([max([e['started_at'] for e in v]) for v in values.values()])
#print(last)


def showmetrics(t1, t2):
    # for each element in the last N hours, print the number of runs and the pass rate
    results = {}
    for k, v in values.items():
        f = list(filter(lambda x: (x['started_at'] >= t1) and (x['started_at'] <= t2), v))
        results[k] = f

    ret = []
    for k, v in results.items():
        for e in v:
            if e['status'] not in ('success', 'failed'):
                print(e)
        #print(len(v))
        p = sum(e['status'] == 'success' for e in v)
        #print(p)
        f = sum(e['status'] == 'failed' for e in v)
        #print(f)
        c = sum(e['status'] == 'canceled' for e in v)
        #print(c)
        try:
            text = '{} : {}/{} -> {:.2f}%'.format(k, p, p+f, 100.0*p/(p+f))
        except ZeroDivisionError:
            text = '{} : no run in range'.format(k)
        #print(text)
        ret.append(text)
    return ret

def on_xlims_change(axes):
    xl = axes.get_xlim()
    #print("updated xlims: ", xl)
    # force only 2 ticks (leftmost, rightmost)
    #axes.set_xticks(xl, minor=False)

    uxl = md.num2epoch(xl)
    t1 = datetime.utcfromtimestamp(uxl[0]).strftime('%Y-%m-%d %H:%M:%S')
    t2 = datetime.utcfromtimestamp(uxl[1]).strftime('%Y-%m-%d %H:%M:%S')
    axes.get_figure().suptitle(t1 + ' - ' + t2)

    rv = showmetrics(uxl[0], uxl[1])
    for a in axes.get_figure().axes:
        a.set_xlabel(rv.pop(0))


def on_ylims_change(axes):
    yl = axes.get_ylim()

    if yl != (-0.01, 1.01):
        # always force Y zoom to full scale
        axes.set_ylim(-0.01, 1.01)

def lineplot(x_data, y_data, ax=None, color='539caf', title='None'):
    # Plot the best fit line, set the linewidth (lw), color and
    # transparency (alpha) of the line
    ax.plot(x_data, y_data, color = '#' + color, marker='o', picker=10, linestyle='None', markersize = 2.0)
    #ax.scatter(x_data, y_data, lw = 2, color = '#' + color, alpha = 1, picker=10)

    # Label the axes and provide a title
    ax.set_title(title)
    ax.set_ylabel('Pass/Fail')
    #ax.tick_params(axis='x', labelrotation=0, labelsize=7, bottom=False)
    ax.tick_params(axis='x', which='both', bottom=False, labelbottom=False)
    xfmt = md.DateFormatter('%Y-%m-%d %H:%M:%S')
    ax.xaxis.set_major_formatter(xfmt)
    ax.callbacks.connect('xlim_changed', on_xlims_change)
    ax.callbacks.connect('ylim_changed', on_ylims_change)
    on_xlims_change(ax)
    #ax.get_xaxis().set_visible(False)


def on_pick(event):
    artist = event.artist
#    print('Artist picked:', artist)
    ind = event.ind
#    print('{} vertices picked'.format(len(ind)))
#    print('Pick between vertices {} and {}'.format(min(ind), max(ind)+1))

    if isinstance(artist, PathCollection):
        print('label:' + artist.get_label())
        print('offsets:' + repr(artist.get_offsets()))

    elif isinstance(artist, ml.Line2D):
        x = artist.get_xdata()

        if len(ind) > 5:
            print('Too many points selected')
        else:
            print('{} points in range:'.format(len(ind)))
            for idx in ind:
#                print('Data point:', x[idx])
                ux = md.num2epoch(x[idx])
#                print(ux)
#                print(datetime.fromtimestamp(ux).strftime('%Y-%m-%d %H:%M:%S'))
                #print(artist.axes.origvalues)
                # find the right point
                for e in artist.axes.origvalues:
                    if e['started_at'] > (ux - 1) and e['started_at'] < (ux + 1):
                        print('  - name : ' + e['name'])
                        print('    - pipeline : ' + e['pipeline']['web_url'])
                        print('    - job : ' + e['web_url'])
                        break
                else:
                    print('Not found')

fig, axs = plt.subplots(1, len(RUNNERS), figsize=(9, 3), sharex=True, sharey=True)
fig.subplots_adjust(top=0.85)
fig.suptitle('Status on runners in by time')
fig.canvas.callbacks.connect('pick_event', on_pick)

for (n,r) in RUNNERS:
    table = values[r]
    xdata = [e['started_at'] for e in table]
    ydata = [0 if e['status'] in ('failed', 'canceled') else 1 for e in table]

    # print(len(xdata))
    # print(len(ydata))
    lineplot(md.epoch2num(xdata), ydata, ax=axs[0], title=n)
    axs[0].origvalues = table
    axs = np.delete(axs, 0)

#plt.legend(loc='upper left')
#plt.locator_params(axis='x', nbins=2)
plt.locator_params(axis='y', nbins=1)
#plt.xticks( rotation=25 )
plt.show()
