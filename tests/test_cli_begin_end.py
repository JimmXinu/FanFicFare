"""Offline tests for --begin/--end chapter-range validation in fanficfare.cli.

Non-numeric --begin/--end values used to slip through validateOptions and
blow up later with a bare ValueError traceback from int() conversion in
BaseSiteAdapter.setChaptersRange. They are now rejected up front with a
clean argparse usage error (exit code 2).
"""
import pytest

from fanficfare import cli


def make_options(begin=None, end=None):
    argv = ['https://test1.com/story?sid=5']
    if begin is not None:
        argv.append('--begin=%s' % begin)
    if end is not None:
        argv.append('--end=%s' % end)
    parser = cli.mkParser(False)
    options, args = parser.parse_args(argv)
    cli.expandOptions(options)
    return parser, options, args


def test_begin_must_be_numeric():
    parser, options, args = make_options(begin='abc')
    with pytest.raises(SystemExit) as excinfo:
        cli.validateOptions(parser, options, args)
    assert excinfo.value.code == 2


def test_end_must_be_numeric():
    parser, options, args = make_options(end='1.5')
    with pytest.raises(SystemExit) as excinfo:
        cli.validateOptions(parser, options, args)
    assert excinfo.value.code == 2


def test_numeric_begin_end_pass_validation():
    parser, options, args = make_options(begin='2', end='4')
    cli.validateOptions(parser, options, args)
