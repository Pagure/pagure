#! /usr/bin/python3
import argparse
import os
import subprocess as sp
from string import Template

TEMPLATE = "dev/docker/test_env_template"

PKG_LIST = "python-alembic python-arrow python-binaryornot \
            python-bleach python-blinker python-chardet python-cryptography \
            python-docutils python-enum34 python-flask python2-fedora-flask \
            python-flask-wtf python2-bcrypt python-jinja2 \
            python-markdown python-munch python-openid-cla \
            python-openid-teams python-psutil python-pygit2 python2-pillow \
            python-sqlalchemy python-straight-plugin python-wtforms \
            python-nose python3-coverage python-mock python-mock \
            python-eventlet python2-flask-oidc python-flake8 python-celery \
            python-redis python-trololio python-beautifulsoup4 redis vim git"


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
        base_image = "registry.fedoraproject.org/fedora:28"
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
