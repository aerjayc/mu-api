import requests
from bs4 import BeautifulSoup
import re
from functools import cached_property


class Manga:
    domain = 'https://www.mangaupdates.com'
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
            entries[sCat.b.text] = sCat.find_next_sibling('div', class_='sContent')
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
            if a.has_attr('title') and (a['title'] == 'Group Info'):
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
        elements = list(self.entries['Latest Release(s)'].children)
        rows = []
        volume = None
        chapter = None
        groups = []
        how_long = None
        for element_index in range(len(elements)):
            element = elements[element_index]
            if element.name == 'br':
                rows.append((volume, chapter, groups, how_long))
                volume = None
                chapter = None
                groups = []
                how_long = None
                continue
            elif element == 'v.':
                volume = elements[element_index + 1].text
            elif element == 'c.':
                chapter = elements[element_index + 1].text
            elif element.name == 'a' and element.has_attr('title') and element['title'] == 'Group Info':
                group_name = element.text
                group_id = self.id_from_url(element['href']) if element.has_attr('href') else None
                groups.append((group_id, group_name))
            elif element.name == 'span':
                how_long = element.text
        return rows
            

    @cached_property
    def status(self):
        return self.entries['Status in Country of Origin'].text.strip()

    @cached_property
    def completely_scanlated(self):
        val = self.entries['Completely Scanlated?'].text.strip()
        if val == 'Yes':
            return True
        elif val == 'No':
            return False
        else:
            return None

    @cached_property
    def anime_chapters(self):
        return self.entries['Anime Start/End Chapter'].stripped_strings

    @cached_property
    def user_reviews(self):
        reviews = []
        a_tags = self.entries['User Reviews'].find_all('a')
        for a in a_tags:
            if a.has_attr('href'):
                review_id = self.id_from_url(a['href'])
                review_name = a.text
                reviewer = a.next_sibling.strip()[3:]   # remove 'by ' from 'by User'
                reviews.append((review_id, review_name, reviewer))
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
        fid = params['fid'] if 'fid' in params else None

        return (fid, num_topics, num_posts)

    @cached_property
    def user_rating(self):
        div = self.entries['User Rating']
        string = div.next_element.strip()
        matches = re.search(r'Average: (\d+\.?\d*)', string, re.IGNORECASE)
        average = float(matches.group(1)) if matches else None

        string = div.find('span').next_sibling
        matches = re.search(r'(\d+) votes', string, re.IGNORECASE)
        votes = int(matches.group(1)) if matches else None

        string = div.find('b').text.strip()
        matches = re.search(r'\d+\.?\d*', string, re.IGNORECASE)
        bayesian_average = float(matches.group(0)) if matches else None

        histogram = div.find_all('div', class_='row no-gutters')
        distribution = dict()
        for bin in histogram:
            key = bin.div.text
            val = next(bin.find('div', class_='text-right').stripped_strings)
            distribution[key] = val

        return (average, bayesian_average, votes, distribution)

    @cached_property
    def last_updated(self):
        return self.entries['Last Updated'].text.strip()

    @cached_property
    def image(self):
        return self.entries['Image'].img['src'] if self.entries['Image'].img else None

    @cached_property
    def genre(self):
        genres = []
        for u in self.entries['Genre'].select('a > u'):
            genres.append(u.text)
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
            cats.append((a.text, score, (agree, disagree)))
        return cats

    @cached_property
    def category_recommendations(self):
        a_tags = self.entries['Category Recommendations'].find_all('a')
        cat_recs = []
        for a in a_tags:
            series_id = self.id_from_url(a['href']) if a.has_attr('href') else None
            series_name = a.text
            cat_recs.append((series_id, series_name))
        return cat_recs

    @cached_property
    def recommendations(self):
        a_tags = self.entries['Recommendations'].find_all('a')
        recs = []
        for a in a_tags:
            if a.has_attr('href'):
                series_id = self.id_from_url(a['href'])
                if series_id is None:   # to avoid `More...` or `Less...` links
                    continue
                series_name = a.text
                if (series_id, series_name) not in recs:    # avoid duplicates
                    recs.append((series_id, series_name))
        return recs

    @cached_property
    def authors(self):
        a_tags = self.entries['Author(s)'].find_all('a')
        authors = []
        for a in a_tags:
            author_id = self.id_from_url(a['href']) if a.has_attr('href') else None
            author_name = a.text
            authors.append((author_id, author_name))
        return authors

    @cached_property
    def artists(self):
        a_tags = self.entries['Artist(s)'].find_all('a')
        artists = []
        for a in a_tags:
            artist_id = self.id_from_url(a['href']) if a.has_attr('href') else None
            artist_name = a.text
            artists.append((artist_id, artist_name))
        return artists

    @cached_property
    def year(self):
        return int(self.entries['Year'].text.strip())

    @cached_property
    def original_publisher(self):
        a = self.entries['Original Publisher'].a
        publisher_id = self.id_from_url(a['href']) if a.has_attr('href') else None
        publisher_name = a.text
        return (publisher_id, publisher_name)

    @cached_property
    def serialized_in(self):
        a_tags = self.entries['Serialized In (magazine)'].find_all('a')
        magazines = []
        for a in a_tags:
            magazine_url = f"{self.domain}/{a['href']}" if a.has_attr('href') else None
            magazine_name = a.text
            magazine_parent = a.next_sibling.strip()[1:-1]  # remove leading/trailing parens
            magazines.append((magazine_url, magazine_name))
        return magazines

    @cached_property
    def licensed_in_english(self):
        val = self.entries['Licensed (in English)'].text.strip()
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
            publisher_id = self.id_from_url(a['href']) if a.has_attr('href') else None
            publisher_name = a.text
            publishers.append((publisher_id, publisher_name))
        return publishers

    @cached_property
    def activity_stats(self):
        a_tags = self.entries['Activity Stats'].find_all('a')
        stats = []
        for a in a_tags:
            interval = a.text
            position = int(a.find_next_sibling('img').next_sibling[1:-1])    # to remove parens
            stats.append((interval, position))
        return stats

    @cached_property
    def list_stats(self):
        b_tags = self.entries['List Stats'].find_all('b')
        stats = []
        for b in b_tags:
            num_users = int(b.text)
            list_name = b.next_sibling.strip()
            stats.append((list_name, num_users))
        return stats

    @staticmethod
    def id_from_url(url):
        ## only match `id=(\d+)`, not (say) `pid=(\d+)`
        #matches = re.search(r'(?:^|[^a-z])id=(\d+)', string, re.IGNORECASE)
        #return int(matches.group(1)) if matches else None
        params = params_from_url(url)
        return int(params['id'][0]) if 'id' in params else None

# from https://stackoverflow.com/a/5075477
def params_from_url(url):
    import urllib.parse as urlparse
    from urllib.parse import parse_qs
    parsed = urlparse.urlparse(url)
    return parse_qs(parsed.query)
