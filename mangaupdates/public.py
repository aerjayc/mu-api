import requests
from bs4 import BeautifulSoup
import re
from functools import cached_property
import time
from dataclasses import dataclass, field
from typing import List, Any
from mangaupdates import exceptions
import json


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
            self._session = requests.Session()
        else:
            self._session = session

        if tentative_title is not None:
            self.title = tentative_title
            self._uses_tentative_title = True
        else:
            self._uses_tentative_title = False

    def __repr__(self):
        if self._uses_tentative_title:
            return f'Series(id={self.id}, tentative_title={repr(self.title)})'
        else:
            return f'Series(id={self.id})'

    def populate(self):
        self._response = self._session.get(f'{self.domain}/series.html', params={'id': self.id})
        self._response.raise_for_status()
        self._main_content = BeautifulSoup(self._response.content, 'lxml').find(id='main_content')

        # delete cache
        cached = ('activity_stats', 'anime_chapters', 'associated_names',
                  'completely_scanlated', 'description', 'entries', 'forum',
                  'image', 'last_updated', 'licensed_in_english', 'list_stats',
                  'original_publisher', 'series_type', 'status', 'title',
                  'user_rating', 'year')
        for key in cached:
            if key in self.__dict__:
                del self.__dict__[key]
        # no longer cached (generators):
        # 'related_series', 'groups_scanlating', 'latest_releases',
        # 'user_reviews', 'genre', 'categories', 'category_recommendations'
        # 'recommendations', 'authors', 'artists', 'serialized_in',
        # 'english_publisher'

    @cached_property
    def title(self):
        span = self._main_content.find('span', class_='releasestitle tabletitle')
        if span is None:
            raise exceptions.ParseError('Title')
        return span.get_text(strip=True)

    @cached_property
    def description(self):
        description_ = self._main_content.find(id='div_desc_link') or self._entries['Description']
        string = description_.get_text(strip=True)
        if string == 'N/A':
            return None
        else:
            return string

    @cached_property
    def _entries(self):
        sCats = self._main_content.find_all('div', class_='sCat')
        entries = {}
        for sCat in sCats:
            if sCat.b:
                key = next(sCat.b.children).strip() # to avoid <b>Name <div>something else</div></b>
                                                    # see Status/Status in Country of Origin
                entries[key] = sCat.find_next_sibling('div', class_='sContent')
        return entries

    @cached_property
    def series_type(self):
        return self._entries['Type'].get_text(strip=True)

    @property
    def related_series(self):
        a_tags = self._entries['Related Series'].find_all('a', href=True)
        for a in a_tags:
            title = a.get_text(strip=True)
            series_id = id_from_url(a['href'])
            relation = self.remove_outer_parens(a.next_sibling)
            yield RelatedSeries(series=Series(series_id, tentative_title=title),
                                relation=relation)

    @cached_property
    def associated_names(self):
        return (name for name in self._entries['Associated Names'].stripped_strings)

    @property
    def groups_scanlating(self):
        a_tags = self._entries['Groups Scanlating'].find_all('a', href=True)
        for a in a_tags:
            if a['href'].startswith('javascript'):  # skip 'More...' and 'Less...'
                continue
            group = Group(name=a.get_text(strip=True))
            if a.has_attr('title') and (a['title'] == 'Group Info'):
                group.id = id_from_url(a['href'])
            yield group

    @property
    def latest_releases(self):
        elements = list(self._entries['Latest Release(s)'].children)
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
                yield release
                release = Release(self.id)  # at last iteration release is not used

    @cached_property
    def status(self):
        return self._entries['Status'].get_text(strip=True)

    @cached_property
    def completely_scanlated(self):
        val = self._entries['Completely Scanlated?'].get_text(strip=True)
        if val == 'Yes':
            return True
        elif val == 'No':
            return False
        else:
            return None

    @cached_property
    def anime_chapters(self):
        strings = list(self._entries['Anime Start/End Chapter'].stripped_strings)
        if len(strings) == 1 and strings[0] == 'N/A':
            return None
        else:
            return strings

    @property
    def user_reviews(self):
        a_tags = self._entries['User Reviews'].find_all('a', href=True)
        for a in a_tags:
            review_id = id_from_url(a['href'])
            review_name = a.get_text(strip=True)
            reviewer = a.next_sibling.strip()[3:]   # remove 'by ' from 'by User'
            yield UserReview(review_id, review_name, reviewer)

    @cached_property
    def forum(self):
        string = next(self._entries['Forum'].stripped_strings)

        pattern = r'(\d+) topics, (\d+) posts'
        matches = re.search(pattern, string, re.IGNORECASE)
        if not matches:
            raise exceptions.RegexParseError(pattern=pattern, string=string)
        topics = int(matches.group(1))
        posts = int(matches.group(2))

        # extract forum id
        params = params_from_url(self._entries['Forum'].a['href'])
        if 'fid' not in params:
            raise exceptions.ParseError("Forum ('fid')")
        fid = int(params['fid'][0])

        return ForumStats(fid, topics, posts)

    @cached_property
    def user_rating(self):
        div = self._entries['User Rating']
        if div.get_text(strip=True) == 'N/A':
            return None

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
        updated = self._entries['Last Updated'].get_text(strip=True)
        if updated == 'N/A':
            return None
        else:
            return updated

    @cached_property
    def image(self):
        img = self._entries['Image'].img
        if img and img.has_attr('src'):
            return img['src']
        else:
            return None

    @property
    def genres(self):
        for u in self._entries['Genre'].select('a > u'):
            yield u.get_text(strip=True)

    @property
    def categories(self):
        score_pattern = re.compile(r'Score: (\d+) \((\d+),(\d+)\)', re.IGNORECASE)
        for a in self._entries['Categories'].select('li > a[title]'):
            string = a['title']
            matches = re.search(score_pattern, string)
            if not matches:
                raise exceptions.RegexParseError(pattern=score_pattern.pattern, string=string)

            score = int(matches.group(1))
            agree = int(matches.group(2))
            disagree = int(matches.group(3))
            name = a.get_text(strip=True)

            yield Category(name, score, agree, disagree)

    @property
    def category_recommendations(self):
        for a in self._entries['Category Recommendations'].find_all('a', href=True):
            series_id = id_from_url(a['href'])
            series_name = a.get_text(strip=True)
            yield Series(series_id, tentative_title=series_name)

    @property
    def recommendations(self):
        start_of_complete_list = False
        for a in self._entries['Recommendations'].find_all('a', href=True):
            if a['href'].startswith('javascript'):  # skips everything before 'More...'
                if a.get_text(strip=True) == 'More...':
                    start_of_complete_list = True
                continue

            if start_of_complete_list:
                series_id = id_from_url(a['href'])
                if series_id is None:
                    raise exceptions.ParseError('Recommendations (Series ID)')
                series_name = a.get_text(strip=True)
                series = Series(series_id, tentative_title=series_name)

                yield series

    @property
    def authors(self):
        for a in self._entries['Author(s)'].find_all('a', href=True):
            yield Author(id=id_from_url(a['href']),
                         name=a.get_text(strip=True))

    @property
    def artists(self):
        for a in self._entries['Artist(s)'].find_all('a', href=True):
            yield Author(id=id_from_url(a['href']),
                         name=a.get_text(strip=True))

    @cached_property
    def year(self):
        yr = self._entries['Year'].get_text(strip=True)
        if yr == 'N/A':
            return None
        else:
            return int(yr)

    @cached_property
    def original_publisher(self):
        a = self._entries['Original Publisher'].a
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

    @property
    def serialized_in(self):
        for a in self._entries['Serialized In (magazine)'].find_all('a', href=True):
            magazine = Magazine(url=f"{self.domain}/{a['href']}",
                                name=a.get_text(strip=True))
            if a.next_sibling and a.next_sibling.name is None:
                magazine.parent = self.remove_outer_parens(a.next_sibling)
            yield magazine

    @cached_property
    def licensed_in_english(self):
        val = self._entries['Licensed (in English)'].get_text(strip=True)
        if val == 'Yes':
            return True
        elif val == 'No':
            return False
        else:
            return None

    @property
    def english_publisher(self):
        for a in self._entries['English Publisher'].find_all('a', href=True):
            publisher = Publisher(id=id_from_url(a['href']),
                                  name=a.get_text(strip=True))
            if a.next_sibling and a.next_sibling.name is None:
                publisher.note = self.remove_outer_parens(a.next_sibling)
            yield publisher

    @cached_property
    def activity_stats(self):
        a_tags = self._entries['Activity Stats'].find_all('a', href=True)
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
        stats = {}
        for b in self._entries['List Stats'].find_all('b'):
            num_users = int(b.get_text(strip=True))
            if b.next_sibling and b.next_sibling.name is None:
                list_name = b.next_sibling.strip()
            else:
                raise exceptions.ParseError('List Stats (List Name)')
            key = ''.join((list_name[:-len(' lists')], '_total'))
            stats[key] = num_users
        return ListStats(self.id, **stats)

    def json(self):
        data = {'id': self.id,
                'title': self.title,
                'description': self.description,
                'series_type': self.series_type,
                'associated_names': list(self.associated_names),
                'status': self.status,
                'completely_scanlated': self.completely_scanlated,
                'anime_chapters': self.anime_chapters,
                'last_updated': self.last_updated,
                'image': self.image,
                'genres': list(self.genres),
                'year': self.year,
                'licensed_in_english': self.licensed_in_english
               }

        data['forum'] = {'id': self.forum.id,
                         'topics': self.forum.topics,
                         'posts': self.forum.posts
                        }

        data['user_rating'] = {'average': self.user_rating.average,
                               'bayesian_average': self.user_rating.bayesian_average,
                               'votes': self.user_rating.votes,
                               'distribution': self.user_rating.distribution
                              } if self.user_rating else None

        data['related_series'] = {}
        for series in self.related_series:
            data['related_series']['id'] = series.series.id
            data['related_series']['title'] = series.series.title
            data['related_series']['relation'] = series.relation

        data['groups_scanlating'] = {}
        for group in self.groups_scanlating:
            data['groups_scanlating']['id'] = group.id
            data['groups_scanlating']['name'] = group.name

        data['latest_releases'] = {}
        for release in self.latest_releases:
            data['latest_releases']['id'] = release.series_id
            data['latest_releases']['volume'] = release.volume
            data['latest_releases']['chapter'] = release.chapter
            for group in release.groups:
                data['latest_releases']['id'] = group.id
                data['latest_releases']['groups'] = group.name

        data['user_reviews'] = {}
        for review in self.user_reviews:
            data['user_reviews']['id'] = review.id
            data['user_reviews']['reviewer'] = review.reviewer
            data['user_reviews']['name'] = review.name

        data['categories'] = {}
        for category in self.categories:
            data['categories']['name'] = category.name
            data['categories']['score'] = category.score
            data['categories']['agree'] = category.agree
            data['categories']['disagree'] = category.disagree

        data['category_recommendations'] = {}
        for series in self.category_recommendations:
            data['category_recommendations']['id'] = series.id
            data['category_recommendations']['title'] = series.title

        data['recommendations'] = {}
        for series in self.recommendations:
            data['recommendations']['id'] = series.id
            data['recommendations']['title'] = series.title

        data['authors'] = {}
        for author in self.authors:
            data['authors']['id'] = author.id
            data['authors']['name'] = author.name

        data['artists'] = {}
        for author in self.authors:
            data['artists']['id'] = author.id
            data['artists']['name'] = author.name

        data['original_publisher'] = {'id': self.original_publisher.id,
                                      'name': self.original_publisher.name,
                                      'note': self.original_publisher.note
                                     } if self.original_publisher else None

        data['serialized_in'] = {}
        for magazine in self.serialized_in:
            data['serialized_in']['name'] = magazine.name
            data['serialized_in']['url'] = magazine.url
            data['serialized_in']['parent'] = magazine.parent

        data['english_publisher'] = {}
        for publisher in self.english_publisher:
            data['english_publisher']['name'] = publisher.name
            data['english_publisher']['id'] = publisher.id
            data['english_publisher']['note'] = publisher.note

        data['activity_stats'] = {'weekly': {'position': self.activity_stats.weekly.position,
                                             'change': self.activity_stats.weekly.change},
                                  'monthly': {'position': self.activity_stats.monthly.position,
                                              'change': self.activity_stats.monthly.change},
                                  'quarterly': {'position': self.activity_stats.quarterly.position,
                                                'change': self.activity_stats.quarterly.change},
                                  'semiannual': {'position': self.activity_stats.semiannual.position,
                                                 'change': self.activity_stats.monthly.change},
                                  'yearly': {'position': self.activity_stats.yearly.position,
                                             'change': self.activity_stats.yearly.change}
                                 }

        data['list_stats'] = {'id': self.list_stats.id,
                              'reading_total': self.list_stats.reading_total,
                              'wish_total': self.list_stats.wish_total,
                              'unfinished_total': self.list_stats.unfinished_total,
                              'custom_total': self.list_stats.custom_total
                             }

        return json.dumps(data)

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
            self._session = requests.Session()
        else:
            self._session = session

        self.reading_total = kwargs.get('reading_total')
        self.wish_total = kwargs.get('wish_total')
        self.unfinished_total = kwargs.get('unfinished_total')
        self.custom_total = kwargs.get('custom_total')
        self._kwarg = kwargs

    def __repr__(self):
        if self._kwarg:
            arguments = ', '.join('='.join((k,repr(v))) for k,v in self._kwarg.items())
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

        self._soups = {}
        for list_name in list_names:
            params['list'] = list_name
            response = self._session.get(url, params=params)
            response.raise_for_status()
            time.sleep(delay)

            self._soups[list_name] = BeautifulSoup(response.content, 'lxml')

    def general_list(self, list_name):
        rows = self._soups[list_name].p.find_next_sibling('p')
        if not rows:
            return None

        prefix = 'javascript:loadUser(' # for extracting the user id
        suffix = f',"{list_name}")'
        for a in rows.find_all('a', recursive=False, href=True):
            username = a.get_text(strip=True)
            user_id = int(a['href'][len(prefix):-len(suffix)])
            entry = ListEntry(series_id=self.id, user_id=user_id, username=username)

            if a.next_sibling == ' - Rating: ':
                entry.rating = float(a.find_next_sibling('b').get_text(strip=True))

            yield entry

    @property
    def read(self):
        return self.general_list('read')

    @property
    def wish(self):
        return self.general_list('wish')

    @property
    def unfinished(self):
        return self.general_list('unfinished')

    def json(self):
        data = {}
        for key in ('read', 'wish', 'unfinished'):
            data[key] = []
            for l in getattr(self, key):
                data[key].append({'id': l.series_id,
                                  'user_id': l.user_id,
                                  'username': l.username})
        return data
