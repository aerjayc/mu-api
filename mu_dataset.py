from mangaupdates import public
import csv
import pandas as pd
import time


def make_dataset(series_ids, filename=None, delay=10, list_names=None):

    col_names = ('userid', 'username', 'score', 'listname', 'seriesid')
    if filename is not None:
        f = open(filename, 'a', newline='')
        writer = csv.writer(f)
        writer.writerows([col_names])

    if filename is None:
        rows = []

    if list_names is None:
        list_names = ('read', 'wish', 'unfinished')
    print('Lists:', list_names)

    for sid in series_ids:
        lists = public.ListStats(sid)
        print(sid, end='\t')
        lists.populate(list_names=list_names)
        time.sleep(delay)

        for key in list_names:
            new_rows = [(*val, key, sid) for val in lists.general_list(key)]
            print(f'{key}:', len(new_rows), 'rows.')
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
    lists_fname = 'lists.csv'
    dataset_fname = 'the_dataset.csv'
    list_names = ['read']
    headers = False
    N = 10

    # Get unique series IDs from file
    series_ids = []
    with open(lists_fname, newline='') as csvfile:
        csvreader = csv.reader(csvfile)
        if headers:
            header_names = next(csvreader)
            sid_index = header_names.index('seriesid')
        else:
            sid_index = 0

        for i,row in enumerate(csvreader):
            if i >= N:
                break
            sid = int(row[sid_index])
            if sid not in series_ids:
                series_ids.append(sid)
    print(series_ids)
    make_dataset(series_ids, filename=dataset_fname, delay=10, list_names=list_names)
