#!/bin/bash

PAGURE_CONFIG=`pwd`/tests/test_config \
PYTHONPATH=pagure \
./nosetests --with-html --with-coverage --cover-erase --cover-package=pagure --with-pagureperf $*
