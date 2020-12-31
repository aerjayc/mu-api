import requests
from bs4 import BeautifulSoup
from functools import cached_property


class Manga:
    def __init__(self, manga_id):
        self.id = manga_id

        response = requests.get('https://www.mangaupdates.com/series.html',
                                params={'id': manga_id})
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'lxml')

        self.main_content = soup.find(id='main_content')

    @cached_property
    def title(self):
        span = self.main_content.select_one('span.releasestitle.tabletitle')
        assert span, f'No title found in {self.id}'
        return span.text

    @cached_property
    def description(self):
        div = self.main_content.select_one('#div_desc_link')
        assert div, f'No description found in {self.id}'
        return div.text

    @cached_property
    def sC(self):
        sCats = self.main_content.find_all('div', class_='sCat')
        d = dict()
        for sCat in sCats:
            d[sCat.text] = sCat.find_next_sibling('div', class_='sContent')
        return d

