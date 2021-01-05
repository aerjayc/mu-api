import requests
from bs4 import BeautifulSoup
from .public import id_from_url
import time


def get_stats(min_users, delay=3):
    url = 'https://www.mangaupdates.com/stats.html'
    lists = dict()
    for list_name in ('read',):#, 'wish', 'unfinished'):
        page = 1
        num_lists = min_users   # just to pass through first iteration
        while num_lists >= min_users:
            params = {'list': list_name,
                      'act': 'list',
                      'perpage': 100,
                      'page': page}
            response = requests.get(url, params=params)
            response.raise_for_status()
            print('requested', response.url)
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
                    rows.append((series_id, series_name, num_lists))

                    # reinitialize in case the other branch skips
                    # num_lists = None

            if num_lists < min_users:
                break
            page += 1

        lists[list_name] = rows
    return rows
