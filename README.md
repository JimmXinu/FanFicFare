[FanFicFare](https://github.com/JimmXinu/FanFicFare)
==========

FanFicFare makes reading stories from various websites much easier by helping
you download them to EBook files.

FanFicFare was previously known as FanFictionDownLoader (AKA
FFDL, AKA fanficdownloader).

Main features:

- Download FanFiction stories from over [100 different sites](https://github.com/JimmXinu/FanFicFare/wiki/SupportedSites). into ebooks.

- Update previously downloaded EPUB format ebooks, downloading only new chapters.

- Get Story URLs from Web Pages.

- Support for downloading images in the story text. (EPUB and HTML
  only -- download EPUB and convert to AZW3 for Kindle) More details on
  configuring images in stories and cover images can be found in the
  [FAQs] or [this post in the old FFDL thread].

- Support for cover image. (EPUB only)

- Optionally keep an Update Log of past updates (EPUB only).

There's additional info in the project [wiki] pages.

There's also a [FanFicFare maillist] for discussion and announcements and a [discussion thread] for the Calibre plugin.

Getting FanFicFare
==================

### Official Releases

This program is available as:

- A Calibre plugin from within Calibre or directly from the plugin [discussion thread], or;
- A Command Line Interface (CLI) [Python
  package](https://pypi.python.org/pypi/FanFicFare) that you can
  install with:
```
pip install FanFicFare
```
- _As of late November 2019, the web service version is shutdown.  See the [Wiki Home](https://github.com/JimmXinu/FanFicFare/wiki#web-service-version) page for details._

### Test Versions

FanFicFare is released roughly every month, but new test versions are posted more frequently as changes are made.

Test versions are available at:

- The [test plugin] is posted at MobileRead.
- The test version of CLI for pip install is uploaded to the testpypi repository and can be installed with:

> `pip install --extra-index-url https://testpypi.python.org/pypi --upgrade FanFicFare`


### Other Releases

Other versions may be available depending on your OS.  I(JimmXinu) don't directly support these:

- **Arch Linux**: The latest CLI release can be obtained from the [fanficfare](https://aur.archlinux.org/packages/fanficfare) AUR package. It will install the calibre plugin, if calibre is installed.


[this post in the old FFDL thread]: https://www.mobileread.com/forums/showthread.php?p=1982785#post1982785
[FAQs]: https://github.com/JimmXinu/FanFicFare/wiki/FAQs#can-fanficfare-download-a-story-containing-images
[FanFicFare maillist]: https://groups.google.com/group/fanfic-downloader
[wiki]: https://github.com/JimmXinu/FanFicFare/wiki
[discussion thread]: https://www.mobileread.com/forums/showthread.php?t=259221
[test plugin]: https://www.mobileread.com/forums/showthread.php?p=3084025&postcount=2
