#!/bin/bash
cd / \
&& git clone -b ${BRANCH} ${REPO} /pagure \
&& cp /tox_py3.sh /pagure/dev/containers/tox_py3.sh \
&& chmod +x /pagure/dev/containers/tox_py3.sh \
&& ln -s /tox /pagure/.tox \
&& cd /pagure \
&& ln -s /results /pagure/results \
&& sed -i -e 's|"alembic-3"|"alembic"|' /pagure/tests/test_alembic.py \
&& dev/containers/tox_py3.sh
