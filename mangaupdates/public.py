import requests
from bs4 import BeautifulSoup
import re
from collections import namedtuple
from functools import cached_property
import time
from dataclasses import dataclass, field
from typing import List, Any
import exceptions


# TODO: convert lists to generators
# TODO: make private methods as needed

@dataclass
class Group:
    name: str
    id: int = None

@dataclass
class RelatedSeries:
    series: Any     # should be Series (used `Any` to avoid recursive definition)
    relation: str

    def __repr__(self):
        return f'RelatedSeries({repr(self.series)}, relation={repr(self.relation)})'

@dataclass
class Release:
    series_id: int
    volume: str = None
    chapter: str = None
    groups: List[Group] = field(default_factory=list)
    elapsed: str = None

@dataclass
class UserReview:
    id: int
    reviewer: str
    name: str

@dataclass
class ForumStats:
    id: int
    topics: int
    posts: int

@dataclass
class UserRating:
    average: float
    bayesian_average: float
    votes: int
    distribution: dict

@dataclass
class Category:
    name: str
    score: int
    agree: int
    disagree: int

    def __repr__(self):
        return (f'Category({repr(self.name)}, score={self.score}, '
                f'agree={self.agree}, disagree={self.disagree})')

@dataclass
class Author:
    name: str
    id: int

    def __repr__(self):
        return f'Author({repr(self.name)}, id={self.id})'

@dataclass
class Publisher:
    name: str
    id: int
    note: str = None

    def __repr__(self):
        return f'Publisher({repr(self.name)}, id={self.id}, note={repr(self.note)})'

@dataclass
class Magazine:
    name: str
    url: str
    parent: str = None

    def __repr__(self):
        return f'Magazine({repr(self.name)}, url={repr(self.url)}, parent={repr(self.parent)})'

@dataclass
class Rank:
    position: int
    change: int = 0

@dataclass
class ActivityStats:
    weekly: Rank = None
    monthly: Rank = None
    quarterly: Rank = None
    semiannual: Rank = None
    yearly: Rank = None

@dataclass
class ListEntry:
    series_id: int
    user_id: int
    username: str
    rating: int = None


class Series:
    domain = 'https://www.mangaupdates.com'
    def __init__(self, id, session=None, tentative_title=None):
        self.id = id

        if session is None:
            self.session = requests.Session()
        else:
            self.session = session

        if tentative_title is not None:
            self.title = tentative_title
            self.__uses_tentative_title = True
        else:
            self.__uses_tentative_title = False

    def __repr__(self):
        if self.__uses_tentative_title:
            return f'Series(id={self.id}, tentative_title={repr(self.title)})'
        else:
            return f'Series(id={self.id})'

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
        if span is None:
            raise exceptions.ParseError('Title')
        return span.get_text(strip=True)

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
        entries = {}
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
        a_tags = self.entries['Related Series'].find_all('a', href=True)
        for a in a_tags:
            title = a.get_text(strip=True)
            series_id = id_from_url(a['href'])
            relation = self.remove_outer_parens(a.next_sibling)
            series.append(RelatedSeries(series=Series(series_id, tentative_title=title),
                                        relation=relation))
        return series

    @cached_property
    def associated_names(self):
        return (name for name in self.entries['Associated Names'].stripped_strings)

    @cached_property
    def groups_scanlating(self):
        groups = []
        a_tags = self.entries['Groups Scanlating'].find_all('a', href=True)
        for a in a_tags:
            if a['href'].startswith('javascript'):  # skip 'More...' and 'Less...'
                continue
            group = Group(name=a.get_text(strip=True))
            if a.has_attr('title') and (a['title'] == 'Group Info'):
                group.id = id_from_url(a['href'])
            groups.append(group)
        return groups

    @cached_property
    def latest_releases(self):
        elements = list(self.entries['Latest Release(s)'].children)
        releases = []
        release = Release(self.id)
        for element_index in range(len(elements)):
            element = elements[element_index]
            if element == 'v.':
                release.volume = elements[element_index + 1].get_text(strip=True)
            elif element == 'c.':
                release.chapter = elements[element_index + 1].get_text(strip=True)
            elif element.name == 'a' and element.has_attr('title') and element['title'] == 'Group Info':
                release.groups.append(Group(name=element.get_text(strip=True),
                                            id=id_from_url(element['href'])))
            elif element.previous_element.name is None and element.previous_element.strip() == 'by':
                release.groups.append(Group(name=element.get_text(strip=True)))
            elif element.name == 'span':
                release.elapsed = element.get_text(strip=True)
            elif element.name == 'br':
                releases.append(release)
                release = Release(self.id)  # at last iteration release is not used
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
            review_id = id_from_url(a['href'])
            review_name = a.get_text(strip=True)
            reviewer = a.next_sibling.strip()[3:]   # remove 'by ' from 'by User'
            reviews.append(UserReview(review_id, review_name, reviewer))
        return reviews

    @cached_property
    def forum(self):
        string = next(self.entries['Forum'].stripped_strings)

        pattern = r'(\d+) topics, (\d+) posts'
        matches = re.search(pattern, string, re.IGNORECASE)
        if not matches:
            raise exceptions.RegexParseError(pattern=pattern, string=string)
        topics = int(matches.group(1))
        posts = int(matches.group(2))

        # extract forum id
        params = params_from_url(self.entries['Forum'].a['href'])
        if 'fid' not in params:
            raise exceptions.ParseError("Forum ('fid')")
        fid = int(params['fid'][0])

        return ForumStats(fid, topics, posts)

    @cached_property
    def user_rating(self):
        div = self.entries['User Rating']

        string = div.next_element.strip()
        pattern = r'Average: (\d+\.?\d*)'
        matches = re.search(pattern, string, re.IGNORECASE)
        if not matches:
            raise exceptions.RegexParseError(pattern, string)
        average = float(matches.group(1))

        span = div.find('span')
        if span and span.next_sibling and span.next_sibling.name is None:
            string = span.next_sibling.strip()
            pattern = r'(\d+) votes'
            matches = re.search(pattern, string, re.IGNORECASE)
            if not matches:
                raise exceptions.RegexParseError(pattern=pattern, string=string)
            votes = int(matches.group(1))
        else:
            raise exceptions.ParseError('User Rating (Votes)')

        b = div.find('b')
        if b:
            string = b.get_text(strip=True)
            pattern = r'\d+\.?\d*'
            matches = re.search(pattern, string, re.IGNORECASE)
            if not matches:
                raise exceptions.RegexParseError(pattern=pattern, string=string)
            bayesian_average = float(matches.group(0))
        else:
            raise exceptions.ParseError('User Rating (Bayesian Average)')

        histogram = div.find_all('div', class_='row no-gutters')
        distribution = {}
        for bin in histogram:
            if bin.div:
                key = bin.div.get_text(strip=True)
                val = next(bin.find('div', class_='text-right').stripped_strings)
                distribution[key] = val

        return UserRating(average, bayesian_average, votes, distribution)

    @cached_property
    def last_updated(self):
        updated = self.entries['Last Updated'].get_text(strip=True)
        if updated == 'N/A':
            return None
        else:
            return updated

    @cached_property
    def image(self):
        img = self.entries['Image'].img
        if img and img.has_attr('src'):
            return img['src']
        else:
            return None

    @cached_property
    def genre(self):
        genres = []
        for u in self.entries['Genre'].select('a > u'):
            genres.append(u.get_text(strip=True))
        return genres

    @cached_property
    def categories(self):
        a_tags = self.entries['Categories'].select('li > a[title]')
        cats = []
        score_pattern = re.compile(r'Score: (\d+) \((\d+),(\d+)\)', re.IGNORECASE)
        for a in a_tags:
            string = a['title']
            matches = re.search(score_pattern, string)
            if not matches:
                raise exceptions.RegexParseError(pattern=score_pattern.pattern, string=string)
            score = int(matches.group(1))
            agree = int(matches.group(2))
            disagree = int(matches.group(3))
            name = a.get_text(strip=True)
            cats.append(Category(name, score, agree, disagree))
        return cats

    @cached_property
    def category_recommendations(self):
        a_tags = self.entries['Category Recommendations'].find_all('a', href=True)
        cat_recs = []
        for a in a_tags:
            series_id = id_from_url(a['href'])
            series_name = a.get_text(strip=True)
            cat_recs.append(Series(series_id, tentative_title=series_name))
        return cat_recs

    @cached_property
    def recommendations(self):
        a_tags = self.entries['Recommendations'].find_all('a', href=True)
        recs = []
        for a in a_tags:
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
        a_tags = self.entries['Author(s)'].find_all('a', href=True)
        authors = []
        for a in a_tags:
            authors.append(Author(id=id_from_url(a['href']),
                                  name=a.get_text(strip=True)))
        return authors

    @cached_property
    def artists(self):
        a_tags = self.entries['Artist(s)'].find_all('a', href=True)
        artists = []
        for a in a_tags:
            artists.append(Author(id=id_from_url(a['href']),
                                  name=a.get_text(strip=True)))
        return artists

    @cached_property
    def year(self):
        yr = self.entries['Year'].get_text(strip=True)
        if yr == 'N/A':
            return None
        else:
            return int(yr)

    @cached_property
    def original_publisher(self):
        a = self.entries['Original Publisher'].a
        if a:
            publisher_id = id_from_url(a.get('href'))
            if a.has_attr('title') and a['title'] == 'Publisher Info':
                publisher_name = a.get_text(strip=True)
            elif a.get_text(strip=True) == 'Add':
                publisher_name = a.parent.get_text(strip=True)[:-len('\xa0[Add]')]
            else:
                raise exceptions.ParseError('Original Publisher (Name)')
            return Publisher(publisher_id, publisher_name)
        else:
            return None

    @cached_property
    def serialized_in(self):
        a_tags = self.entries['Serialized In (magazine)'].find_all('a', href=True)
        magazines = []
        for a in a_tags:
            magazine = Magazine(url=f"{self.domain}/{a['href']}",
                                name=a.get_text(strip=True))
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
        a_tags = self.entries['English Publisher'].find_all('a', href=True)
        publishers = []
        for a in a_tags:
            publisher = Publisher(id=id_from_url(a['href']),
                                  name=a.get_text(strip=True))
            if a.next_sibling and a.next_sibling.name is None:
                publisher.note = self.remove_outer_parens(a.next_sibling)
            publishers.append(publisher)
        return publishers

    @cached_property
    def activity_stats(self):
        a_tags = self.entries['Activity Stats'].find_all('a', href=True)
        stats = ActivityStats()
        for a in a_tags:
            interval = a.get_text(strip=True)
            b = a.find_next_sibling('b')
            if not b:
                raise exceptions.ParseError('Activity Stats (Position)')
            position = int(b.get_text(strip=True))
            rank = Rank(position)

            img = a.find_next_sibling('img')
            if img and img.next_sibling and img.next_sibling.name is None:
                rank.change = int(self.remove_outer_parens(img.next_sibling))

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
                raise exceptions.ParseError('List Stats (List Name)')
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
    if 'id' in params:
        return int(params['id'][0])
    else:
        return None

class ListStats:
    def __init__(self, id, session=None, **kwargs):
        self.id = id

        if session is None:
            self.session = requests.Session()
        else:
            self.session = session

        self.reading_total = kwargs.get('reading_total')
        self.wish_total = kwargs.get('wish_total')
        self.unfinished_total = kwargs.get('unfinished_total')
        self.custom_total = kwargs.get('custom_total')
        self.__kwargs = kwargs

    def __repr__(self):
        if self.__kwargs:
            arguments = ', '.join('='.join((k,repr(v))) for k,v in self.__kwargs.items())
            return f'ListStats(id={self.id}, {arguments})'
        else:
            return f'ListStats(id={self.id})'

    def populate(self, delay=2, list_names=None):
        # https://www.mangaupdates.com/series.html?act=list&list=read&sid=33
        if list_names is None:
            list_names = ('read', 'wish', 'unfinished')

        url = 'https://www.mangaupdates.com/series.html'
        params = {'act': 'list',
                  'sid': self.id}

        self.soups = {}
        for list_name in list_names:
            params['list'] = list_name
            response = self.session.get(url, params=params)
            response.raise_for_status()
            time.sleep(delay)

            self.soups[list_name] = BeautifulSoup(response.content, 'lxml')

        # delete cache
        cached = ('read', 'wish', 'unfinished')
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
        for a in rows.find_all('a', recursive=False, href=True):
            username = a.get_text(strip=True)
            user_id = int(a['href'][len(prefix):-len(suffix)])
            entry = ListEntry(series_id=self.id, user_id=user_id, username=username)

            if a.next_sibling == ' - Rating: ':
                entry.rating = float(a.find_next_sibling('b').get_text(strip=True))

            entries.append(entry)

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
