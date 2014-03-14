#!/bin/bash

[ -d forks/pingou ] || mkdir -p forks/pingou

pushd forks/pingou
  for pkg in `pkgdb-cli list --user=pingou --nameonly`;
  do
      git clone --bare git://pkgs.fedoraproject.org/$pkg;
  done;
popd

[ -d repos ] || mkdir -p repos

pushd repos
  for pkg in `pkgdb-cli list --user=pingou --nameonly`;
  do
      git clone --bare git://pkgs.fedoraproject.org/$pkg;
  done;
popd

