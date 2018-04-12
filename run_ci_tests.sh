yum install -y python-virtualenv \
               gcc python-cryptography \
               libgit2 python-pygit2 \
               redis swig openssl-devel m2crypto \
               python2-fedmsg fedmsg \
               python2-pylint python-pep8

sysctl -w fs.file-max=2048

set -e

echo "============== ENVIRONMENT ============="
/usr/bin/env
echo "============== END ENVIRONMENT ============="

if [ -n "$REPO" -a -n "$BRANCH" ]; then
git remote rm proposed || true
git gc --auto
git remote add proposed "$REPO"
git fetch proposed
git checkout origin/master
git config --global user.email "you@example.com"
git config --global user.name "Your Name"
git merge --no-ff "proposed/$BRANCH" -m "Merge PR"

echo "Running tests for branch $BRANCH of repo $REPO"
echo "Last commits:"
git log -2
fi


virtualenv pagureenv --system-site-packages
source pagureenv/bin/activate

pip install pip --upgrade
# Needed within the venv
pip install nose --upgrade
pip install --upgrade --force-reinstall python-fedora 'setuptools>=17.1' pygments
pip install -r tests_requirements.txt
pip install -r requirements-ev.txt  # We have one test on the SSE server
sed -i -e 's|pygit2 >= 0.20.1||' requirements.txt
pip install -r requirements.txt
pip install psycopg2
pip install python-openid python-openid-teams python-openid-cla

#    pip uninstall cffi -y
trap deactivate SIGINT SIGTERM EXIT


# Reload where the nosetests app is (within the venv)
hash -r


python setup.py build

PAGURE_CONFIG=`pwd`/tests/test_config \
PYTHONPATH=pagure \
./nosetests -v --with-xcoverage --cover-erase --cover-package=pagure

set +e

PYTHONPATH=pagure pylint-2 -f parseable pagure | tee pylint.out
pep8 pagure/*.py pagure/*/*.py | tee pep8.out

