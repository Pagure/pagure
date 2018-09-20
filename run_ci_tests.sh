set -x

yum install -y python-virtualenv python34 python34-devel \
               gcc python-cryptography python34-cryptography \
               libgit2 libgit2-devel python-pygit2 \
               redis swig openssl-devel m2crypto \
               python2-fedmsg python34-fedmsg-core fedmsg \
               python-tox python-pip python34-pip \
               parallel zeromq-devel python-Cython

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

# Apparently newer requests has strong feeling about idna:
# https://github.com/requests/requests/commit/991e8b76b7a9d21f698b24fa
# and only in py3 we're having a version that is too old (2.1)
pip3 install --upgrade "idna<2.8"
pip install --upgrade tox trollius
pip install --upgrade --force-reinstall chardet
pip3 install "pygit2 <= `rpm -q libgit2 --queryformat='%{version}'`"
tox --sitepackages -e 'py27-flask011-ci' -- --results=results-py2
tox --sitepackages -e 'py34-flask011-ci' -- --results=results-py3

# Let's see if we can print the script this way
sed -i -e "s|less|cat|" ./runtests.py
python ./runtests.py list --show -n 1

