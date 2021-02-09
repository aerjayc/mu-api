import pytest
import time
from mangaupdates import Series, exceptions


def test_series_id_not_found():
    sids = [0, -1, 9999999999]
    for sid in sids:
        with pytest.raises(exceptions.InvalidSeriesIDError) as e:
            series = Series(sid)
            series.populate()

def test_series_not_yet_populated():
    series = Series(1)
    with pytest.raises(exceptions.UnpopulatedError) as e:
        series.title

@pytest.fixture(autouse=True, scope='module')
def all_series():
    sids = [33,         # general testing
            118731,     # has a non-int year '2015-2019', which previously caused a ValueError
            108987,     # has a negatively-scored category, which previously caused RegexParseError
           ]
    series = {}
    for i, sid in enumerate(sids):
        series[sid] = Series(sid)
        series[sid].populate()

        if i+1 < len(sids):
            time.sleep(1)

    yield series

class TestSeriesNoExceptions:

    def test_title(self, all_series):
        for s in all_series.values():
            s.title

    def test_description(self, all_series):
        for s in all_series.values():
            s.description

    def test_entries_has_complete_keys(self, all_series):
        keys = {'Description', 'Type', 'Related Series', 'Associated Names',
                'Groups Scanlating', 'Latest Release(s)', 'Status',
                'Completely Scanlated?', 'Anime Start/End Chapter',
                'User Reviews', 'Forum', 'User Rating', 'Last Updated', 'Image',
                'Genre', 'Categories', 'Category Recommendations',
                'Recommendations', 'Author(s)', 'Artist(s)', 'Year',
                'Original Publisher', 'Serialized In (magazine)',
                'Licensed (in English)', 'English Publisher', 'Activity Stats',
                'List Stats'}
        for s in all_series.values():
            assert set(s._entries.keys()) == keys

    def test_series_type(self, all_series):
        for s in all_series.values():
            s.series_type

    def test_related_series(self, all_series):
        for s in all_series.values():
            s.related_series

    def test_associated_names(self, all_series):
        for s in all_series.values():
            s.associated_names

    def test_groups_scanlating(self, all_series):
        for s in all_series.values():
            s.groups_scanlating

    def test_latest_releases(self, all_series):
        for s in all_series.values():
            s.latest_releases

    def test_status(self, all_series):
        for s in all_series.values():
            s.status

    def test_completely_scanlated(self, all_series):
        for s in all_series.values():
            s.completely_scanlated

    def test_anime_chapters(self, all_series):
        for s in all_series.values():
            s.anime_chapters

    def test_user_reviews(self, all_series):
        for s in all_series.values():
            s.user_reviews

    def test_forum(self, all_series):
        for s in all_series.values():
            s.forum

    def test_user_rating(self, all_series):
        for s in all_series.values():
            s.user_rating

    def test_last_updated(self, all_series):
        for s in all_series.values():
            s.last_updated

    def test_image(self, all_series):
        for s in all_series.values():
            s.image

    def test_genres(self, all_series):
        for s in all_series.values():
            s.genres

    def test_categories(self, all_series):
        for s in all_series.values():
            s.categories

    def test_category_recommendations(self, all_series):
        for s in all_series.values():
            s.category_recommendations

    def test_recommendations(self, all_series):
        for s in all_series.values():
            s.recommendations

    def test_authors_is_oda(self, all_series):
        for s in all_series.values():
            s.authors

    def test_artists_is_oda(self, all_series):
        for s in all_series.values():
            s.authors

    def test_original_publisher_is_shueisha(self, all_series):
        for s in all_series.values():
            s.original_publisher

    def test_serialized_in(self, all_series):
        for s in all_series.values():
            s.serialized_in

    def test_licensed_in_english(self, all_series):
        for s in all_series.values():
            s.licensed_in_english

    def test_english_publisher(self, all_series):
        for s in all_series.values():
            s.english_publisher

    def test_activity_stats(self, all_series):
        for s in all_series.values():
            s.activity_stats

    def test_list_stats(self, all_series):
        for s in all_series.values():
            s.list_stats

    def test_json(self, all_series):
        for s in all_series.values():
            s.json()

class TestSeries33:
    sid = 33

    def test_title_is_one_piece(self, all_series):
        assert all_series[self.sid].title == 'One Piece'

    def test_series_type(self, all_series):
        assert all_series[self.sid].series_type == 'Manga'

    def test_authors_is_oda(self, all_series):
        authors = list(all_series[self.sid].authors)
        assert len(authors) == 1
        assert authors[0].id == 31
        assert authors[0].name == 'ODA Eiichiro'

    def test_artists_is_oda(self, all_series):
        artists = list(all_series[self.sid].authors)
        assert len(artists) == 1
        assert artists[0].id == 31
        assert artists[0].name == 'ODA Eiichiro'

    def test_original_publisher_is_shueisha(self, all_series):
        assert all_series[self.sid].original_publisher.id == 163
        assert all_series[self.sid].original_publisher.name == 'Shueisha'
