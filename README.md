# Unofficial MangaUpdates API

A simple python package for accessing data from MangaUpdates, acting as an 
*unofficial* API. (In Progress...)

## Usage

To load a Series page from MangaUpdates (given a series ID):

```python3
>>> import mangaupdates
>>> series = mangaupdates.Series(33)
>>> series.populate()          # execute GET request
```

The `.populate()` method should be called to load the actual webpage of the
series. To access some of the basic information about the series:

```python3
>>> series.title
'One Piece'
>>> series.description
'Before the Pirate King was executed, he dared the many pirates of the world
to seek out the fortune that he left behind ...'
>>> series.series_type
'Manga'
>>> series.status
'98 Volumes (Ongoing)'
>>> series.completely_scanlated
False
>>> series.anime_chapters
['Starts at Vol 1, Chap 1']
>>> series.last_updated
datetime.datetime(2021, 1, 18, 13, 48, tzinfo=tzlocal())
>>> series.image
'https://www.mangaupdates.com/image/i334567.jpg'
>>> series.year
1997
>>> series.licensed_in_english
True
```

### Properties that return dataclasses

For properties that have multiple fields (e.g. an author has a `name` and `id`),
this API uses custom dataclasses instead of dictionaries (hoping that in the
future those dataclasses will be replaced by actual classes that fetch more
data about itself. Consider an `Author` class from a `Series` instance, which
you can immediately use to access the author page of that series). Thus,
instead of accessing the data by `author['name']`, we should instead do
`author.name`.

#### Forum Statistics:

```python3
>>> series.forum
ForumStats(id=38, topics=353, posts=5556)
>>> series.forum.id
38
>>> series.forum.topics
353
>>> series.forum.posts
5556
```

#### User Ratings:

```python3
>>> series.user_rating
UserRating(average=9.0, bayesian_average=8.98, votes=4510, distribution={'10': '60%', '9+': '18%', '8+': '10%', '7+': '4%', '6+': '2%', '5+': '1%', '4+': '1%', '3+': '0%', '2+': '0%', '1+': '3%'})
>>> series.user_rating.average
9.0
>>> series.user_rating.bayesian_average
8.98
>>> series.user_rating.votes
4510
>>> series.user_rating.distribution
{'10': '60%', '9+': '18%', '8+': '10%', '7+': '4%', '6+': '2%', '5+': '1%', '4+': '1%', '3+': '0%', '2+': '0%', '1+': '3%'}
```

### Properties that return generators

This API returns generators instead of lists, wherever possible, since some
entries return a lot of data. In those cases, you can access them all at once
using `list()`.

#### Associated Names

```python3
>>> list(series.associated_names)
['Budak Getah (Malay)', 'قطعة واحدة', 'وان پیس', 'ون بيس', 'วันพีซ', ...
```

#### Related Series
```python3
>>> list(series.related_series)
[RelatedSeries(Series(id=164909, title='Chin Piece'), relation='Spin-Off'), ...
>>> for s in series.related_series:
...     print(s.series.id, s.series.title, s.relation)
164909 Chin Piece Spin-Off
60414 Chopperman Spin-Off
5575 Cross Epoch Spin-Off
```

#### Groups Scanlating

```python3
>>> list(series.groups_scanlating)
[Group(name='/a/nonymous', id=5816), Group(name='A-Team', id=2931), ...
>>> for group in series.groups_scanlating:
...     print(group.name, group.id)
/a/nonymous 5816
A-Team 2931
Akatsuki 2595
Amaitsumi 6617
```

#### Latest Releases

```python3
>>> list(series.latest_releases)
[Release(series_id=33, volume=None, chapter='111', groups=[Group(name='MANGA Plus', id=10280)], elapsed='2 days ago'), ...
>>> for release in series.latest_releases:
...     print(release.series_id, release.volume, release.chapter, release.groups, release.elapsed)
33 None 111 [Group(name='MANGA Plus', id=10280)] 2 days ago
33 None 110 [Group(name='MANGA Plus', id=10280)] 9 days ago
```

#### User Reviews

```python3
>>> list(series.user_reviews)
[UserReview(id=44, reviewer='One Piece', name='Unknown'),
 UserReview(id=60, reviewer='One Piece', name='_AsD'),
 UserReview(id=65, reviewer='One Piece', name='cryptic'),
>>> for review in series.user_reviews:
...     print(review.id, review.reviewer, review.name)
44 One Piece Unknown
60 One Piece _AsD
65 One Piece cryptic
```

#### Genres

```python3
>>> list(series.genres)
['Action', 'Adventure', 'Comedy', 'Drama', 'Fantasy', 'Shounen']
```

#### Categories

```python3
>>> list(series.categories)
[Category('Adapted to Anime', score=256, agree=259, disagree=3),
 Category('Ambitious Goal/s', score=235, agree=238, disagree=3),
 ...]
>>> for category in series.categories:
...     print(category.name, category.score, category.agree, category.disagree)
Adapted to Anime 256 259 3
Ambitious Goal/s 235 238 3
Banding Together 260 267 7
```

#### Recommendations and Category Recommendations

```python3
>>> list(series.recommendations)
[RecommendedSeries(series=Series(id=3793, title='Fairy Tail'), level=78),
RecommendedSeries(series=Series(id=88, title='Berserk'), level=75), ...]
>>> for rec in series.recommendations:
...     print(rec.series.id, rec.series.title, rec.level)
412 Hagane no Renkinjutsushi 81
3793 Fairy Tail 78
88 Berserk 75
>>> list(series.category_recommendations)
[Series(id=135409, title='Zhi Mo (Novel)'), Series(id=56545, title='Aronui Mujeokhamdae'),
 Series(id=172424, title='One Piece Episode A'),...
>>> for rec in series.category_recommendations:
...     print(rec.id, rec.title)
135409 Zhi Mo (Novel)
56545 Aronui Mujeokhamdae
172424 One Piece Episode A
```

#### Authors and Artists

```python3
>>> list(series.authors)
[Author('ODA Eiichiro', id=31)]
>>> for author in series.authors:
...     print(author.name, author.id)
ODA Eiichiro 31
>>> list(series.artists)
[Author('ODA Eiichiro', id=31)]
>>> for artist in series.artists:
...     print(artist.name, artist.id)
ODA Eiichiro 31
```


#### Publishers

```python3
>>> series.original_publisher
Publisher('Shueisha', id=163, note=None)
>>> series.original_publisher.name
'Shueisha'
>>> series.original_publisher.id
163
>>> series.original_publisher.note

>>> list(series.english_publisher)
[Publisher('MANGA Plus', id=1502, note=''),  Publisher('Viz', id=235,
 note='95 Vols - Ongoing; Print & digital | 30, 3-in-1, Omnibus - Ongoing;print')]
>>> for pub in series.english_publisher:
...     print(pub.name, pub.id, pub.note)
MANGA Plus 1502
Viz 235 95 Vols - Ongoing; Print & digital | 30, 3-in-1, Omnibus - Ongoing;print
```

### Activity Stats

```python3
>>> series.activity_stats
ActivityStats(weekly=Rank(position=136, change=20), monthly=Rank(position=117,
change=-26), quarterly=Rank(position=117, change=-2), semiannual=Rank(position=
107, change=-15), yearly=Rank(position=91, change=-26))
```

```python3
print('Weekly Pos #{} ({})'.format(series.activity_stats.weekly.position,
                                   series.activity_stats.weekly.change))
print('Monthly Pos #{} ({})'.format(series.activity_stats.monthly.position,
                                    series.activity_stats.monthly.change))
print('3 Month Pos #{} ({})'.format(series.activity_stats.quarterly.position,
                                    series.activity_stats.quarterly.change))
print('6 Month Pos #{} ({})'.format(series.activity_stats.semiannual.position,
                                    series.activity_stats.semiannual.change))
print('Year Pos #{} ({})'.format(series.activity_stats.yearly.position,
                                 series.activity_stats.yearly.change))
```

Outputs:

```
Weekly Pos #136 (20)
Monthly Pos #117 (-26)
3 Month Pos #117 (-2)
6 Month Pos #107 (-15)
Year Pos #91 (-26)
```

## List Stats

To access the number of users who added the series to one of their lists:

```python3
>>> series.list_stats
ListStats(id=33, reading_total=14252, wish_total=819, unfinished_total=429,
custom_total=800)
>>> series.list_stats.id
33
>>> series.list_stats.reading_total
14252
>>> series.list_stats.wish_total
819
>>> series.list_stats.unfinished_total
429
>>> series.list_stats.custom_total
800
```

These data are parsed from the series webpage. To get the usernames of those
users that added the series to their list and that set that list to public, we
can simply load (and parse) the webpage using `series.list_stats`:

```python3
>>> l = series.list_stats
>>> l.populate()
>>> l.id
33
>>> list(l.read)
[ListEntry(series_id=33, user_id=252343, username='_Alucard_', rating=10.0),
ListEntry(series_id=33, user_id=36041, username='_hikikomori', rating=10.0),
...]
>>> for entry in l.read:
...     print(entry.series_id, entry.user_id, entry.username, entry.rating)
33 252343 _Alucard_ 10.0
33 36041 _hikikomori 10.0
33 112808 07704706 10.0
```
The same pattern goes for the wish, unfinished, and custom lists (but it's
development is still in progress).
