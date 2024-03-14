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
tar  --strip-components=1 -xzf $bdir/RELEASES/PyXB-CTC-${version}.tar.gz
python3 setup.py sdist
twine check dist/*
twine upload --verbose dist/*
cd ${bdir}
rm -rf ${wdir}
