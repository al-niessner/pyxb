#! /usr/bin/env bash

# sudo python3 pip install -U twine wheel setuptools
bdir=$(pwd)
wdir=$(mktemp -d)
version=$(python <<EOF
import setup
print(setup.version)
EOF
          )
echo "tempdir: ${wdir}"
echo "version: ${version}"
cd $wdir
# No, this gets the release from github so that what is in this branch is not
# what is pushed to pypi. In essence, multiple runs of this script with same
# version produces same results.
wget https://github.com/al-niessner/pyxb/archive/${version}.tar.gz
tar  --strip-components=1 -xzf ${version}.tar.gz
python3 setup.py sdist
twine check dist/*
twine upload --verbose dist/*
cd ${bdir}
rm -rf ${wdir}
