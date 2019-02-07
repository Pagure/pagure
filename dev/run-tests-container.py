#! /usr/bin/env python

import argparse
import os
import subprocess as sp


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
        "--pip",
        action="store_true",
        help="Run the tests in a venv on a Fedora host",
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
        container_names = ["pagure-c7-rpms-py2"]
        container_files = ["centos7-rpms-py2"]
    elif args.fedora is True:
        container_names = ["pagure-f29-rpms-py3"]
        container_files = ["f29-rpms-py3"]
    elif args.pip is True:
        container_names = ["pagure-fedora-pip-py3"]
        container_files = ["fedora-pip-py3"]
    else:
        container_names = [
            "pagure-f29-rpms-py3", "pagure-c7-rpms-py2",
            "pagure-fedora-pip-py3"
        ]
        container_files = [
            "f29-rpms-py3", "centos7-rpms-py2",
            "fedora-pip-py3"
        ]

    for idx, container_name in enumerate(container_names):
        if args.skip_build is not False:
            print("------ Building Container Image -----")
            sp.call(
                [
                    "podman",
                    "build",
                    "--rm",
                    "-t",
                    container_name,
                    "-f",
                    "dev/containers/%s" % container_files[idx],
                    "dev/containers",
                ]
            )

        result_path = "{}/results_{}".format(os.getcwd(), container_files[idx])
        if not os.path.exists(result_path):
            os.mkdir(result_path)

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
                "{}/results_{}:/pagure/results:z".format(
                    os.getcwd(), container_files[idx]),
                "-e",
                "BRANCH=$BRANCH",
                "-e",
                "REPO=$REPO",
                "--entrypoint=/bin/bash",
                container_name,
            ]
            sp.call(command)
        else:
            print("--------- Running Test --------------")
            sp.call(
                [
                    "podman",
                    "run",
                    "-it",
                    "--rm",
                    "--name",
                    container_name,
                    "-v",
                    "{}/results_{}:/pagure/results:z".format(
                        os.getcwd(), container_files[idx]),
                    "-e",
                    "BRANCH={}".format(os.environ.get("BRANCH") or ""),
                    "-e",
                    "REPO={}".format(os.environ.get("REPO") or ""),
                    container_name,
                    args.test_case,
                ]
            )
