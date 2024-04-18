#!/bin/bash


ls -l /

echo "============== ENVIRONMENT ============="
/usr/bin/env
echo "============== END ENVIRONMENT ============="

if [ -n "$REPO" -a -n "$BRANCH" ]; then
git remote rm proposed || true
git gc --auto
git remote add proposed "$REPO"
GIT_TRACE=1 git fetch proposed
git checkout origin/master
git config --global user.email "you@example.com"
git config --global user.name "Your Name"
git merge --no-ff "proposed/$BRANCH" -m "Merge PR"

echo "Running tests for branch $BRANCH of repo $REPO"
echo "Last commits:"
git --no-pager log -2
fi

sed -i -e "s|#!/usr/bin/env python|#!/usr/bin/env python3|" pagure/hooks/files/hookrunner

pytest-3 -n auto ${TESTCASE:-tests/}
