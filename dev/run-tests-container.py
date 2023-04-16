#!/usr/bin/env -S python -u

import argparse
import os
import subprocess as sp


ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))


def _container_image_exist(container_name, container_type):
    cmd = [
        "podman",
        "image",
        "exists",
        containers[container_name][container_type]
    ]
    return _call_command(cmd)


def _build_container(container_name, container_type, container_volume=None, **kwargs):
    # kwargs can be used to pass '--build-arg'
    build_args = []
    for arg in kwargs.values():
        build_args.append("--build-arg")
        build_args.append(arg)

    volume = []
    if container_volume:
        volume.append("-v")
        volume.append(volume)

    container_file = ""
    if container_type == "base":
        container_file = containers[container_name]["base"]
        container_name = container_file
    if container_type == "code":
        container_file = containers[container_name]["code"]
        container_name = container_file

    cmd = [
        "podman",
        "build",
        "--rm",
        "-t",
        container_name,
        "-f",
        ROOT + "/dev/containers/%s" % container_file,
        ROOT + "/dev/containers",
    ]

    cmd += build_args
    cmd += volume

    return _call_command(cmd)


def _call_command(cmd):
    print("Command: " + " ".join(cmd))
    rc = sp.call(cmd)
    if rc != 0:
        return False
    else:
        return True


def _check_pre_reqs():
    programs = [
        {
            "name": "podman",
            "cmd": ["podman", "version"]
        },
        {
            "name": "git",
            "cmd": ["git", "version"]
        }
    ]

    # 'os.devnull' used for backward compatibility with Python2.
    # for Py3 only, 'sp.DEVNULL' can be used and this workaround removed.
    FNULL = open(os.devnull, 'w')

    missing = []
    for program in programs:
        try:
            sp.call(program["cmd"], stdout=FNULL, stderr=sp.STDOUT)
        except OSError:
            missing.append(program["name"])

    if len(missing) > 0:
        print("Error! Required programs not found: " + ", ".join(missing))
        os._exit(1)


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
        "--rebuild",
        dest="rebuild",
        action="store_true",
        help="Enforce rebuild of container images",
    )
    parser.add_argument(
        "--rebuild-code",
        dest="rebuild_code",
        action="store_true",
        help="Enforce rebuild of code container images only",
    )
    parser.add_argument(
        "--shell",
        dest="shell",
        action="store_true",
        help="Gives you a shell into the container instead "
        "of running the tests",
    )

    parser.add_argument(
        "--repo",
        dest="repo",
        default="https://pagure.io/pagure.git",
        help="URL of the public repo to use as source, can be overridden using "
        "the REPO environment variable",
    )
    parser.add_argument(
        "--branch",
        dest="branch",
        default="master",
        help="Branch of the repo to use as source, can be overridden using "
        "the BRANCH environment variable",
    )

    return parser


if __name__ == "__main__":
    _check_pre_reqs()

    parser = setup_parser()
    args = parser.parse_args()

    containers = {
        "centos": {
            "name": "pagure-tests-centos-stream8-rpms-py3",
            "base": "base-centos-stream8-rpms-py3",
            "code": "code-centos-stream8-rpms-py3"
        },
        "fedora": {
            "name": "pagure-tests-fedora-rpms-py3",
            "base": "base-fedora-rpms-py3",
            "code": "code-fedora-rpms-py3"
        },
        "pip": {
            "name": "pagure-tests-fedora-pip-py3",
            "base": "base-fedora-pip-py3",
            "code": "code-fedora-pip-py3"
        }
    }

    if args.centos:
        container_names = ["centos"]
    elif args.fedora:
        container_names = ["fedora"]
    elif args.pip:
        container_names = ["pip"]
    else:
        container_names = ["centos", "fedora", "pip"]

    failed = []
    print("Running for %d containers:" % len(container_names))
    print("  - " + "\n  - ".join(container_names))
    for container_name in container_names:
        print("\n------ Building Container Image -----")

        if not _container_image_exist(container_name, "base") or args.rebuild:
            print("Container does not exist, building: %s" % containers[container_name]["base"])
            if _build_container(
                container_name,
                "base",
                branch="{}".format(os.environ.get("BRANCH") or args.branch),
                repo="{}".format(os.environ.get("REPO") or args.repo)
            ):
                base_build = True
            else:
                print("Failed building: %s" % containers[container_name]["base"])
                break
        else:
            base_build = False
            print("Container already exist, skipped building: %s" % containers[container_name]["base"])

        if not _container_image_exist(container_name, "code") or \
                base_build or \
                args.rebuild or \
                args.rebuild_code:
            print("Container does not exist, building: %s" % containers[container_name]["code"])
            if not _build_container(container_name, "code"):
                print("Failed building: %s" % containers[container_name]["code"])
                break
        else:
            print("Container already exist, skipped building: %s" % containers[container_name]["code"])

        result_path = "{}/results_{}".format(os.getcwd(), containers[container_name]["name"])
        if not os.path.exists(result_path):
            os.mkdir(result_path)

        if args.shell:
            print("--------- Shelling in the container --------------")
            cmd = [
                "podman",
                "run",
                "-it",
                "--rm",
                "--name",
                containers[container_name]["name"],
                "-v",
                "{}/results_{}:/results:z".format(
                    os.getcwd(), containers[container_name]["name"]
                ),
                "-e",
                "BRANCH={}".format(os.environ.get("BRANCH") or args.branch),
                "-e",
                "REPO={}".format(os.environ.get("REPO") or args.repo),
                "--entrypoint=/bin/bash",
                containers[container_name]["code"],
            ]
            sp.call(cmd)
        else:
            print("--------- Running Test --------------")
            cmd = [
                "podman",
                "run",
                "-it",
                "--rm",
                "--name",
                containers[container_name]["name"],
                "-v",
                "{}/results_{}:/results:z".format(
                    os.getcwd(), containers[container_name]["name"]
                ),
                "-e",
                "BRANCH={}".format(os.environ.get("BRANCH") or args.branch),
                "-e",
                "REPO={}".format(os.environ.get("REPO") or args.repo),
                "-e",
                "TESTCASE={}".format(args.test_case or ""),
                containers[container_name]["code"],
            ]
            if not _call_command(cmd):
                failed.append(container_name)

    if not args.shell:
        print("\nSummary:")
        if not failed:
            print("  ALL TESTS PASSED")
        else:
            print("  %s TESTS FAILED:" % len(failed))
            for fail in failed:
                print("    - %s" % fail)
