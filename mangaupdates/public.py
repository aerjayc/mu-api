import requests
from bs4 import BeautifulSoup
import re
from collections import namedtuple
from functools import cached_property
import time
from dataclasses import dataclass, field
from typing import List, Any


# TODO: convert lists to generators
# TODO: convert `x = d[key] if key in d else None` to `x = d.get(key)`
# TODO: conver `x = dict()` to `x ={}`
# TODO: add `__repr__` methods

@dataclass
class Group:
    id: int = None
    name: str = None

@dataclass
class RelatedSeries:
    series: Any
    relation: str = None

@dataclass
class Release:
    volume: str = None
    chapter: str = None
    groups: List[Group] = field(default_factory=list)
    elapsed: str = None

@dataclass
class UserReview:
    id: int = None
    reviewer: str = None
    name: str = None

@dataclass
class ForumStats:
    id: int = None
    topics: int = 0
    posts: int = 0

@dataclass
class UserRating:
    # average, bayesian_average, votes, distribution
    average: float = None
    bayesian_average: float = None
    votes: int = None
    distribution: dict = field(default_factory=dict)

@dataclass
class Category:
    name: str = None
    score: int = None
    agree: int = None
    disagree: int = None

@dataclass
class Recommendation:
    id: int = None
    name: str = None

@dataclass
class Author:
    id: int = None
    name: str = None

@dataclass
class Publisher:
    id: int = None
    name: str = None
    note: str = None

@dataclass
class Magazine:
    name: str = None
    url: str = None
    parent: str = None

@dataclass
class Rank:
    position: int
    change: int

@dataclass
class ActivityStats:
    weekly: Rank = None
    monthly: Rank = None
    quarterly: Rank = None
    semiannual: Rank = None
    yearly: Rank = None


class Series:
    domain = 'https://www.mangaupdates.com'
    def __init__(self, series_id, session=None, tentative_title=None):
        self.id = series_id

        if session is None:
            self.session = requests.Session()
        else:
            self.session = session

        if tentative_title is None:
            self.title = tentative_title

    def populate(self):
        self.response = self.session.get(f'{self.domain}/series.html', params={'id': self.id})
        self.response.raise_for_status()
        self.main_content = BeautifulSoup(self.response.content, 'lxml').find(id='main_content')

        # delete cache
        cached = ('activity_stats', 'anime_chapters', 'artists',
                  'associated_names', 'authors', 'categories',
                  'category_recommendations', 'completely_scanlated',
                  'description', 'english_publisher', 'entries', 'forum',
                  'genre', 'groups_scanlating', 'image', 'last_updated',
                  'latest_releases', 'licensed_in_english', 'list_stats',
                  'original_publisher', 'recommendations', 'related_series',
                  'serialized_in', 'series_type', 'status', 'title',
                  'user_rating', 'user_reviews', 'year')
        for key in cached:
            if key in self.__dict__:
                del self.__dict__[key]

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
            title = a.get_text(strip=True)
            series_id = id_from_url(a.get('href'))
            rs = RelatedSeries(Series(series_id, tentative_title=title))

            if a.next_sibling.name is None:
                rs.relation = self.remove_outer_parens(a.next_sibling)
            series.append(rs)
        return series

    @cached_property
    def associated_names(self):
        return (name for name in self.entries['Associated Names'].stripped_strings)

    @cached_property
    def groups_scanlating(self):
        groups = []
        a_tags = self.entries['Groups Scanlating'].find_all('a', href=True)
        for a in a_tags:
            group = Group()
            if a.has_attr('title') and (a['title'] == 'Group Info'):
                group.id = id_from_url(a['href'])
                group.name = a.get_text(strip=True)
            else:   # for groups without their own pages (e.g. Soka)
                matches = re.search(r'https?://(?:www\.)?mangaupdates.com/releases\.html\?search=([\w\d]+)',
                                    a['href'], re.IGNORECASE)
                if matches: # use urldecode?
                    group.name = matches.group(1)
            groups.append(group)
        return groups

    @cached_property
    def latest_releases(self):
        elements = list(self.entries['Latest Release(s)'].children)
        releases = []
        release = Release()
        for element_index in range(len(elements)):
            element = elements[element_index]
            if element == 'v.':
                release.volume = elements[element_index + 1].get_text(strip=True)
            elif element == 'c.':
                release.chapter = elements[element_index + 1].get_text(strip=True)
            elif element.name == 'a' and element.has_attr('title') and element['title'] == 'Group Info':
                group = Group()
                group.name = element.get_text(strip=True)
                if element.has_attr('href'):
                    group.id = id_from_url(element['href'])
                release.groups.append(group)
            elif element.name == 'span':
                release.elapsed = element.get_text(strip=True)
            elif element.name == 'br':
                releases.append(release)
                release = Release()     # at last iteration release is not used
        return releases

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
            review = UserReview()
            review.id = id_from_url(a['href'])
            review.name = a.get_text(strip=True)
            if a.next_sibling and a.next_sibling.name is None and a.next_sibling.strip().startswith('by '):
                review.reviewer = a.next_sibling.strip()[3:]   # remove 'by ' from 'by User'
            reviews.append(review)
        return reviews

    @cached_property
    def forum(self):
        string = next(self.entries['Forum'].stripped_strings)

        forum_stats = ForumStats()
        matches = re.search(r'(\d+) topics, (\d+) posts', string, re.IGNORECASE)
        if matches:
            forum_stats.topics = int(matches.group(1))
            forum_stats.posts = int(matches.group(2))

        # extract forum id
        params = params_from_url(self.entries['Forum'].a['href'])
        if 'fid' in params:
            forum_stats.id = int(params['fid'][0])

        return forum_stats

    @cached_property
    def user_rating(self):
        div = self.entries['User Rating']
        ur = UserRating()

        string = div.next_element.strip()
        matches = re.search(r'Average: (\d+\.?\d*)', string, re.IGNORECASE)
        ur.average = float(matches.group(1)) if matches else None

        span = div.find('span')
        if span and span.next_sibling and span.next_sibling.name is None:
            string = span.next_sibling.strip()
            matches = re.search(r'(\d+) votes', string, re.IGNORECASE)
            if matches:
                ur.votes = int(matches.group(1))

        b = div.find('b')
        if b:
            string = b.get_text(strip=True)
            matches = re.search(r'\d+\.?\d*', string, re.IGNORECASE)
            if matches:
                ur.bayesian_average = float(matches.group(0))

        histogram = div.find_all('div', class_='row no-gutters')
        distribution = dict()
        for bin in histogram:
            if bin.div:
                key = bin.div.get_text(strip=True)
                val = next(bin.find('div', class_='text-right').stripped_strings)
                ur.distribution[key] = val

        return ur

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
                cat = Category()
                cat.name = a.get_text(strip=True)
                matches = re.search(score_pattern, a['title'])
                if matches:
                    cat.score = int(matches.group(1))
                    cat.agree = int(matches.group(2))
                    cat.disagree = int(matches.group(3))
                cats.append(cat)
        return cats

    @cached_property
    def category_recommendations(self):
        a_tags = self.entries['Category Recommendations'].find_all('a')
        cat_recs = []
        for a in a_tags:
            series_id = id_from_url(a['href']) if a.has_attr('href') else None
            series_name = a.get_text(strip=True)
            cat_recs.append(Series(series_id, tentative_title=series_name))
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
                series = Series(series_id, tentative_title=series_name)
                if series not in recs:    # avoid duplicates
                    recs.append(series)
        return recs

    @cached_property
    def authors(self):
        a_tags = self.entries['Author(s)'].find_all('a')
        authors = []
        for a in a_tags:
            author = Author()
            if a.has_attr('href'):
                author.id = id_from_url(a['href'])
            author.name = a.get_text(strip=True)
            authors.append(author)
        return authors

    @cached_property
    def artists(self):
        a_tags = self.entries['Artist(s)'].find_all('a')
        artists = []
        for a in a_tags:
            artist = Author()
            if a.has_attr('href'):
                artist.id = id_from_url(a['href'])
            artist.name = a.get_text(strip=True)
            artists.append(artist)
        return artists

    @cached_property
    def year(self):
        yr = self.entries['Year'].get_text(strip=True)
        return None if yr == 'N/A' else int(yr)

    @cached_property
    def original_publisher(self):
        a = self.entries['Original Publisher'].a
        if a:
            publisher = Publisher()
            publisher.id = id_from_url(a['href']) if a.has_attr('href') else None
            if a.has_attr('title') and a['title'] == 'Publisher Info':
                publisher.name = a.get_text(strip=True)
            elif a.get_text(strip=True) == 'Add':
                publisher.name = a.parent.get_text(strip=True)[:-len('\xa0[Add]')]
            else:
                return None
            return publisher
        else:
            return None

    @cached_property
    def serialized_in(self):
        a_tags = self.entries['Serialized In (magazine)'].find_all('a')
        magazines = []
        for a in a_tags:
            magazine = Magazine()
            if a.has_attr('href'):
                magazine.url = f"{self.domain}/{a['href']}"
            magazine.name = a.get_text(strip=True)
            if a.next_sibling and a.next_sibling.name is None:
                magazine.parent = self.remove_outer_parens(a.next_sibling)
            magazines.append(magazine)
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
            publisher = Publisher()
            if a.has_attr('href'):
                publisher.id = id_from_url(a['href'])
            publisher.name = a.get_text(strip=True)
            if a.next_sibling and a.next_sibling.name is None:
                publisher.note = self.remove_outer_parens(a.next_sibling)
            publishers.append(publisher)
        return publishers

    @cached_property
    def activity_stats(self):
        # TODO: parse and return position changes
        a_tags = self.entries['Activity Stats'].find_all('a')
        stats = ActivityStats()
        for a in a_tags:
            interval = a.get_text(strip=True)
            b = a.find_next_sibling('b')
            change = int(b.get_text(strip=True)) if b else None
            img = a.find_next_sibling('img')
            if img and img.next_sibling and img.next_sibling.name is None:
                position = int(self.remove_outer_parens(img.next_sibling))
            rank = Rank(position, change)

            if interval == 'Weekly':
                stats.weekly = rank
            elif interval == 'Monthly':
                stats.monthly = rank
            elif interval == '3 Month':
                stats.quarterly = rank
            elif interval == '6 Month':
                stats.semiannual = rank
            elif interval == 'Year':
                stats.yearly = rank
        return stats

    @cached_property
    def list_stats(self):
        b_tags = self.entries['List Stats'].find_all('b')
        stats = {}
        for b in b_tags:
            num_users = int(b.get_text(strip=True))
            if b.next_sibling and b.next_sibling.name is None:
                list_name = b.next_sibling.strip()
            else:
                list_name = None
            key = ''.join((list_name[:-len(' lists')], '_total'))
            stats[key] = num_users
        return ListStats(self.id, **stats)

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
    def __init__(self, series_id, session=None, **kwargs):
        self.id = series_id

        if session is None:
            self.session = requests.Session()
        else:
            self.session = session

        self.reading_total = kwargs.get('reading_total')
        self.wish_total = kwargs.get('wish_total')
        self.unfinished_total = kwargs.get('unfinished_total')
        self.custom_total = kwargs.get('custom_total')

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

        # delete cache
        cached = ('read', 'wish', 'unfinished', 'custom')
        for key in cached:
            if key in self.__dict__:
                del self.__dict__[key]

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

