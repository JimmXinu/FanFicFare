# -*- coding: utf-8 -*-
"""Regression tests for RoyalRoadAdapter.performLogin.

Covers the late-2026 Royal Road login breakage (upstream #1444):

* the login GET can return an Anubis/Cloudflare bot-wall page instead
  of the login form -- the old code crashed with
  ``TypeError: 'NoneType' object is not subscriptable`` on the missing
  ``__RequestVerificationToken`` input;
* with a shared browser (Camoufox) session the login page can be an
  already-logged-in page with no login form at all;
* the old failure test, ``"Sign in" in <POST response>``, falsely
  reported "RoyalRoad requires Email not name" for successful logins
  whose landing page merely contains those words.

No network: the adapter's get/post are stubbed with canned pages.
"""

import pytest
from bs4 import BeautifulSoup

from fanficfare import exceptions
from fanficfare.adapters.adapter_royalroadcom import RoyalRoadAdapter


LOGIN_FORM = """
<html><head><title>Sign In | Royal Road</title></head><body>
<form method="post" action="/account/login">
  <input type="hidden" name="__RequestVerificationToken" value="TOK">
  <input type="hidden" name="ReturnUrl" value="/home">
  <input name="Email" type="email">
  <input name="Password" type="password">
  <input type="checkbox" name="RememberMe" value="true">
  <button type="submit">Sign In</button>
</form>
</body></html>
"""

# a successful login landing page that happens to contain "Sign in"
HOME_PAGE = """
<html><body>Welcome back
<a href="/user/profile/123">Profile</a> Sign out
<script>var s = 'Sign in to sync your library';</script>
</body></html>
"""

ANUBIS_PAGE = """
<html><head><title>Making sure you're not a bot!</title></head>
<body><script id="anubis_challenge">{}</script></body></html>
"""

ALREADY_LOGGED_IN_PAGE = """
<html><body>
<a href="/user/profile/123">My Profile</a>
<a href="/account/logout">Sign out</a>
</body></html>
"""


def make_adapter(get_page, post_page, password='secret'):
    adapter = RoyalRoadAdapter.__new__(RoyalRoadAdapter)
    adapter.username = 'NoneGiven'
    adapter.password = ''
    adapter.url = 'https://www.royalroad.com/fiction/84749'
    adapter._get_page = get_page
    adapter._post_page = post_page
    adapter.posted = None
    config = {'username': 'reader@example.com', 'password': password}

    adapter.getConfig = lambda key, default='': config.get(key, default)
    adapter.get_request = lambda url: adapter._get_page
    def post_request(url, params):
        adapter.posted = (url, params)
        return adapter._post_page
    adapter.post_request = post_request
    adapter.make_soup = lambda data: BeautifulSoup(data or '', 'html.parser')
    return adapter


def test_bot_wall_on_get_is_failed_to_login_not_a_crash():
    adapter = make_adapter(ANUBIS_PAGE, '')
    with pytest.raises(exceptions.FailedToLogin) as excinfo:
        adapter.performLogin()
    assert 'bot-check' in str(excinfo.value)
    assert adapter.posted is None


def test_already_logged_in_skips_post():
    adapter = make_adapter(ALREADY_LOGGED_IN_PAGE, '')
    assert adapter.performLogin() is True
    assert adapter.posted is None


def test_successful_login_with_sign_in_text_on_landing_page():
    adapter = make_adapter(LOGIN_FORM, HOME_PAGE)
    assert adapter.performLogin() is True
    url, params = adapter.posted
    assert url == 'https://www.royalroad.com/account/login'
    # form-driven: hidden fields copied as sent, fields filled by
    # their real names (Password, not a hardcoded 'password')
    assert params['__RequestVerificationToken'] == 'TOK'
    assert params['ReturnUrl'] == '/home'
    assert params['Email'] == 'reader@example.com'
    assert params['Password'] == 'secret'


def test_login_form_returned_after_post_is_a_failure():
    adapter = make_adapter(LOGIN_FORM, LOGIN_FORM)
    with pytest.raises(exceptions.FailedToLogin) as excinfo:
        adapter.performLogin()
    assert 'login form again' in str(excinfo.value)


def test_bot_wall_on_post_is_failed_to_login():
    adapter = make_adapter(LOGIN_FORM, ANUBIS_PAGE)
    with pytest.raises(exceptions.FailedToLogin) as excinfo:
        adapter.performLogin()
    assert 'bot-check' in str(excinfo.value)


def test_no_password_configured_skips_login():
    adapter = make_adapter(LOGIN_FORM, '', password='')
    assert adapter.performLogin() is None
    assert adapter.posted is None
