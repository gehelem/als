from als import als
from als.datastore import VERSION


def test_temp():
    assert VERSION is not None


def test_coverage():
    assert als.MainWindow.get_ip() is not None
