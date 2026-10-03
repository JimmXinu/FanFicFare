# -*- coding: utf-8 -*-
"""decide_update() gate for the three update paths (cli.py, jobs.py,
fff_plugin.py).

The critical case: when update_preserve_deleted_chapters is enabled and a
site deletes N chapters while adding N new ones, chaptercount ==
urlchaptercount.  The gate must NOT short-circuit to 'already_contains';
it must proceed so deleted chapters can be preserved and the new ones
downloaded.
"""
import pytest

from fanficfare.updategate import decide_update


@pytest.mark.parametrize('chaptercount,urlchaptercount,kwargs,expected', [
    # Plain equal counts -> nothing to do.
    (20, 20, {}, 'already_contains'),
    # Equal swapped-out/added chapters while preserving deleted ones -> update.
    (20, 20, {'preserve_deleted': True}, 'proceed'),
    # Equal counts with edit-detection needing a re-download -> update.
    (20, 20, {'needs_edit_check': True}, 'proceed'),
    # Equal counts forced via updatealways/metaonly -> update.
    (20, 20, {'updatealways': True}, 'proceed'),
    (20, 20, {'metaonly': True}, 'proceed'),
    (20, 20, {'updatealways': True, 'force_update_epub_always': True}, 'proceed'),
    # Existing has more than the site.
    (20, 10, {}, 'more_than_source'),
    # ...but fine when preserving deleted chapters.
    (20, 10, {'preserve_deleted': True}, 'proceed'),
    # ...or when updatealways with force_update_epub_always.
    (20, 10, {'updatealways': True},
     'more_than_source'),
    (20, 10, {'updatealways': True, 'force_update_epub_always': True},
     'proceed'),
    # No recognizable chapters in the existing epub.
    (0, 10, {}, 'no_chapters'),
    # Both zero -> equal branch wins (matches inline gate order).
    (0, 0, {}, 'already_contains'),
    # Site has more than the existing epub -> update.
    (10, 20, {'preserve_deleted': True}, 'proceed'),
    (10, 20, {}, 'proceed'),
])
def test_decide_update(chaptercount, urlchaptercount, kwargs, expected):
    assert decide_update(chaptercount, urlchaptercount, **kwargs) == expected