#!/bin/bash
cd / \
&& git clone -b ${BRANCH} ${REPO} /pagure \
&& chmod +x /pagure/dev/containers/runtests_py3.sh \
&& cd /pagure \
&& ln -s /results /pagure/results \
&& python3 setup.py build \
&& dev/containers/runtests_py3.sh