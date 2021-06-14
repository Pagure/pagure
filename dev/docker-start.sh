#! /bin/bash

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
ROOT_DIR="$( dirname "$SCRIPT_DIR" )"

cd "$ROOT_DIR"

echo "Pagure Env: $ROOT_DIR/lcl"
mkdir -p lcl/{repos,remotes,attachments,releases}

docker image build -f dev/containers/base -t pagure-base .

COMPOSE=docker-compose
if ! command -v "$COMPOSE" &> /dev/null
then
  echo "docker-compose not found, trying podman-compose.."
  COMPOSE=podman-compose
fi

"$COMPOSE" -f dev/docker-compose.yml build
"$COMPOSE" -f dev/docker-compose.yml up
