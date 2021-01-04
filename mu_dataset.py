from mangaupdates import public
import pandas as pd

def make_dataset(series_ids):

    rows = []
    for sid in series_ids:
        lists = public.ListStats(sid)
        lists.populate()

        for key in ('read', 'wish', 'unfinished', 'custom'):
            rows.extend([(*row, key) for row in lists.general_list(key)])

    dataset = pd.DataFrame(rows)

    return dataset
