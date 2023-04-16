#!/bin/bash
export TIMESTAMP=$(date +%s) \
&& cd / \
&& git clone -b ${BRANCH} ${REPO} /pagure 2>&1 | tee -a /results/"$TIMESTAMP"_output.log \
&& chmod +x /pagure/dev/containers/runtests_py3.sh \
&& cd /pagure \
&& ln -s /results /pagure/results \
&& python3 setup.py build 2>&1 | tee -a /results/"$TIMESTAMP"_output.log \
&& dev/containers/runtests_py3.sh 2>&1 | tee -a /results/"$TIMESTAMP"_output.log