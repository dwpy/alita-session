#!/bin/bash
source ~/.bash_profile
cd ~/work/alita-session
rm -rf dist
python setup.py sdist bdist_wheel
twine upload dist/*
python -V