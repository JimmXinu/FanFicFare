

"""A setuptools based setup module.

See:
https://packaging.python.org/guides/distributing-packages-using-setuptools/
https://github.com/pypa/sampleproject
"""

# Always prefer setuptools over distutils
from setuptools import setup
# To use a consistent encoding
import codecs

package_name="FanFicFare"

import sys
if sys.version_info < (2,7):
    sys.exit(package_name+' requires Python 2.7 or newer.')

# Get the long description from the relevant file
with codecs.open('DESCRIPTION.rst', encoding='utf-8') as f:
    long_description = f.read()

setup(
    name=package_name,

    # Versions should comply with PEP440.
    version="4.19.8",

    description='A tool for downloading fanfiction to eBook formats',
    long_description=long_description,

    # The project's main homepage.
    url='https://github.com/JimmXinu/FanFicFare',

    # Author details
    author='Jim Miller',
    author_email='retiefjimm@gmail.com',

    # Choose your license
    license='Apache License',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 5 - Production/Stable',

        'Environment :: Console',

        # Indicate who your project is intended for
        'Intended Audience :: End Users/Desktop',
        'Topic :: Internet :: WWW/HTTP',

        # Pick your license as you wish (should match "license" above)
        'License :: OSI Approved :: Apache Software License',

        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        # Earlier py3 version may work, but I've not tested them.
        'Programming Language :: Python :: 3.7',
    ],

    # What does your project relate to?
    keywords='fanfiction download ebook epub html',

    # You can just specify the packages manually here if your project is
    # simple. Or you can use find_packages().
    # packages=find_packages(exclude=['contrib', 'docs', 'tests*']),
    packages=['fanficfare',
              'fanficfare.adapters', 'fanficfare.fetchers', 'fanficfare.writers',
              'fanficfare.browsercache','fanficfare.browsercache.chromagnon'],

    # for package_data
    package_dir={'fanficfare': 'fanficfare'},

    # List run-time dependencies here.  These will be installed by pip when
    # your project is installed. For an analysis of "install_requires" vs pip's
    # requirements files see:
    # https://packaging.python.org/en/latest/requirements.html
    install_requires=['beautifulsoup4',
                      'chardet',
                      'html5lib',
                      'html2text',
                      'cloudscraper', # includes requests and deps.
                      'urllib3 >= 1.26.2', # for Retry(other=)
                      'requests >= 2.25.1', # otherwise version issues with urllib3
                      'requests-file',
                      'brotli',
                      'pywin32; platform_system=="Windows"'],
    # html5lib requires 'six', FFF includes it's own copy as fanficfare.six

    # List additional groups of dependencies here (e.g. development
    # dependencies). You can install these using the following syntax,
    # for example:
    # $ pip install -e .[dev,test]
    extras_require={
        'image_processing': ['Pillow'],
        # 'dev': ['check-manifest'],
        # 'test': ['coverage'],
    },

    # If there are data files included in your packages that need to be
    # installed, specify them here.  If using Python 2.6 or less, then these
    # have to be included in MANIFEST.in as well.
    package_data={
        'fanficfare': ['defaults.ini', 'example.ini'],
    },

    # Although 'package_data' is the preferred approach, in some case you may
    # need to place data files outside of your packages. See:
    # http://docs.python.org/3.4/distutils/setupscript.html#installing-additional-files # noqa
    # In this case, 'data_file' will be installed into '<sys.prefix>/my_data'
    # data_files=[('my_data', ['data/data_file'])],

    # To provide executable scripts, use entry points in preference to the
    # "scripts" keyword. Entry points provide cross-platform support and allow
    # pip to create the appropriate form of executable for the target platform.
    entry_points={
        'console_scripts': [
            'fanficfare=fanficfare.cli:main',
        ],
    },
)
