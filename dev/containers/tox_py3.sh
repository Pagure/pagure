#!/bin/bash

# Print all executed commands to the terminal
set -x

# Fail script if any commands returns an error
set -e

ls -l /

echo "============== ENVIRONMENT ============="
/usr/bin/env
echo "============== END ENVIRONMENT ============="

if [ -n "$REPO" -a -n "$BRANCH" ]; then
  git remote rm proposed || true
  git gc --auto

  # Merge into upstream/master to identify if feature branch
  # is out-of-sync or has merge conflicts early in testing
  git remote add proposed "$REPO"
  GIT_TRACE=1 git fetch proposed
  git remote add upstream https://pagure.io/pagure.git
  GIT_TRACE=1 git fetch upstream
  git checkout upstream/master
  git config --global user.email "you@example.com"
  git config --global user.name "Your Name"
  git merge --no-ff "proposed/$BRANCH" -m "Merge PR"

  echo "Running tests for branch $BRANCH of repo $REPO"
  echo "Last commits:"
  git --no-pager log -2
fi

export LANG="en_US.UTF-8"

echo TOXENV: "${TOXENV}"
if [ -z "${TOXENV}" ]; then
  tox -v -e "${TOXENV}" -- ${TESTCASE:-tests/}
else
  tox -v -- ${TESTCASE:-tests/}
fi
