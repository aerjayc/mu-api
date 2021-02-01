import pytest
import time
from mangaupdates import Series


@pytest.fixture(autouse=True, scope='module')
def series():
    sids = [33]
    all_series = {}
    for sid in sids:
        all_series[sid] = Series(sid)
        all_series[sid].populate()
        time.sleep(2)

    yield all_series

class TestSeriesNoExceptions:

    def test_title(self, series):
        for s in series.values():
            s.title

    def test_description(self, series):
        for s in series.values():
            s.description

    def test_entries_has_complete_keys(self, series):
        keys = {'Description', 'Type', 'Related Series', 'Associated Names',
                'Groups Scanlating', 'Latest Release(s)', 'Status',
                'Completely Scanlated?', 'Anime Start/End Chapter',
                'User Reviews', 'Forum', 'User Rating', 'Last Updated', 'Image',
                'Genre', 'Categories', 'Category Recommendations',
                'Recommendations', 'Author(s)', 'Artist(s)', 'Year',
                'Original Publisher', 'Serialized In (magazine)',
                'Licensed (in English)', 'English Publisher', 'Activity Stats',
                'List Stats'}
        for s in series.values():
            assert set(s._entries.keys()) == keys

    def test_series_type(self, series):
        for s in series.values():
            s.series_type

    def test_related_series(self, series):
        for s in series.values():
            s.related_series

    def test_associated_names(self, series):
        for s in series.values():
            s.associated_names

    def test_groups_scanlating(self, series):
        for s in series.values():
            s.groups_scanlating

    def test_latest_releases(self, series):
        for s in series.values():
            s.latest_releases

    def test_status(self, series):
        for s in series.values():
            s.status

    def test_completely_scanlated(self, series):
        for s in series.values():
            s.completely_scanlated

    def test_anime_chapters(self, series):
        for s in series.values():
            s.anime_chapters

    def test_user_reviews(self, series):
        for s in series.values():
            s.user_reviews

    def test_forum(self, series):
        for s in series.values():
            s.forum

    def test_user_rating(self, series):
        for s in series.values():
            s.user_rating

    def test_last_updated(self, series):
        for s in series.values():
            s.last_updated

    def test_image(self, series):
        for s in series.values():
            s.image

    def test_genres(self, series):
        for s in series.values():
            s.genres

    def test_categories(self, series):
        for s in series.values():
            s.categories

    def test_category_recommendations(self, series):
        for s in series.values():
            s.category_recommendations

    def test_recommendations(self, series):
        for s in series.values():
            s.recommendations

    def test_authors_is_oda(self, series):
        for s in series.values():
            s.authors

    def test_artists_is_oda(self, series):
        for s in series.values():
            s.authors

    def test_original_publisher_is_shueisha(self, series):
        for s in series.values():
            s.original_publisher

    def test_serialized_in(self, series):
        for s in series.values():
            s.serialized_in

    def test_licensed_in_english(self, series):
        for s in series.values():
            s.licensed_in_english

    def test_english_publisher(self, series):
        for s in series.values():
            s.english_publisher

    def test_activity_stats(self, series):
        for s in series.values():
            s.activity_stats

    def test_list_stats(self, series):
        for s in series.values():
            s.list_stats

class TestSeries33:
    sid = 33

    def test_title_is_one_piece(self, series):
        assert series[self.sid].title == 'One Piece'

    def test_series_type(self, series):
        assert series[self.sid].series_type == 'Manga'

    def test_authors_is_oda(self, series):
        authors = list(series[self.sid].authors)
        assert len(authors) == 1
        assert authors[0].id == 31
        assert authors[0].name == 'ODA Eiichiro'

    def test_artists_is_oda(self, series):
        artists = list(series[self.sid].authors)
        assert len(artists) == 1
        assert artists[0].id == 31
        assert artists[0].name == 'ODA Eiichiro'

    def test_original_publisher_is_shueisha(self, series):
        assert series[self.sid].original_publisher.id == 163
        assert series[self.sid].original_publisher.name == 'Shueisha'
