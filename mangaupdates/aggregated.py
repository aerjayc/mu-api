import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from bs4 import BeautifulSoup
from .utils import id_from_url
import time
import csv


def get_most_listed(min_num_users=1, first_page=1, max_pages=None, delay=10, list_names=None, filename=None, MAX_RETRIES=5):
    """Extracts most-listed series on the site.

    Arguments:
        min_num_users (int): The point at which the function stops iterating over
                             pages
                             Default is 1
        num_pages (int): The max number of pages to iterate over
                         (overrides min_num_users if not `None`)
                         Default is `None`
        delay (int):     the number of secs delay after each GET request
        list_names ([str, str,...]):
                         The names of the lists to be searched
                         must be a subset of {'read', 'wish', 'unfinished'}
        filename (str): path to the file to which the function will export the
                        extracted list of tuples as a `.csv` file.
                        If `None` (default), the list will not be exported.
    Returns:
        [(series_id, series_name, num_users, list_name), ...]
    """

    url = 'https://www.mangaupdates.com/stats.html'
    if list_names is None:
        list_names = ('read', 'wish', 'unfinished', 'completed', 'hold')

    if filename is not None:
        f = open(filename, 'a', newline='')
        writer = csv.writer(f)
        writer.writerow(['series_id', 'series_name', 'num_users', 'list_name'])
    else:
        lists = []

    sess = requests.Session()
    retries = Retry(total=MAX_RETRIES, backoff_factor=3)
    sess.mount('http://', HTTPAdapter(max_retries=retries))
    for list_name in list_names:
        page = first_page
        num_users = min_num_users   # just to pass through first iteration
        while (max_pages is None and num_users >= min_num_users) or (max_pages is not None and page <= max_pages):
            params = {'list': list_name,
                      'act': 'list',
                      'perpage': 100,
                      'page': page}

            for _ in range(MAX_RETRIES):
                try:
                    print('Requesting', repr(list_name), 'page', params['page'], end='\t', flush=True)
                    response = sess.get(url, params=params)
                    response.raise_for_status()
                    break
                except requests.exceptions.ConnectionError as e:
                    print(e)
                    time.sleep(120)
                    print('Retrying...')
            else:       # no break
                print('Skipping page', page, '(exceeded MAX_RETRIES)')
                continue
            time.sleep(delay)

            soup = BeautifulSoup(response.content, 'lxml')
            table = soup.find(id='main_content').find('div', class_='row no-gutters')

            if filename is None:
                rows = []
            cell = table.div.find_next_sibling('div')
            while (cell := cell.find_next_sibling('div')):
                if 'col-1' in cell['class']:    # num_users
                    num_users = int(cell.get_text(strip=True))
                    # Note: `cell` also has an <a> with 'href' having an id
                    # but not of the list. Instead, it links to the series id.
                    # This is likely a bug since series_id != list_id, so it
                    # links to a different list (often it doesn't exist)
                elif 'col-11' in cell['class']: # series_name + id
                    series_id = id_from_url(cell.a['href'])
                    series_name = cell.a.get_text(strip=True)

                    # end of row
                    row = (series_id, series_name, num_users, list_name)
                    if filename is None:
                        rows.append(row)
                    else:
                        writer.writerows([row])

                    # reinitialize in case the other branch skips
                    # num_users = None

            print('`num_users`:', num_users)
            if num_users < min_num_users:
                break
            page += 1

            if filename is None:
                lists.extend(rows)

    if filename:
        f.close()
    else:
        return lists
