import pytest
import time
from mangaupdates import ListStats, exceptions


def test_invalid_list_name():
    list_names = ['asdf']
    for name in list_names:
        with pytest.raises(exceptions.InvalidListNameError) as e:
            l = ListStats(1)
            l.populate(list_names=list_names)

@pytest.fixture(autouse=True, scope='module', params=[33])
def populated_liststats(request):
    l = ListStats(request.param)
    l.populate()
    yield l

class TestListStatsNormal:

    def test_reading_list(self, populated_liststats):
        list(populated_liststats.reading)

    def test_wish_list(self, populated_liststats):
        list(populated_liststats.wish)

    def test_unfinished_list(self, populated_liststats):
        list(populated_liststats.unfinished)

    def test_complete_list(self, populated_liststats):
        list(populated_liststats.complete)

    def test_on_hold_list(self, populated_liststats):
        list(populated_liststats.on_hold)

    def test_json(self, populated_liststats):
        populated_liststats.json()

@pytest.fixture(autouse=True, scope='module')
def unpopulated_liststats():
    return ListStats(1)

class TestListStatsUnpopulated:

    def test_reading_list(self, unpopulated_liststats):
        with pytest.raises(exceptions.UnpopulatedError) as e:
            list(unpopulated_liststats.reading)

    def test_wish_list(self, unpopulated_liststats):
        with pytest.raises(exceptions.UnpopulatedError) as e:
            list(unpopulated_liststats.wish)

    def test_unfinished_list(self, unpopulated_liststats):
        with pytest.raises(exceptions.UnpopulatedError) as e:
            list(unpopulated_liststats.unfinished)

    def test_complete_list(self, unpopulated_liststats):
        with pytest.raises(exceptions.UnpopulatedError) as e:
            list(unpopulated_liststats.complete)

    def test_on_hold_list(self, unpopulated_liststats):
        with pytest.raises(exceptions.UnpopulatedError) as e:
            list(unpopulated_liststats.on_hold)

    def test_json(self, unpopulated_liststats):
        with pytest.raises(exceptions.UnpopulatedError) as e:
            unpopulated_liststats.json()

def test_populate_persistence():
    l = ListStats(1)
    l.populate()
    l.populate(list_names=['read'])

    # test if still accessible
    list(l.reading)
    list(l.wish)
    list(l.complete)
    list(l.on_hold)
