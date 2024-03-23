#! /usr/bin/env bash

if [[ $# -ne 1 ]]
then
    echo "usage ./pypi.sh <release>"
    exit
fi

# sudo python3 pip install -U twine wheel setuptools
bdir=$(pwd)
wdir=$(mktemp -d)
version=${1}
echo "tempdir: ${wdir}"
echo "version: ${version}"
cd $wdir
# No, this gets the release from github so that what is in this branch is not
# what is pushed to pypi. In essence, multiple runs of this script with same
# version produces same results.
wget https://github.com/al-niessner/pyxb/archive/${version}.tar.gz
tar  --strip-components=1 -xzf ${version}.tar.gz
PYTHONPATH="." python3 <<EOF
import setup
uv = setup.update_version(None)
uv.run()
EOF
python3 setup.py sdist
twine check dist/*
twine upload --verbose dist/*
cd ${bdir}
rm -rf ${wdir}
