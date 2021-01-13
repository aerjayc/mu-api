import pytest
from mangaupdates import public


@pytest.fixture(autouse=True, scope='class')
def setup_filled_series(request):
    # id=33 (One Piece)
    series = public.Series(33)
    series.populate()
    request.cls.filled_series = series

#def test_populate(series_id):
#    """ Test if successfully able to execute GET request """
#
#    series = public.Series(33)
#    series.populate()
#    assert series.response.status_code == 200

class TestFilledSeries:

    def test_title(self):
        assert self.filled_series.title == 'One Piece'

    def test_description(self):
        self.filled_series.description
    
    def test_entries_has_complete_keys(self):
        keys = {'Description', 'Type', 'Related Series', 'Associated Names',
                'Groups Scanlating', 'Latest Release(s)', 'Status',
                'Completely Scanlated?', 'Anime Start/End Chapter',
                'User Reviews', 'Forum', 'User Rating', 'Last Updated', 'Image',
                'Genre', 'Categories', 'Category Recommendations',
                'Recommendations', 'Author(s)', 'Artist(s)', 'Year',
                'Original Publisher', 'Serialized In (magazine)',
                'Licensed (in English)', 'English Publisher', 'Activity Stats',
                'List Stats'}
        assert set(self.filled_series.entries.keys()) == keys
    
    def test_series_type(self):
        assert self.filled_series.series_type == 'Manga'
    
    def test_related_series(self):
        self.filled_series.related_series
    
    def test_associated_names(self):
        self.filled_series.associated_names
    
    def test_groups_scanlating(self):
        self.filled_series.groups_scanlating
    
    def test_latest_releases(self):
        self.filled_series.latest_releases
    
    def test_status(self):
        self.filled_series.status
    
    def test_completely_scanlated(self):
        self.filled_series.completely_scanlated
    
    def test_anime_chapters(self):
        self.filled_series.anime_chapters
    
    def test_user_reviews(self):
        self.filled_series.user_reviews
    
    def test_forum(self):
        self.filled_series.forum
    
    def test_user_rating(self):
        self.filled_series.user_rating
    
    def test_last_updated(self):
        self.filled_series.last_updated
    
    def test_image(self):
        self.filled_series.image
    
    def test_genre(self):
        self.filled_series.genre
    
    def test_categories(self):
        self.filled_series
    
    def test_category_recommendations(self):
        self.filled_series.category_recommendations
    
    def test_recommendations(self):
        self.filled_series.recommendations
    
    def test_authors_is_oda(self):
        assert self.filled_series.authors == [(31, 'ODA Eiichiro')]
    
    def test_artists_is_oda(self):
        assert self.filled_series.artists == [(31, 'ODA Eiichiro')]
    
    def test_original_publisher_is_shueisha(self):
        assert self.filled_series.original_publisher == (163, 'Shueisha')
    
    def test_serialized_in(self):
        self.filled_series.serialized_in
    
    def test_licensed_in_english(self):
        assert self.filled_series.licensed_in_english
    
    def test_english_publisher(self):
        self.filled_series.english_publisher
    
    def test_activity_stats(self):
        self.filled_series.activity_stats
    
    def test_list_stats(self):
        self.filled_series.list_stats