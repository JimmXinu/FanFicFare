import pytest

from fanficfare.configurable import Configuration


@pytest.mark.parametrize('first_default', ['first', '', None, []])
def test_missing_option_respects_each_callers_default(first_default):
    config = Configuration(['example.com'], 'EPUB', lightweight=True)

    assert config.getConfig('missing_option', first_default) == first_default
    assert config.getConfig('missing_option', 'second') == 'second'


def test_add_to_option_is_a_configured_value_independent_of_default():
    config = Configuration(['example.com'], 'EPUB', lightweight=True)
    config.add_section('example.com')
    config.set('example.com', 'add_to_missing_option', '-suffix')

    assert config.getConfig('missing_option', 'first') == '-suffix'
    assert config.getConfig('missing_option', 'second') == '-suffix'


def test_interpolation_is_disabled():
    from io import StringIO

    config = Configuration(['example.com'], 'EPUB', lightweight=True)
    config.read_file(StringIO(
        "[example.com]\n"
        "password: p%zss%word%%100\n"
        "datePublished_format: %Y-%m-%d\n"
    ))

    assert config.getConfig('password') == 'p%zss%word%%100'
    assert config.getConfig('datePublished_format') == '%Y-%m-%d'
