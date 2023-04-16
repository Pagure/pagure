#!/bin/bash
cd / \
&& GIT_TRACE=1 GIT_CURL_VERBOSE=1 git clone -b ${BRANCH} ${REPO} /pagure \
&& chmod +x /pagure/dev/containers/runtests_py3.sh \
&& cd /pagure \
&& ln -s /results /pagure/results \
&& python3 setup.py build \
&& dev/containers/runtests_py3.sh