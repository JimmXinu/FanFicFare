Before uploading the webservice to Google AppEngine, the files here,
along with ../fanficfare and the contents of
../included_dependencies should be copied to a 'build' (or other)
directory.

rm -rf build
mkdir build

cp -R * build
cp -R ../fanficfare ../included_dependencies/* build

cd build

.../appcfg.py update .
