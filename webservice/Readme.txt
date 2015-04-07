Note that the defaults.ini and example.ini files for CLI and
webservice are now separate and will need to be kept synchronized.

Before uploading the webservice to Google AppEngine, the files here,
along with ../fff_internals and the contents of
../included_dependencies should be copied to a 'build' (or other)
directory.

rm -rf build
mkdir build

cp -R * build
cp -R ../fff_internals ../included_dependencies/* build

cd build

.../appcfg.py update .
