from mangaupdates import Series, ListStats
import csv
import pandas as pd
import time
import os
import os.path
import argparse


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
        list_names = ('read', 'wish', 'unfinished')
    print('Lists:', list_names)

    for i, sid in enumerate(series_ids):
        lists = ListStats(sid)
        print(sid, end='\t\t', flush=True)
        lists.populate(list_names=list_names)
        time.sleep(delay)


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
            new_rows = [(*val, key, sid) for val in lists.general_list(key)]
            print(key, f'{len(new_rows)} rows.', sep='\t')
            if filename is None:
                rows.extend(new_rows)
            else:
                writer.writerows(new_rows)

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
    args = parser.parse_args()

    list_names = ['read']
    if args.all:
        list_names.extend(['wish', 'unfinished'])

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

    make_dataset(series_ids, filename=args.output, delay=10, mode=mode,
                 list_names=list_names)
