import requests
from bs4 import BeautifulSoup
import re
from functools import cached_property


class Manga:
    def __init__(self, manga_id):
        self.id = manga_id

    def populate(self):
        response = requests.get('https://www.mangaupdates.com/series.html',
                                params={'id': self.id})
        response.raise_for_status()
        self.main_content = BeautifulSoup(response.content, 'lxml').find(id='main_content')

    @cached_property
    def title(self):
        return self.main_content.select_one('span.releasestitle.tabletitle').text.strip()

    @cached_property
    def description(self):
        return self.main_content.find(id='div_desc_link').text.strip()

    @cached_property
    def entries(self):
        sCats = self.main_content.find_all('div', class_='sCat')
        entries = dict()
        for sCat in sCats:
            entries[sCat.text] = sCat.find_next_sibling('div', class_='sContent')
        return entries

    @cached_property
    def series_type(self):
        return self.entries['Type'].text.strip()

    @cached_property
    def related_series(self):
        series = []
        a_tags = self.entries['Related Series'].find_all('a')
        for a in a_tags:
            series_id = self.id_from_url(a['href'])
            series_name = a.text
            series_relation = a.next_sibling.strip()
            series.append((series_id, series_name, series_relation))

        return series

    @cached_property
    def associated_names(self):
        return list(self.entries['Associated Names'].stripped_strings)

    @cached_property
    def groups_scanlating(self):
        groups = []
        a_tags = self.entries['Groups Scanlating'].find_all('a')
        for a in a_tags:
            if 'href' not in a.attrs:
                continue
            if ('title' in a.attrs) and (a['title'] == 'Group Info'):
                group_id = self.id_from_url(a['href'])
                group_name = a.text
                groups.append((group_id, group_name))
            else:   # for groups without their own pages (e.g. Soka)
                matches = re.search(r'https?://(?:www\.)?mangaupdates.com/''releases\.html\?search=([\w\d]+)',
                                    a['href'], re.IGNORECASE)
                if matches:
                    groups.append((None, matches.group(1)))
        return groups

    @cached_property
    def latest_releases(self):
        pass

    @cached_property
    def status(self):
        pass

    @cached_property
    def completely_scanlated(self):
        pass

    @cached_property
    def anime_chapters(self):
        pass

    @cached_property
    def user_reviews(self):
        pass

    @cached_property
    def forum(self):
        pass

    @cached_property
    def user_rating(self):
        pass

    @cached_property
    def last_updated(self):
        pass

    @cached_property
    def image(self):
        pass

    @cached_property
    def genre(self):
        pass

    @cached_property
    def categories(self):
        pass

    @cached_property
    def category_recommendations(self):
        pass

    @cached_property
    def recommendations(self):
        pass

    @cached_property
    def authors(self):
        pass

    @cached_property
    def artists(self):
        pass

    @cached_property
    def year(self):
        pass

    @cached_property
    def original_publisher(self):
        pass

    @cached_property
    def serialized_in(self):
        pass

    @cached_property
    def licensed_in_english(self):
        pass

    @cached_property
    def english_publisher(self):
        pass

    @cached_property
    def activity_stats(self):
        pass

    @cached_property
    def list_stats(self):
        pass

    @staticmethod
    def id_from_url(string):
        matches = re.search(r'id=(\d+)', string, re.IGNORECASE)
        return int(matches.group(1)) if matches else None
