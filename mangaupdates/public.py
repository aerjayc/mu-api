import requests
from bs4 import BeautifulSoup
import re
from functools import cached_property
import time


class Series:
    domain = 'https://www.mangaupdates.com'
    def __init__(self, series_id, session=None):
        self.id = series_id

        if session is None:
            self.session = requests.Session()
        else:
            self.session = session

    def populate(self):
        self.response = self.session.get(f'{self.domain}/series.html', params={'id': self.id})
        self.response.raise_for_status()
        self.main_content = BeautifulSoup(self.response.content, 'lxml').find(id='main_content')

    @cached_property
    def title(self):
        span = self.main_content.select_one('span.releasestitle.tabletitle')
        if span:
            return span.get_text(strip=True)
        else:
            return None

    @cached_property
    def description(self):
        description_ = self.main_content.find(id='div_desc_link') or self.entries['Description']
        string = description_.get_text(strip=True)
        if string == 'N/A':
            return None
        else:
            return string

    @cached_property
    def entries(self):
        sCats = self.main_content.find_all('div', class_='sCat')
        entries = dict()
        for sCat in sCats:
            if sCat.b:
                key = next(sCat.b.children).strip() # to avoid <b>Name <div>something else</div></b>
                                                    # see Status/Status in Country of Origin
                entries[key] = sCat.find_next_sibling('div', class_='sContent')
        return entries

    @cached_property
    def series_type(self):
        return self.entries['Type'].get_text(strip=True)

    @cached_property
    def related_series(self):
        series = []
        a_tags = self.entries['Related Series'].find_all('a')
        for a in a_tags:
            series_id = id_from_url(a['href']) if a.has_attr('href') else None
            series_name = a.get_text(strip=True)
            if a.next_sibling.name is None:
                series_relation = self.remove_outer_parens(a.next_sibling)
            else:
                series_relation = None
            series.append((series_id, series_name, series_relation))

        return series

    @cached_property
    def associated_names(self):
        return list(self.entries['Associated Names'].stripped_strings)

    @cached_property
    def groups_scanlating(self):
        groups = []
        a_tags = self.entries['Groups Scanlating'].find_all('a', href=True)
        for a in a_tags:
            if a.has_attr('title') and (a['title'] == 'Group Info'):
                group_id = id_from_url(a['href'])
                group_name = a.get_text(strip=True)
                groups.append((group_id, group_name))
            else:   # for groups without their own pages (e.g. Soka)
                matches = re.search(r'https?://(?:www\.)?mangaupdates.com/releases\.html\?search=([\w\d]+)',
                                    a['href'], re.IGNORECASE)
                if matches: # use urldecode?
                    groups.append((None, matches.group(1)))
        return groups

    @cached_property
    def latest_releases(self):
        elements = list(self.entries['Latest Release(s)'].children)
        rows = []
        volume = None
        chapter = None
        groups = []
        how_long = None
        for element_index in range(len(elements)):
            element = elements[element_index]
            if element == 'v.':
                volume = elements[element_index + 1].get_text(strip=True)
            elif element == 'c.':
                chapter = elements[element_index + 1].get_text(strip=True)
            elif element.name == 'a' and element.has_attr('title') and element['title'] == 'Group Info':
                group_name = element.get_text(strip=True)
                group_id = id_from_url(element['href']) if element.has_attr('href') else None
                groups.append((group_id, group_name))
            elif element.name == 'span':
                how_long = element.get_text(strip=True)
            elif element.name == 'br':
                rows.append((volume, chapter, groups, how_long))
                volume = None
                chapter = None
                groups = []
                how_long = None
                continue
        return rows
            

    @cached_property
    def status(self):
        return self.entries['Status'].get_text(strip=True)

    @cached_property
    def completely_scanlated(self):
        val = self.entries['Completely Scanlated?'].get_text(strip=True)
        if val == 'Yes':
            return True
        elif val == 'No':
            return False
        else:
            return None

    @cached_property
    def anime_chapters(self):
        strings = list(self.entries['Anime Start/End Chapter'].stripped_strings)
        if len(strings) == 1 and strings[0] == 'N/A':
            return None
        else:
            return strings

    @cached_property
    def user_reviews(self):
        reviews = []
        a_tags = self.entries['User Reviews'].find_all('a', href=True)
        for a in a_tags:
            review_id = id_from_url(a['href'])
            review_name = a.get_text(strip=True)
            if a.next_sibling and a.next_sibling.name is None and a.next_sibling.strip().startswith('by '):
                reviewer = a.next_sibling.strip()[3:]   # remove 'by ' from 'by User'
            else:
                reviewer = None
            reviews.append((review_id, reviewer, review_name))
        return reviews

    @cached_property
    def forum(self):
        # extract numbers
        num_topics = 0
        num_posts = 0
        string = next(self.entries['Forum'].stripped_strings)
        matches = re.search(r'(\d+) topics, (\d+) posts', string, re.IGNORECASE)
        if matches:
            num_topics = int(matches.group(1))
            num_posts = int(matches.group(2))

        # extract forum id
        params = params_from_url(self.entries['Forum'].a['href'])
        fid = int(params['fid'][0]) if 'fid' in params else None

        return (fid, num_topics, num_posts)

    @cached_property
    def user_rating(self):
        average, votes, bayesian_average = None, None, None
        div = self.entries['User Rating']

        string = div.next_element.strip()
        matches = re.search(r'Average: (\d+\.?\d*)', string, re.IGNORECASE)
        average = float(matches.group(1)) if matches else None

        span = div.find('span')
        if span and span.next_sibling and span.next_sibling.name is None:
            string = span.next_sibling.strip()
            matches = re.search(r'(\d+) votes', string, re.IGNORECASE)
            votes = int(matches.group(1)) if matches else None

        b = div.find('b')
        if b:
            string = b.get_text(strip=True)
            matches = re.search(r'\d+\.?\d*', string, re.IGNORECASE)
            bayesian_average = float(matches.group(0)) if matches else None

        histogram = div.find_all('div', class_='row no-gutters')
        distribution = dict()
        for bin in histogram:
            if bin.div:
                key = bin.div.get_text(strip=True)
                val = next(bin.find('div', class_='text-right').stripped_strings)
                distribution[key] = val

        return (average, bayesian_average, votes, distribution)

    @cached_property
    def last_updated(self):
        updated = self.entries['Last Updated'].get_text(strip=True)
        return None if updated == 'N/A' else updated

    @cached_property
    def image(self):
        img = self.entries['Image'].img
        return img['src'] if img and img.has_attr('src') else None

    @cached_property
    def genre(self):
        genres = []
        for u in self.entries['Genre'].select('a > u'):
            genres.append(u.get_text(strip=True))
        return genres

    @cached_property
    def categories(self):
        a_tags = self.entries['Categories'].select('li > a')
        cats = []
        score_pattern = re.compile(r'Score: (\d+) \((\d+),(\d+)\)', re.IGNORECASE)
        for a in a_tags:
            if a.has_attr('title'):
                matches = re.search(score_pattern, a['title'])
                if matches:
                    score = int(matches.group(1))
                    agree = int(matches.group(2))
                    disagree = int(matches.group(3))
                else:
                    score, agree, disagree = None, None, None
                cats.append((a.get_text(strip=True), score, (agree, disagree)))
        return cats

    @cached_property
    def category_recommendations(self):
        a_tags = self.entries['Category Recommendations'].find_all('a')
        cat_recs = []
        for a in a_tags:
            series_id = id_from_url(a['href']) if a.has_attr('href') else None
            series_name = a.get_text(strip=True)
            cat_recs.append((series_id, series_name))
        return cat_recs

    @cached_property
    def recommendations(self):
        a_tags = self.entries['Recommendations'].find_all('a')
        recs = []
        for a in a_tags:
            if a.has_attr('href'):
                series_id = id_from_url(a['href'])
                if series_id is None:   # to avoid `More...` or `Less...` links
                    continue
                series_name = a.get_text(strip=True)
                if (series_id, series_name) not in recs:    # avoid duplicates
                    recs.append((series_id, series_name))
        return recs

    @cached_property
    def authors(self):
        a_tags = self.entries['Author(s)'].find_all('a')
        authors = []
        for a in a_tags:
            author_id = id_from_url(a['href']) if a.has_attr('href') else None
            author_name = a.get_text(strip=True)
            authors.append((author_id, author_name))
        return authors

    @cached_property
    def artists(self):
        a_tags = self.entries['Artist(s)'].find_all('a')
        artists = []
        for a in a_tags:
            artist_id = id_from_url(a['href']) if a.has_attr('href') else None
            artist_name = a.get_text(strip=True)
            artists.append((artist_id, artist_name))
        return artists

    @cached_property
    def year(self):
        year_ = self.entries['Year'].get_text(strip=True)
        return None if year_ == 'N/A' else int(year_)

    @cached_property
    def original_publisher(self):
        a = self.entries['Original Publisher'].a
        if a:
            publisher_id = id_from_url(a['href']) if a.has_attr('href') else None
            if a.has_attr('title') and a['title'] == 'Publisher Info':
                publisher_name = a.get_text(strip=True)
            elif a.get_text(strip=True) == 'Add':
                publisher_name = a.parent.get_text(strip=True)[:-len('\xa0[Add]')]
            else:
                return None
            return (publisher_id, publisher_name)
        else:
            return None

    @cached_property
    def serialized_in(self):
        a_tags = self.entries['Serialized In (magazine)'].find_all('a')
        magazines = []
        for a in a_tags:
            magazine_url = f"{self.domain}/{a['href']}" if a.has_attr('href') else None
            magazine_name = a.get_text(strip=True)
            if a.next_sibling and a.next_sibling.name is None:
                magazine_parent = self.remove_outer_parens(a.next_sibling)
            else:
                magazine_parent = None
            magazines.append((magazine_url, magazine_name, magazine_parent))
        return magazines

    @cached_property
    def licensed_in_english(self):
        val = self.entries['Licensed (in English)'].get_text(strip=True)
        if val == 'Yes':
            return True
        elif val == 'No':
            return False
        else:
            return None

    @cached_property
    def english_publisher(self):
        a_tags = self.entries['English Publisher'].find_all('a')
        publishers = []
        for a in a_tags:
            publisher_id = id_from_url(a['href']) if a.has_attr('href') else None
            publisher_name = a.get_text(strip=True)
            if a.next_sibling and a.next_sibling.name is None:
                publisher_note = self.remove_outer_parens(a.next_sibling)
            else:
                publisher_note = None
            publishers.append((publisher_id, publisher_name, publisher_note))
        return publishers

    @cached_property
    def activity_stats(self):
        a_tags = self.entries['Activity Stats'].find_all('a')
        stats = []
        for a in a_tags:
            interval = a.get_text(strip=True)
            img = a.find_next_sibling('img')
            if img and img.next_sibling and img.next_sibling.name is None:
                position = int(self.remove_outer_parens(img.next_sibling))
            else:
                position = None
            stats.append((interval, position))
        return stats

    @cached_property
    def list_stats(self):
        b_tags = self.entries['List Stats'].find_all('b')
        stats = []
        for b in b_tags:
            num_users = int(b.get_text(strip=True))
            if b.next_sibling and b.next_sibling.name is None:
                list_name = b.next_sibling.strip()
            else:
                list_name = None
            stats.append((list_name, num_users))
        return stats

    @staticmethod
    def remove_outer_parens(string, strip=True):
        if strip:
            string = string.strip()
        if string.startswith('(') and string.endswith(')'):
            return string[1:-1]
        else:
            return string

# from https://stackoverflow.com/a/5075477
def params_from_url(url):
    import urllib.parse as urlparse
    from urllib.parse import parse_qs
    parsed = urlparse.urlparse(url)
    return parse_qs(parsed.query)

def id_from_url(url):
    params = params_from_url(url)
    return int(params['id'][0]) if 'id' in params else None

class ListStats:
    def __init__(self, series_id, session=None):
        self.id = series_id

        if session is None:
            self.session = requests.Session()
        else:
            self.session = session

    def populate(self, delay=2, list_names=None):
        # https://www.mangaupdates.com/series.html?act=list&list=read&sid=33
        if list_names is None:
            list_names = ('read', 'wish', 'unfinished')

        url = 'https://www.mangaupdates.com/series.html'
        params = {'act': 'list',
                  'sid': self.id}

        self.soups = dict()
        for list_name in list_names:
            params['list'] = list_name
            response = self.session.get(url, params=params)
            response.raise_for_status()
            time.sleep(delay)

            self.soups[list_name] = BeautifulSoup(response.content, 'lxml')

    def general_list(self, list_name):
        rows = self.soups[list_name].p.find_next_sibling('p')
        if not rows:
            return None

        prefix = 'javascript:loadUser(' # for extracting the user id
        suffix = f',"{list_name}")'
        entries = []
        for a in rows.find_all('a', recursive=False):
            username = a.get_text(strip=True)
            user_id = int(a['href'][len(prefix):-len(suffix)])

            if a.next_sibling == ' - Rating: ':
                rating = float(a.find_next_sibling('b').get_text(strip=True))
            else:
                rating = None

            entries.append((user_id, username, rating))

        return entries

    @cached_property
    def read(self):
        return self.general_list('read')

    @cached_property
    def wish(self):
        return self.general_list('wish')

    @cached_property
    def unfinished(self):
        return self.general_list('unfinished')

    @cached_property
    def custom(self):
        return self.general_list('custom')

