"""Browser ownership tests that do not require Calibre or Camoufox installed."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from fanficfare import cli
from fanficfare.fetchers import camoufoxbrowser
from fanficfare.fetchers.camoufoxbrowser_cli import Browser


@pytest.mark.parametrize('failure', [None, RuntimeError, KeyboardInterrupt])
def test_cli_closes_its_browser_on_completion_or_failure(monkeypatch, failure):
    browser = Browser.__new__(Browser)
    browser.close = Mock()
    instance = SimpleNamespace(_initialized=True, browser=browser)

    def dispatch(*args):
        monkeypatch.setattr(camoufoxbrowser.CamoufoxBrowserSingleton, '_instance', instance)
        if failure:
            raise failure()

    monkeypatch.setattr(cli, 'dispatch', dispatch)
    monkeypatch.setattr(camoufoxbrowser.CamoufoxBrowserSingleton, '_instance', None)
    if failure:
        with pytest.raises(failure):
            cli.main(['https://www.royalroad.com/fiction/203028'])
    else:
        cli.main(['https://www.royalroad.com/fiction/203028'])
    browser.close.assert_called_once_with()
    assert camoufoxbrowser.CamoufoxBrowserSingleton._instance is None


def test_cli_leaves_calibre_browser_running(monkeypatch):
    browser = Mock()
    instance = SimpleNamespace(_initialized=True, browser=browser)
    monkeypatch.setattr(camoufoxbrowser.CamoufoxBrowserSingleton, '_instance', instance)
    with camoufoxbrowser.cli_browser_session():
        pass
    browser.close.assert_not_called()
    assert camoufoxbrowser.CamoufoxBrowserSingleton._instance is instance


def test_startup_failure_is_not_masked_by_cleanup(monkeypatch):
    # __new__ can have created the singleton before browser setup fails.
    instance = SimpleNamespace(_initialized=False)
    monkeypatch.setattr(camoufoxbrowser.CamoufoxBrowserSingleton, '_instance', instance)
    with pytest.raises(RuntimeError, match='startup failed'):
        with camoufoxbrowser.cli_browser_session():
            raise RuntimeError('startup failed')
