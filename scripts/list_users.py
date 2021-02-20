import importlib.util
import sys
spec = importlib.util.spec_from_file_location('mangaupdates', 'mangaupdates/__init__.py')
mangaupdates = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mangaupdates
spec.loader.exec_module(mangaupdates)

from mangaupdates import Series, ListStats
import csv
import pandas as pd
import time
import os
import os.path
import argparse
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

MAX_RETRIES = 5
CONNECTION_ERROR_DELAY = 90


def make_dataset(series_ids, filename=None, delay=10, list_names=None, mode='n'):

    col_names = ('userid', 'username', 'score', 'listname', 'seriesid')
    resuming = False
    if filename is not None:
        write_col_names = True
        if os.path.isfile(filename):
            if mode == 'n':
                print(filename, 'exists. Aborting...')
                return
            elif mode == 'a':
                print(filename, 'exists. Rows will be appended.')
                resuming = True
                write_col_names = False

                # get latest sid in final line
                # https://stackoverflow.com/a/54278929
                with open(filename, 'rb') as f:
                    f.seek(-2, os.SEEK_END)
                    while f.read(1) != b'\n':
                        f.seek(-2, os.SEEK_CUR)
                    last_line = f.readline().decode()

                split_line = last_line.split(',')
                last_sid = int(split_line[-1])
                last_list_name = split_line[-2]
                last_sid_index = series_ids.index(last_sid)
                series_ids = series_ids[last_sid_index:]
            elif mode == 'w':
                print(filename, 'exists. Overwriting...')
            else:
                print(f"Error: value for mode ({mode}) should be either 'n', "
                       "'a', or 'w'. Exiting...")
                return
        elif mode == 'n':
            mode = 'w'
        f = open(filename, mode, newline='')
        writer = csv.writer(f)

        if write_col_names:
            writer.writerows([col_names])

    if filename is None:
        rows = []

    if list_names is None:
        list_names = ('read', 'wish', 'unfinished', 'complete', 'hold')
    print('Lists:', list_names)

    sess = requests.Session()
    retries = Retry(total=MAX_RETRIES, backoff_factor=3)
    sess.mount('http://', HTTPAdapter(max_retries=retries))
    loaded = False
    try:
        for i, sid in enumerate(series_ids):
            loaded = False
            lists = ListStats(sid, session=sess)
            print(sid, end='\t\t', flush=True)
            for _ in range(MAX_RETRIES):
                try:
                    lists.populate(list_names=list_names)
                    break
                except requests.exceptions.ConnectionError as e:
                    print(e)
                    print('Retrying...')
                    time.sleep(CONNECTION_ERROR_DELAY)
            else:       # no break
                print('Skipping', sid, '(exceeded MAX_RETRIES)')
                continue


            for key in list_names:
                if resuming and i == 0:
                    if list_names.index(key) <= list_names.index((last_list_name)):
                        print('0 rows (resuming).')
                        continue
                    resuming = False
                    # Since this program only writes to the file every iteration of
                    # a list of a series, we know that on the previous run, the
                    # program probably stopped between (instead of in the middle
                    # of) writing to the file.
                    # Thus, we assume that if the last entry on the file has
                    # some series id `last_sid` and list name `last_list_name`, we
                    # can simply skip all entries before that.
                new_rows = [(val.user_id, val.username, val.rating, key, sid) for val in lists.general_list(key)]
                print(key, f'{len(new_rows)} rows.', sep='\t')
                if filename is None:
                    rows.extend(new_rows)
                else:
                    writer.writerows(new_rows)
            loaded = True
            time.sleep(delay)
    except (KeyboardInterrupt, requests.exceptions.ConnectionError) as e:
        print('\n', e, sep='')
        if loaded:
            print("Stopped after loading", sid)
        else:
            print("Stopped before loading", sid)

    if filename is not None:
        f.close()
        return
    else:
        return rows


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(metavar='INPUT', dest='input',
                        help='csv file containing series ids.')
    parser.add_argument(metavar='OUTPUT', dest='output',
                        help='csv file where the output will be saved.')
    parser.add_argument('--headers', action='store_true',
                        help='there are headers in the input file (overrides --column)')
    parser.add_argument('-n', default=10, dest='N', help='# of series to crawl.')
    parser.add_argument('-m', '--mode', default='n',
                        help="'n': abort if OUTPUT file already exists (default)."
                        "'a': append to OUTPUT file if already exists."
                        "'w': overwrite OUTPUT file (equivalent to --force).")
    parser.add_argument('-f', '--force', action='store_true',
                        help='overwrite the output file if it exists (instead '
                             'of appending to it). overrides --mode.')
    parser.add_argument('--all', action='store_true',
                        help='"read", "wish", and "unfinished" lists will all be '
                             'crawled, otherwise only "read" will be crawled.')
    parser.add_argument('-c', '--column', default=0,
                        help='column (0-indexed) of series id (overriden by --headers')
    parser.add_argument('--resume', action='store_true',
                        help="equivalent to mode='a'. resumes progress if stopped"
                        " previously. overrides --force.")
    parser.add_argument('-d', '--delay', default=10,
                        help='# of seconds of delay between GET requests.')
    parser.add_argument('--listnames', default='rwuch')
    args = parser.parse_args()

    list_names = ['read']
    if args.all:
        list_names.extend(['wish', 'unfinished', 'complete', 'hold'])
    elif set(args.listnames).issubset('rwuch'):
        list_names = []
        if 'r' in args.listnames:
            list_names.append('read')
        if 'w' in args.listnames:
            list_names.append('wish')
        if 'u' in args.listnames:
            list_names.append('unfinished')
        if 'c' in args.listnames:
            list_names.append('complete')
        if 'h' in args.listnames:
            list_names.append('hold')
    else:
        print('--listnames', args.listnames, 'is invalid. Aborting...')
        exit(-1)

    mode = args.mode
    if args.resume:
        mode = 'a'
    elif args.force:
        mode = 'w'

    # Get unique series IDs from file
    series_ids = []
    with open(args.input, 'r', newline='') as csvfile:
        csvreader = csv.reader(csvfile)
        if args.headers:
            header_names = next(csvreader)
            if 'seriesid' in header_names:
                header = 'seriesid'
            elif 'series_id' in header_names:
                header = 'series_id'
            else:
                print('Error: No "seriesid" or "series_id" header in', args.INPUT)
                csvfile.close()
                exit(-1)
            sid_index = header_names.index('seriesid')
        else:
            sid_index = 0

        for i,row in enumerate(csvreader):
            if i >= int(args.N):
                break
            sid = int(row[sid_index])
            if sid not in series_ids:
                series_ids.append(sid)

    make_dataset(series_ids, filename=args.output, delay=args.delay, mode=mode,
                 list_names=list_names)
