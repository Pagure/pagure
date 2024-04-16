#!/bin/bash
cd / \
&& GIT_TRACE=1 git clone -b ${BRANCH} ${REPO} /pagure \
&& chmod +x /pagure/dev/containers/tox_py3.sh \
&& ln -s /tox /pagure/.tox \
&& cd /pagure \
&& ln -s /results /pagure/results \
&& sed -i -e 's|"alembic-3"|"alembic"|' /pagure/tests/test_alembic.py \
&& dev/containers/tox_py3.sh
