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


def test_pass_cmd_used_when_password_not_set():
    import sys

    config = Configuration(['example.com'], 'EPUB', lightweight=True)
    config.add_section('example.com')
    config.set(
        'example.com',
        'pass_cmd',
        '"%s" -c "print(\'s3cr%%t\')" | "%s" -c "import sys; print(sys.stdin.read().strip())"'
        % (sys.executable, sys.executable),
    )

    assert config.hasConfig('password') is True
    assert config.getConfig('password') == 's3cr%t'


def test_password_takes_precedence_over_pass_cmd():
    import sys

    config = Configuration(['example.com'], 'EPUB', lightweight=True)
    config.add_section('example.com')
    config.set('example.com', 'password', 'explicit-pass')
    config.set('example.com', 'pass_cmd', '"%s" -c "print(\'from-cmd\')"' % sys.executable)

    assert config.getConfig('password') == 'explicit-pass'


def test_pass_cmd_failure_falls_back_to_default():
    import sys

    config = Configuration(['example.com'], 'EPUB', lightweight=True)
    config.add_section('example.com')
    config.set('example.com', 'pass_cmd', '"%s" -c "import sys; sys.exit(1)"' % sys.executable)

    assert config.getConfig('password', 'fallback') == 'fallback'


def test_pass_cmd_is_cached(tmp_path):
    import sys

    counter = tmp_path / 'count.txt'
    cmd = (
        '"%s" -c "from pathlib import Path; p = Path(r\'%s\'); '
        'n = int(p.read_text()) + 1 if p.exists() else 1; '
        'p.write_text(str(n)); print(f\'pw-{n}\')"'
    ) % (sys.executable, counter)

    config = Configuration(['example.com'], 'EPUB', lightweight=True)
    config.add_section('example.com')
    config.set('example.com', 'pass_cmd', cmd)

    assert config.getConfig('password') == 'pw-1'
    assert config.getConfig('password') == 'pw-1'
    assert counter.read_text() == '1'


def test_pass_cmd_valid_keyword():
    import fanficfare.adapters as adapters_mod
    from fanficfare import configurable

    configurable.adapters = adapters_mod
    assert 'pass_cmd' in configurable.get_valid_keywords()
