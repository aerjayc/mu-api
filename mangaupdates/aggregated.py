import requests
from bs4 import BeautifulSoup
from .public import id_from_url
import time


def get_most_listed(min_users, max_pages=None, delay=10, list_names=None):
    """Extracts most-listed series on the site.

    Arguments:
        min_users (int): the point at which the function stops iterating over
                         pages
        num_pages (int): the max number of pages to iterate over
                         (overrides min_users if not None)
        delay (int):     the number of secs delay after each GET request
        list_names ([str, str,...]): 
                         the names of the lists to be searched
                         must be a subset of {'read', 'wish', 'unfinished'}            
    Returns: 
        [(series_id, series_name, num_lists, list_name), ...]
    """

    url = 'https://www.mangaupdates.com/stats.html'
    if list_names is None:
        list_names = ('read', 'wish', 'unfinished')

    lists = []
    for list_name in list_names:
        page = 1
        num_lists = min_users   # just to pass through first iteration
        while (max_pages is None and num_lists >= min_users) or (max_pages is not None and page < max_pages):
            params = {'list': list_name,
                      'act': 'list',
                      'perpage': 100,
                      'page': page}
            response = requests.get(url, params=params)
            print('Requested', response.url, end='\t')
            response.raise_for_status()
            time.sleep(delay)

            soup = BeautifulSoup(response.content, 'lxml')
            table = soup.find(id='main_content').find('div', class_='row no-gutters')

            rows = []
            cell = table.div.find_next_sibling('div')
            while (cell := cell.find_next_sibling('div')):
                if 'col-1' in cell['class']:    # num_lists
                    num_lists = int(cell.get_text(strip=True))
                    # Note: `cell` also has an <a> with 'href' having an id
                    # but not of the list. Instead, it links to the series id.
                    # This is likely a bug since series_id != list_id, so it
                    # links to a different list (often it doesn't exist)
                elif 'col-11' in cell['class']: # series_name + id
                    series_id = id_from_url(cell.a['href'])
                    series_name = cell.a.get_text(strip=True)

                    # end of row
                    rows.append((series_id, series_name, num_lists, list_name))

                    # reinitialize in case the other branch skips
                    # num_lists = None

            print('`num_lists`:', num_lists)
            if num_lists < min_users:
                break
            page += 1

        lists.extend(rows)
    return lists

def export_most_listed(filename, *args, **kwargs):
    import csv

    lists = get_most_listed(*args, **kwargs)
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(lists)

