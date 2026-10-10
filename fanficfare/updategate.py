'''
Shared update-count decision logic for cli.py, calibre-plugin/jobs.py
and calibre-plugin/fff_plugin.py.

Returns a string decision so each caller can keep its own messaging and
error handling:

  'already_contains'  -- existing file and site have the same chapter
                         count and no recheck/edit detection needed.
  'more_than_source'  -- existing file has more chapters than the site and
                         deleted chapters are not being preserved.
  'no_chapters'       -- no recognizable chapters in the existing file.
  'proceed'           -- do the update.
'''


def decide_update(chaptercount, urlchaptercount,
                  metaonly=False,
                  updatealways=False,
                  needs_edit_check=False,
                  preserve_deleted=False,
                  force_update_epub_always=False):
    # Equal counts usually mean nothing to do, but keep going when
    # preserving deleted chapters so equal numbers of deleted and new
    # chapters can be swapped.
    if chaptercount == urlchaptercount and not metaonly and not updatealways \
            and not needs_edit_check and not preserve_deleted:
        return 'already_contains'
    if chaptercount > urlchaptercount and not preserve_deleted \
            and not (updatealways and force_update_epub_always):
        return 'more_than_source'
    if chaptercount == 0:
        return 'no_chapters'
    return 'proceed'