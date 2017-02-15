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
echo "Last commit:"
git log -1
fi


DATE=`date +%Y%m%d`
HASH=`sha1sum requirements.txt | awk '{print $1}'`

if [ ! -d pagureenv-$DATE-$HASH ];
then
    rm -rf pagureenv*;
    virtualenv pagureenv-$DATE-$HASH --system-site-packages
    source pagureenv-$DATE-$HASH/bin/activate

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

    pip uninstall cffi -y
else
    source pagureenv-$DATE-$HASH/bin/activate
fi
trap deactivate SIGINT SIGTERM EXIT


# Reload where the nosetests app is (within the venv)
hash -r


python setup.py build

PYTHONPATH=pagure ./nosetests -v --with-xcoverage --cover-erase --cover-package=pagure

if [ "$?" = "0" ]; then

    PYTHONPATH=pagure pylint -f parseable pagure | tee pylint.out
    pep8 pagure/*.py pagure/*/*.py | tee pep8.out

fi
