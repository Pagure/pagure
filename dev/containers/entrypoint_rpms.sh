#!/bin/bash
cd / \
&& git clone -b ${BRANCH} ${REPO} /pagure \
&& chmod +x /pagure/dev/containers/runtests_py3.sh \
&& ln -s /results /pagure/results \
&& cd /pagure \
&& python3 setup.py build \
&& dev/containers/runtests_py3.sh