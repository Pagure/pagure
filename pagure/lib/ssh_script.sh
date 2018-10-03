#!/bin/sh
ssh -i $SSHKEY -oStrictHostKeyChecking=no "$@"
