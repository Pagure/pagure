#! /usr/bin/python3
import argparse
import os
import subprocess as sp
from string import Template

TEMPLATE = "dev/docker/test_env_template"

PKG_LIST = "python3-alembic python3-arrow python3-binaryornot \
            python3-bleach python3-blinker python3-chardet python3-cryptography \
            python3-docutils python3-flask python3-fedora-flask \
            python3-flask-wtf python3-bcrypt python3-jinja2 \
            python3-markdown python3-munch python3-openid-cla \
            python3-openid-teams python3-psutil python3-pygit2 python3-pillow \
            python3-sqlalchemy python3-straight-plugin python3-wtforms \
            python3-nose python3-coverage python3-mock python3-mock \
            python3-eventlet python3-flask-oidc python3-flake8 python3-celery \
            python3-redis python3-trololio python3-beautifulsoup4 python3-black redis vim git"


def setup_parser():
    """ Setup the cli arguments """
    parser = argparse.ArgumentParser(prog="pagure-test")
    parser.add_argument(
        "test_case", nargs="?", default="", help="Run the given test case"
    )
    parser.add_argument(
        "--fedora",
        action="store_true",
        help="Run the tests in fedora environment (DEFAULT)",
    )
    parser.add_argument(
        "--centos",
        action="store_true",
        help="Run the tests in centos environment",
    )
    parser.add_argument(
        "--skip-build",
        dest="skip_build",
        action="store_false",
        help="Skip building the container image",
    )
    parser.add_argument(
        "--shell",
        dest="shell",
        action="store_true",
        help="Gives you a shell into the container instead "
        "of running the tests",
    )

    return parser


if __name__ == "__main__":
    parser = setup_parser()
    args = parser.parse_args()

    if args.centos is True:
        base_image = "centos:7"
        pkg_mgr = "yum"
        epel_pkg = "RUN yum -y install epel-release"
        infra_repo = (
            "ADD ./fedora-infra-tags.repo /etc/yum.repos.d/infra-tags.repo"
        )
        container_name = "pagure-test-centos"
        PKG_LIST += "python34 python34-coverage"
    else:
        base_image = "registry.fedoraproject.org/fedora:latest"
        pkg_mgr = "dnf"
        container_name = "pagure-test-fedora"
        epel_pkg = ""
        infra_repo = ""

    with open(TEMPLATE, "r") as fp:
        t = Template(fp.read())
    with open("dev/docker/test_env", "w") as fp:
        fp.write(
            t.substitute(
                base_image=base_image,
                pkg_list=PKG_LIST,
                pkg_mgr=pkg_mgr,
                epel_pkg=epel_pkg,
                infra_repo=infra_repo,
            )
        )

    if args.skip_build is not False:
        print("------ Building Docker Image -----")
        sp.run(
            [
                "podman",
                "build",
                "--rm",
                "-t",
                container_name,
                "-f",
                "dev/docker/test_env",
                "dev/docker",
            ]
        )
    if args.shell:
        print("--------- Shelling in the container --------------")
        command = [
            "podman",
            "run",
            "-it",
            "--rm",
            "--name",
            container_name,
            "-v",
            "{}:/pagure".format(os.getcwd()),
            "--entrypoint=/bin/bash",
            container_name,
        ]
        sp.run(command)

    else:

        print("--------- Running Test --------------")
        sp.run(
            [
                "podman",
                "run",
                "-it",
                "--rm",
                "--name",
                container_name,
                "-v",
                "{}:/pagure".format(os.getcwd()),
                container_name,
                args.test_case,
            ]
        )
