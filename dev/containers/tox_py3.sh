#!/bin/bash


ls -l /

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

tox -v --sitepackages -e 'py34-flask100-ci' -- --results=results
