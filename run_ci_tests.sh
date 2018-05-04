set -x

yum install -y python-virtualenv python34 python34-devel \
               gcc python-cryptography python34-cryptography \
               libgit2 python-pygit2 \
               redis swig openssl-devel m2crypto \
               python2-fedmsg python34-fedmsg-core fedmsg \
               python-tox python-pip

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

pip install --upgrade tox
pip install --upgrade --force-reinstall pygments chardet
tox --sitepackages -e 'py{27,34}-flask011-ci' -- -v --with-xcoverage --cover-erase --cover-package=pagure

set +e

tox --sitepackages -e pylint -- -f parseable | tee pylint.out
tox --sitepackages -e lint | tee flake8.out
