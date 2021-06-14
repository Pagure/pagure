#! /bin/bash

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
ROOT_DIR="$( dirname "$SCRIPT_DIR" )"

cd "$ROOT_DIR"

echo "Pagure Env: $ROOT_DIR/lcl"
mkdir -p lcl/{repos,remotes,attachments,releases}

docker image build -f dev/containers/base -t pagure-base .

docker-compose -f dev/docker-compose.yml build

docker-compose -f dev/docker-compose.yml up

