#!/bin/bash

PYTHONPATH=progit ./nosetests --with-coverage --cover-erase --cover-package=progit $*
