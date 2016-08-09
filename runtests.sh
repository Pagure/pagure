#!/bin/bash

PYTHONPATH=pagure ./nosetests --with-coverage --cover-erase --cover-package=pagure $*
