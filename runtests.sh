#!/bin/bash

PAGURE_CONFIG=../tests/config PYTHONPATH=pagure ./nosetests --with-coverage --cover-erase --cover-package=pagure $*
