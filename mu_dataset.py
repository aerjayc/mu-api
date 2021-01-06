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
