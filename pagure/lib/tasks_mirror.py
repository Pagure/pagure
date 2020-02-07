# -*- coding: utf-8 -*-

"""
 (c) 2018 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals, absolute_import

import base64
import logging
import os
import stat
import struct

import six
import werkzeug.utils

from celery import Celery
from cryptography import utils
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

import pagure.lib.query
from pagure.config import config as pagure_config
from pagure.lib.tasks_utils import pagure_task
from pagure.utils import ssh_urlpattern

# logging.config.dictConfig(pagure_config.get('LOGGING') or {'version': 1})
_log = logging.getLogger(__name__)


if os.environ.get("PAGURE_BROKER_URL"):  # pragma: no-cover
    broker_url = os.environ["PAGURE_BROKER_URL"]
elif pagure_config.get("BROKER_URL"):
    broker_url = pagure_config["BROKER_URL"]
else:
    broker_url = "redis://%s" % pagure_config["REDIS_HOST"]

conn = Celery("tasks_mirror", broker=broker_url, backend=broker_url)
conn.conf.update(pagure_config["CELERY_CONFIG"])


# Code from:
# https://github.com/pyca/cryptography/blob/6b08aba7f1eb296461528328a3c9871fa7594fc4/src/cryptography/hazmat/primitives/serialization.py#L161
# Taken from upstream cryptography since the version we have is too old
# and doesn't have this code (yet)
def _ssh_write_string(data):
    return struct.pack(">I", len(data)) + data


def _ssh_write_mpint(value):
    data = utils.int_to_bytes(value)
    if six.indexbytes(data, 0) & 0x80:
        data = b"\x00" + data
    return _ssh_write_string(data)


# Code from _openssh_public_key_bytes at:
# https://github.com/pyca/cryptography/tree/6b08aba7f1eb296461528328a3c9871fa7594fc4/src/cryptography/hazmat/backends/openssl#L1616
# Taken from upstream cryptography since the version we have is too old
# and doesn't have this code (yet)
def _serialize_public_ssh_key(key):
    if isinstance(key, rsa.RSAPublicKey):
        public_numbers = key.public_numbers()
        return b"ssh-rsa " + base64.b64encode(
            _ssh_write_string(b"ssh-rsa")
            + _ssh_write_mpint(public_numbers.e)
            + _ssh_write_mpint(public_numbers.n)
        )
    else:
        # Since we only write RSA keys, drop the other serializations
        return


def _create_ssh_key(keyfile):
    """ Create the public and private ssh keys.

    The specified file name will be the private key and the public one will
    be in a similar file name ending with a '.pub'.

    """
    private_key = rsa.generate_private_key(
        public_exponent=65537, key_size=4096, backend=default_backend()
    )

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )
    with os.fdopen(
        os.open(keyfile, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb"
    ) as stream:
        stream.write(private_pem)

    public_key = private_key.public_key()
    public_pem = _serialize_public_ssh_key(public_key)
    if public_pem:
        with open(keyfile + ".pub", "wb") as stream:
            stream.write(public_pem)


@conn.task(queue=pagure_config["MIRRORING_QUEUE"], bind=True)
@pagure_task
def setup_mirroring(self, session, username, namespace, name):
    """ Setup the specified project for mirroring.
    """
    plugin = pagure.lib.plugins.get_plugin("Mirroring")
    plugin.db_object()

    project = pagure.lib.query._get_project(
        session, namespace=namespace, name=name, user=username
    )

    public_key_name = werkzeug.utils.secure_filename(project.fullname)
    ssh_folder = pagure_config["MIRROR_SSHKEYS_FOLDER"]

    if not os.path.exists(ssh_folder):
        os.makedirs(ssh_folder, mode=0o700)
    else:
        if os.path.islink(ssh_folder):
            raise pagure.exceptions.PagureException("SSH folder is a link")
        folder_stat = os.stat(ssh_folder)
        filemode = stat.S_IMODE(folder_stat.st_mode)
        if filemode != int("0700", 8):
            raise pagure.exceptions.PagureException(
                "SSH folder had invalid permissions"
            )
        if (
            folder_stat.st_uid != os.getuid()
            or folder_stat.st_gid != os.getgid()
        ):
            raise pagure.exceptions.PagureException(
                "SSH folder does not belong to the user or group running "
                "this task"
            )

    public_key_file = os.path.join(ssh_folder, "%s.pub" % public_key_name)
    _log.info("Public key of interest: %s", public_key_file)

    if os.path.exists(public_key_file):
        raise pagure.exceptions.PagureException("SSH key already exists")

    _log.info("Creating public key")
    _create_ssh_key(os.path.join(ssh_folder, public_key_name))

    with open(public_key_file) as stream:
        public_key = stream.read()

    if project.mirror_hook.public_key != public_key:
        _log.info("Updating information in the DB")
        project.mirror_hook.public_key = public_key
        session.add(project.mirror_hook)
        session.commit()


@conn.task(queue=pagure_config["MIRRORING_QUEUE"], bind=True)
@pagure_task
def teardown_mirroring(self, session, username, namespace, name):
    """ Stop the mirroring of the specified project.
    """
    plugin = pagure.lib.plugins.get_plugin("Mirroring")
    plugin.db_object()

    project = pagure.lib.query._get_project(
        session, namespace=namespace, name=name, user=username
    )

    ssh_folder = pagure_config["MIRROR_SSHKEYS_FOLDER"]

    public_key_name = werkzeug.utils.secure_filename(project.fullname)
    private_key_file = os.path.join(ssh_folder, public_key_name)
    public_key_file = os.path.join(ssh_folder, "%s.pub" % public_key_name)

    if os.path.exists(private_key_file):
        os.unlink(private_key_file)

    if os.path.exists(public_key_file):
        os.unlink(public_key_file)

    project.mirror_hook.public_key = None
    session.add(project.mirror_hook)
    session.commit()


@conn.task(queue=pagure_config["MIRRORING_QUEUE"], bind=True)
@pagure_task
def mirror_project(self, session, username, namespace, name):
    """ Does the actual mirroring of the specified project.
    """
    plugin = pagure.lib.plugins.get_plugin("Mirroring")
    plugin.db_object()

    project = pagure.lib.query._get_project(
        session, namespace=namespace, name=name, user=username
    )

    repofolder = pagure_config["GIT_FOLDER"]
    repopath = os.path.join(repofolder, project.path)
    if not os.path.exists(repopath):
        _log.warning("Git folder not found at: %s, bailing", repopath)
        return

    ssh_folder = pagure_config["MIRROR_SSHKEYS_FOLDER"]
    public_key_name = werkzeug.utils.secure_filename(project.fullname)
    private_key_file = os.path.join(ssh_folder, public_key_name)

    if not os.path.exists(private_key_file):
        _log.warning("No %s key found, bailing", private_key_file)
        project.mirror_hook.last_log = "Private key not found on disk, bailing"
        session.add(project.mirror_hook)
        session.commit()
        return

    # Add the utility script allowing this feature to work on old(er) git.
    here = os.path.join(os.path.dirname(os.path.abspath(__file__)))
    script_file = os.path.join(here, "ssh_script.sh")

    # Get the list of remotes
    remotes = [
        remote.strip()
        for remote in project.mirror_hook.target.split("\n")
        if project.mirror_hook
        and remote.strip()
        and ssh_urlpattern.match(remote.strip())
    ]

    # Push
    logs = []
    for remote in remotes:
        _log.info(
            "Pushing to remote %s using key: %s", remote, private_key_file
        )
        (stdout, stderr) = pagure.lib.git.read_git_lines(
            ["push", "--mirror", remote],
            abspath=repopath,
            error=True,
            env={"SSHKEY": private_key_file, "GIT_SSH": script_file},
        )
        log = "Output from the push:\n  stdout: %s\n  stderr: %s" % (
            stdout,
            stderr,
        )
        logs.append(log)

    if logs:
        project.mirror_hook.last_log = "\n".join(logs)
        session.add(project.mirror_hook)
        session.commit()
        _log.info("\n".join(logs))
