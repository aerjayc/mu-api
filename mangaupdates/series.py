import requests
from bs4 import BeautifulSoup
import re
import time
import json
import dateutil.parser

from functools import cached_property
from dataclasses import dataclass, field
from typing import List, Any

from mangaupdates import exceptions
from .authors import Author
from .groups import Group
from .publishers import Publisher, Magazine
from .tags import Category
from .users import UserReview, UserRating
from .utils import remove_outer_parens, params_from_url, id_from_url


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
class ForumStats:
    id: int
    topics: int
    posts: int

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

    def __init__(self, id, session=None, title=None):
        """Initializes Series object

        Arguments:
            - id (int): Series id
            - session (requests.Session):
                Optional. Session to be used by the Series instance.
                Defaults to None. If None, a new requests.Session object is used.
            - title (str):
                Optional. Title assigned to the series. Defaults to None.
                Will be overriden by new information provided by the `populate()`
                method.
        Returns
            Series
        """

        self.id = id

        if session is None:
            self._session = requests.Session()
        else:
            self._session = session

        if title is not None:
            self.title = title
            self._uses_tentative_title = True
        else:
            self._uses_tentative_title = False

    def __repr__(self):
        if self._uses_tentative_title:
            return f'Series(id={self.id}, title={repr(self.title)})'
        else:
            return f'Series(id={self.id})'

    def populate(self):
        """Re/loads the series webpage. Needs to be called to access the class
        properties.
        """

        self._response = self._session.get(f'{self.domain}/series.html', params={'id': self.id})
        self._response.raise_for_status()
        self._main_content = BeautifulSoup(self._response.content, 'lxml').find(id='main_content')
        _ = self._entries

        # delete cache
        cached = ('activity_stats', 'anime_chapters',
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
        """The title of the series.

        Returns:
            - str: Title
        Raises:
            - exceptions.UnpopulatedError: If `.populate()` hasn't been called yet
            - exceptions.ParseError: If HTML content is unexpected
        """

        try:
            span = self._main_content.find('span', class_='releasestitle tabletitle')
        except AttributeError:
            raise exceptions.UnpopulatedError

        if span is None:
            raise exceptions.ParseError('Title')
        return span.get_text(strip=True)

    @cached_property
    def description(self):
        """The description of the series.

        Returns either:
            - str: Description
                 (Note: not fully working, as it requires javascript to get the
                 entire description)
            - None: If series has no description
        Raises:
            - exceptions.UnpopulatedError: If `.populate()` hasn't been called yet
        """

        try:
            description_ = self._main_content.find(id='div_desc_link') or self._entries['Description']
        except AttributeError:
            raise exceptions.UnpopulatedError

        string = description_.get_text(strip=True)
        if string == 'N/A':
            return None
        else:
            return string

    @cached_property
    def _entries(self):
        """Snippets of HTML to be parsed by the property methods.

        Returns:
            - dict[key] = bs4.element.Tag:
                A dict of html tags from which the properties will be parsed.
                The keys are the bold text inside the HTML elements with
                `class="sCat"`
        Raises:
            - exceptions.UnpopulatedError: If `.populate()` hasn't been called yet
        """

        try:
            sCats = self._main_content.find_all('div', class_='sCat')
        except AttributeError:
            raise exceptions.UnpopulatedError

        entries = {}
        for sCat in sCats:
            if sCat.b:
                key = next(sCat.b.children).strip() # to avoid <b>Name <div>something else</div></b>
                                                    # see Status/Status in Country of Origin
                entries[key] = sCat.find_next_sibling('div', class_='sContent')
        return entries

    @cached_property
    def series_type(self):
        """Type of series (Manga, Manhwa, etc.)

        Returns:
            - str: Type of series
        Raises:
            - exceptions.UnpopulatedError: If `.populate()` hasn't been called yet
        """

        if '_entries' not in self.__dict__:
            raise exceptions.UnpopulatedError

        return self._entries['Type'].get_text(strip=True)

    @property
    def related_series(self):
        """Series related to this series (Spin-offs, etc.)

        Yields:
            - RelatedSeries:
                Series related to this series. Contains a `Series` object
                and its relation (str).
                Can be accessed by:
                    RelatedSeries.series     # Series object
                    RelatedSeries.relation   # str
        Raises:
            - exceptions.UnpopulatedError: If `.populate()` hasn't been called yet
        """

        if '_entries' not in self.__dict__:
            raise exceptions.UnpopulatedError

        a_tags = self._entries['Related Series'].find_all('a', href=True)
        for a in a_tags:
            title = a.get_text(strip=True)
            series_id = id_from_url(a['href'])
            relation = remove_outer_parens(a.next_sibling)
            yield RelatedSeries(series=Series(series_id, title=title),
                                relation=relation)

    @property
    def associated_names(self):
        """Other/associated names of the series

        Yields:
            - str: Name associated to the series
        Raises:
            - exceptions.UnpopulatedError: If `.populate()` hasn't been called yet
        """

        if '_entries' not in self.__dict__:
            raise exceptions.UnpopulatedError

        return (name for name in self._entries['Associated Names'].stripped_strings)

    @property
    def groups_scanlating(self):
        """Other/associated names of the series

        Yields:
            - Group:
                Group that has scanlated the series.
                    Group.name               # str
                    Group.id                 # int
        Raises:
            - exceptions.UnpopulatedError: If `.populate()` hasn't been called yet
        """

        if '_entries' not in self.__dict__:
            raise exceptions.UnpopulatedError

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
        """Latest releases of the series

        Yields:
            - Release
                Release.series_id            # int/None
                Release.volume               # str/None
                Release.chapter              # str/None
                Release.groups               # list[Group]
                    Release.groups.name      # str
                    Release.groups.id        # int
                Release.elapsed              # str

        Raises:
            - exceptions.UnpopulatedError: If `.populate()` hasn't been called yet
        """

        if '_entries' not in self.__dict__:
            raise exceptions.UnpopulatedError

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
        """Status of the series

        Returns:
            - str: Status ('Complete', 'Ongoing', etc).
        Raises:
            - exceptions.UnpopulatedError: If `.populate()` hasn't been called yet
        """

        if '_entries' not in self.__dict__:
            raise exceptions.UnpopulatedError

        return self._entries['Status'].get_text(strip=True)

    @cached_property
    def completely_scanlated(self):
        """Completely scanlated?

        Returns either:
            - bool
            - None: If the parsed string is neither 'Yes' nor 'No'
        Raises:
            - exceptions.UnpopulatedError: If `.populate()` hasn't been called yet
        """

        if '_entries' not in self.__dict__:
            raise exceptions.UnpopulatedError

        val = self._entries['Completely Scanlated?'].get_text(strip=True)
        if val == 'Yes':
            return True
        elif val == 'No':
            return False
        else:
            return None

    @cached_property
    def anime_chapters(self):
        """Chapters of the series that were adapted into anime (if adapted)

        Returns either:
            - list[str]
            - None: If series has not been adapted to anime
        Raises:
            - exceptions.UnpopulatedError: If `.populate()` hasn't been called yet
        """

        if '_entries' not in self.__dict__:
            raise exceptions.UnpopulatedError

        strings = list(self._entries['Anime Start/End Chapter'].stripped_strings)
        if len(strings) == 1 and strings[0] == 'N/A':
            return None
        else:
            return strings

    @property
    def user_reviews(self):
        """User Reviews of the series

        Yields:
            - UserReview
                UserReview.id                    # int
                UserReview.reviewer              # str
                UserReview.name                  # str
        Raises:
            - exceptions.UnpopulatedError: If `.populate()` hasn't been called yet
        """

        if '_entries' not in self.__dict__:
            raise exceptions.UnpopulatedError

        a_tags = self._entries['User Reviews'].find_all('a', href=True)
        for a in a_tags:
            review_id = id_from_url(a['href'])
            review_name = a.get_text(strip=True)
            reviewer = a.next_sibling.strip()[3:]   # remove 'by ' from 'by User'
            yield UserReview(review_id, review_name, reviewer)

    @cached_property
    def forum(self):
        """User Reviews of the series

        Returns:
            - ForumStats
                ForumStats.id                # int
                ForumStats.topics            # int
                ForumStats.posts             # int
        Raises:
            - exceptions.UnpopulatedError: If `.populate()` hasn't been called yet
            - exceptions.RegexParseError: If HTML content is unexpected
            - exceptions.ParseError: If HTML content is unexpected
        """

        if '_entries' not in self.__dict__:
            raise exceptions.UnpopulatedError

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
        """User Rating of the series

        Returns either:
            - UserRating
                UserRating.average                   # int
                UserRating.bayesian_average          # int
                UserRating.votes                     # int
                UserRating.distribution              # dict
            - None: If no user ratings
        Raises:
            - exceptions.UnpopulatedError: If `.populate()` hasn't been called yet
            - exceptions.RegexParseError: If HTML content is unexpected
            - exceptions.ParseError: If HTML content is unexpected
        """

        if '_entries' not in self.__dict__:
            raise exceptions.UnpopulatedError

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
        """Timestamp when the series was last updated

        Returns either:
            - str: <Month> <Date>th <Year>, <Hour>:<Minute><am/pm> <timezone>
            - None: If no releases
        Raises:
            - exceptions.UnpopulatedError: If `.populate()` hasn't been called yet
        """

        if '_entries' not in self.__dict__:
            raise exceptions.UnpopulatedError

        updated = self._entries['Last Updated'].get_text(strip=True)
        if updated == 'N/A':
            return None
        else:
            return dateutil.parser.parse(updated)

    @cached_property
    def image(self):
        """Series Image URL

        Returns either:
            - str: URL of series image
            - None: If no image
        Raises:
            - exceptions.UnpopulatedError: If `.populate()` hasn't been called yet
        """

        if '_entries' not in self.__dict__:
            raise exceptions.UnpopulatedError

        img = self._entries['Image'].img
        if img and img.has_attr('src'):
            return img['src']
        else:
            return None

    @property
    def genres(self):
        """Genres of the series

        Yields:
            - str: genre
        Raises:
            - exceptions.UnpopulatedError: If `.populate()` hasn't been called yet
        """

        if '_entries' not in self.__dict__:
            raise exceptions.UnpopulatedError

        for u in self._entries['Genre'].select('a > u'):
            yield u.get_text(strip=True)

    @property
    def categories(self):
        """Categories of the series

        Yields:
            - Category
                Category.name                    # str
                Category.score                   # int
                Category.agree                   # int
                Category.disagree                # int
        Raises:
            - exceptions.UnpopulatedError: If `.populate()` hasn't been called yet
            - exceptions.RegexParseError: If HTML content is unexpected
        """

        if '_entries' not in self.__dict__:
            raise exceptions.UnpopulatedError

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
        """Series recommendations (based on category)

        Yields:
            - Series
                Series.id                        # int
                Series.title                     # str
        Raises:
            - exceptions.UnpopulatedError: If `.populate()` hasn't been called yet
        """

        if '_entries' not in self.__dict__:
            raise exceptions.UnpopulatedError

        for a in self._entries['Category Recommendations'].find_all('a', href=True):
            series_id = id_from_url(a['href'])
            series_name = a.get_text(strip=True)
            yield Series(series_id, title=series_name)

    @property
    def recommendations(self):
        """Series recommendations

        Yields:
            - Series
                Series.id                        # int
                Series.title                     # str
        Raises:
            - exceptions.UnpopulatedError: If `.populate()` hasn't been called yet
        """

        if '_entries' not in self.__dict__:
            raise exceptions.UnpopulatedError

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
                series = Series(series_id, title=series_name)

                yield series

    @property
    def authors(self):
        """Authors of the series

        Yields:
            - Author
                Author.name                          # str
                Author.id                            # int
        Raises:
            - exceptions.UnpopulatedError: If `.populate()` hasn't been called yet
        """

        if '_entries' not in self.__dict__:
            raise exceptions.UnpopulatedError

        for a in self._entries['Author(s)'].find_all('a', href=True):
            yield Author(id=id_from_url(a['href']),
                         name=a.get_text(strip=True))

    @property
    def artists(self):
        """Artists of the series

        Yields:
            - Author
                Author.name                          # str
                Author.id                            # int
        Raises:
            - exceptions.UnpopulatedError: If `.populate()` hasn't been called yet
        """

        if '_entries' not in self.__dict__:
            raise exceptions.UnpopulatedError

        for a in self._entries['Artist(s)'].find_all('a', href=True):
            yield Author(id=id_from_url(a['href']),
                         name=a.get_text(strip=True))

    @cached_property
    def year(self):
        """Year the series was first released

        Returns either:
            - int: Year
            - None: If no year listed
        Raises:
            - exceptions.UnpopulatedError: If `.populate()` hasn't been called yet
        """

        if '_entries' not in self.__dict__:
            raise exceptions.UnpopulatedError

        yr = self._entries['Year'].get_text(strip=True)
        if yr == 'N/A':
            return None
        else:
            return int(yr)

    @cached_property
    def original_publisher(self):
        """Original publisher of the series

        Returns either:
            - Publisher
                Publisher.id
                Publisher.name
            - None: If no publisher listed
        Raises:
            - exceptions.UnpopulatedError: If `.populate()` hasn't been called yet
        """

        if '_entries' not in self.__dict__:
            raise exceptions.UnpopulatedError

        a = self._entries['Original Publisher'].a
        if a:
            publisher_id = id_from_url(a.get('href'))
            if a.has_attr('title') and a['title'] == 'Publisher Info':
                publisher_name = a.get_text(strip=True)
            elif a.get_text(strip=True) == 'Add':
                publisher_name = a.parent.get_text(strip=True)[:-len('\xa0[Add]')]
            else:
                raise exceptions.ParseError('Original Publisher (Name)')
            return Publisher(publisher_name, publisher_id)
        else:
            return None

    @property
    def serialized_in(self):
        """Magazines in which the series was serialized

        Yields:
            - Magazine
                Magazine.name                            # str
                Magazine.url                             # str
                Magazine.parent                          # str
        Raises:
            - exceptions.UnpopulatedError: If `.populate()` hasn't been called yet
        """

        if '_entries' not in self.__dict__:
            raise exceptions.UnpopulatedError

        for a in self._entries['Serialized In (magazine)'].find_all('a', href=True):
            magazine = Magazine(url=f"{self.domain}/{a['href']}",
                                name=a.get_text(strip=True))
            if a.next_sibling and a.next_sibling.name is None:
                magazine.parent = remove_outer_parens(a.next_sibling)
            yield magazine

    @cached_property
    def licensed_in_english(self):
        """Licensed in English?

        Returns either:
            - bool
            - None: If the parsed string is neither 'Yes' nor 'No'
        Raises:
            - exceptions.UnpopulatedError: If `.populate()` hasn't been called yet
        """

        if '_entries' not in self.__dict__:
            raise exceptions.UnpopulatedError

        val = self._entries['Licensed (in English)'].get_text(strip=True)
        if val == 'Yes':
            return True
        elif val == 'No':
            return False
        else:
            return None

    @property
    def english_publisher(self):
        """English Publisher

        Yields:
            - Publisher
                Publisher.name                           # str
                Publisher.id                             # int
                Publisher.note                           # str
        Raises:
            - exceptions.UnpopulatedError: If `.populate()` hasn't been called yet
        """

        if '_entries' not in self.__dict__:
            raise exceptions.UnpopulatedError

        for a in self._entries['English Publisher'].find_all('a', href=True):
            publisher = Publisher(id=id_from_url(a['href']),
                                  name=a.get_text(strip=True))
            if a.next_sibling and a.next_sibling.name is None:
                publisher.note = remove_outer_parens(a.next_sibling)
            yield publisher

    @cached_property
    def activity_stats(self):
        """Activity Stats

        Returns:
            - ActivityStats
                ActivityStats.weekly                     # Rank
                ActivityStats.monthly                    # Rank
                ActivityStats.quarterly                  # Rank
                ActivityStats.semiannual                 # Rank
                ActivityStats.yearly                     # Rank
                    # Rank.position              # int
                    # Rank.change                # int
        Raises:
            - exceptions.UnpopulatedError: If `.populate()` hasn't been called yet
        """

        if '_entries' not in self.__dict__:
            raise exceptions.UnpopulatedError

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
                rank.change = int(remove_outer_parens(img.next_sibling))

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
        """Series list statistics

        Returns:
            - ListStats
                ListStats.id                             # int
                ListStats.reading_total                  # int
                ListStats.wish_total                     # int
                ListStats.unfinished_total               # int
                ListStats.custom_total                   # int
        Raises:
            - exceptions.UnpopulatedError: If `.populate()` hasn't been called yet
        """

        if '_entries' not in self.__dict__:
            raise exceptions.UnpopulatedError

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
        """Export Series object as json

        Returns:
            - str
        Raises:
            - exceptions.UnpopulatedError: If `.populate()` hasn't been called yet
            - exceptions.RegexParseError: If HTML content is unexpected
            - exceptions.ParseError: If HTML content is unexpected
        """

        data = {'id': self.id,
                'title': self.title,
                'description': self.description,
                'series_type': self.series_type,
                'associated_names': list(self.associated_names),
                'groups_scanlating': [group.__dict__ for group in self.groups_scanlating],
                'status': self.status,
                'completely_scanlated': self.completely_scanlated,
                'anime_chapters': self.anime_chapters,
                'user_reviews': [review.__dict__ for review in self.user_reviews],
                'forum': self.forum.__dict__,
                'user_rating': self.user_rating.__dict__ if self.user_rating else None,
                'last_updated': self.last_updated.strftime('%B %dth %Y, %I:%M%p %Z'),
                'image': self.image,
                'genres': list(self.genres),
                'categories': [category.__dict__ for category in self.categories],
                'authors': [author.__dict__ for author in self.authors],
                'artists': [artist.__dict__ for artist in self.authors],
                'year': self.year,
                'original_publisher': self.original_publisher.__dict__ if self.original_publisher else None,
                'serialized_in': [magazine.__dict__ for magazine in self.serialized_in],
                'licensed_in_english': self.licensed_in_english,
                'english_publisher': [publisher.__dict__ for publisher in self.english_publisher],
               }

        data['related_series'] = []
        for i, series in enumerate(self.related_series):
            data['related_series'].append({'id': series.series.id,
                                           'title': series.series.title,
                                           'relation': series.relation})

        data['category_recommendations'] = []
        for series in self.category_recommendations:
            data['category_recommendations'].append({'id': series.id,
                                                     'title': series.title})

        data['recommendations'] = []
        for series in self.recommendations:
            data['recommendations'].append({'id': series.id,
                                            'title': series.title})

        data['latest_releases'] = []
        for release in self.latest_releases:
            data['latest_releases'].append({'id': release.series_id,
                                            'volume': release.volume,
                                            'chapter': release.chapter,
                                            'groups': [group.__dict__ for group in release.groups]})

        data['activity_stats'] = {'weekly': self.activity_stats.weekly.__dict__,
                                  'monthly': self.activity_stats.monthly.__dict__,
                                  'quarterly': self.activity_stats.quarterly.__dict__,
                                  'semiannual': self.activity_stats.semiannual.__dict__,
                                  'yearly': self.activity_stats.yearly.__dict__
                                 }

        data['list_stats'] = {'id': self.list_stats.id,
                              'reading_total': self.list_stats.reading_total,
                              'wish_total': self.list_stats.wish_total,
                              'unfinished_total': self.list_stats.unfinished_total,
                              'custom_total': self.list_stats.custom_total,
                             }

        return json.dumps(data)

class ListStats:
    def __init__(self, id, session=None, **kwargs):
        """Initializes ListStats object

        Arguments:
            - id (int): Series id
            - session (requests.Session):
                Optional. Session to be used by the Series instance.
                Defaults to None. If None, a new requests.Session object is used.
            - reading_total/wish_total/unfinished_total/custom_total (int):
                Optional. Number of users who added the series on the
                corresponding list. Used by Series object.
        Returns
            ListStats
        """

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
        """Re/loads the various List webpages for the series.
        """

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
        """Users who have added the series to their list specified by `list_name`

        Yields:
            - ListEntry
                ListEntry.series_id                      # int
                ListEntry.user_id                        # int
                ListEntry.username                       # str
                ListEntry.rating                         # float
            - None: If there are no entries
        """

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
        """Users who have added the series to their reading list

        Yields either:
            - ListEntry
            - None: If there are no entries
        """

        return self.general_list('read')

    @property
    def wish(self):
        """Users who have added the series to their wish list

        Yields either:
            - ListEntry
            - None: If there are no entries
        """

        return self.general_list('wish')

    @property
    def unfinished(self):
        """Users who have added the series to their unfinished list

        Yields either:
            - ListEntry
            - None: If there are no entries
        """

        return self.general_list('unfinished')

    def json(self):
        """Export ListStats object as json

        Returns:
            - str
        """

        data = {}
        for key in ('read', 'wish', 'unfinished'):
            data[key] = []
            for l in getattr(self, key):
                data[key].append({'id': l.series_id,
                                  'user_id': l.user_id,
                                  'username': l.username})
        return data
