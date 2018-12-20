#!/usr/bin/env python3

from __future__ import print_function, unicode_literals, absolute_import

import argparse
import coverage
import json
import logging
import multiprocessing
import os
import shutil
import subprocess
import sys
import threading
import time


RUNNER_PY = "nosetests"
RUNNER_PY2 = "nosetests-2"
RUNNER_PY3 = "nosetests-3"
COVER_PY = "coverage"
COVER_PY2 = "coverage2"
COVER_PY3 = "coverage3"

LASTLEN = None
NUMREMAINING = None
PRINTLOCK = None
RUNNING = []
FAILED = []
NUMPROCS = multiprocessing.cpu_count() - 1
if os.environ.get('BUILD_ID'):
    NUMPROCS = multiprocessing.cpu_count()

LOG = logging.getLogger(__name__)

def setup_parser():
    """ Set up the command line arguments supported and return the arguments
    """

    parser = argparse.ArgumentParser(description="Run the Pagure tests")
    parser.add_argument(
        "--debug",
        dest="debug",
        action="store_true",
        default=False,
        help="Increase the level of data logged.",
    )

    subparsers = parser.add_subparsers(title="actions")

    # RUN
    parser_run = subparsers.add_parser("run", help="Run the tests")
    parser_run.add_argument(
        "--py2",
        dest="py2",
        action="store_true",
        default=False,
        help="Runs the tests only in python2 instead of both python2 and python3",
    )
    parser_run.add_argument(
        "--py3",
        dest="py3",
        action="store_true",
        default=False,
        help="Runs the tests only in python3 instead of both python2 and python3",
    )
    parser_run.add_argument(
        "--results",
        default="results",
        help="Specify a folder in which the results should be placed "
        "(defaults to `results`)",
    )
    parser_run.add_argument(
        "-f",
        "--force",
        default=False,
        action="store_true",
        help="Override the results and newfailed file without asking you",
    )
    parser_run.add_argument(
        "--with-coverage",
        default=False,
        action="store_true",
        help="Also build coverage report",
    )
    parser_run.add_argument(
        "failed_tests",
        nargs="?",
        help="File containing a JSON list of the failed tests to run or "
        "pointing to a test file to run.",
    )
    parser_run.set_defaults(func=do_run)

    # RERUN
    parser_run = subparsers.add_parser("rerun", help="Run failed tests")
    parser_run.add_argument(
        "--debug",
        dest="debug",
        action="store_true",
        default=False,
        help="Expand the level of data returned.",
    )
    parser_run.add_argument(
        "--py2",
        dest="py2",
        action="store_true",
        default=False,
        help="Runs the tests only in python2 instead of both python2 and python3",
    )
    parser_run.add_argument(
        "--py3",
        dest="py3",
        action="store_true",
        default=False,
        help="Runs the tests only in python3 instead of both python2 and python3",
    )
    parser_run.add_argument(
        "--results",
        default="results",
        help="Specify a folder in which the results should be placed "
        "(defaults to `results`)",
    )
    parser_run.add_argument(
        "--with-coverage",
        default=False,
        action="store_true",
        help="Also build coverage report",
    )
    parser_run.set_defaults(func=do_rerun)

    # LIST
    parser_run = subparsers.add_parser("list", help="List failed tests")
    parser_run.add_argument(
        "--results",
        default="results",
        help="Specify a folder in which the results should be placed "
        "(defaults to `results`)",
    )
    parser_run.add_argument(
        "--show",
        default=False,
        action="store_true",
        help="Show the error files using `less`",
    )
    parser_run.add_argument(
        "-n", default=None, nargs="?", type=int,
        help="Number of failed test to show",
    )
    parser_run.set_defaults(func=do_list)

    # SHOW-COVERAGE
    parser_run = subparsers.add_parser(
        "show-coverage",
        help="Shows the coverage report from the data in the results folder")
    parser_run.add_argument(
        "--debug",
        dest="debug",
        action="store_true",
        default=False,
        help="Expand the level of data returned.",
    )
    parser_run.add_argument(
        "--py2",
        dest="py2",
        action="store_true",
        default=False,
        help="Runs the tests only in python2 instead of both python2 and python3",
    )
    parser_run.add_argument(
        "--py3",
        dest="py3",
        action="store_true",
        default=False,
        help="Runs the tests only in python3 instead of both python2 and python3",
    )
    parser_run.add_argument(
        "--results",
        default="results",
        help="Specify a folder in which the results should be placed "
        "(defaults to `results`)",
    )
    parser_run.set_defaults(func=do_show_coverage)

    return parser


def clean_line():
    global LASTLEN

    with PRINTLOCK:
        if LASTLEN is not None:
            print(" " * LASTLEN, end="\r")
        LASTLEN = None


def print_running():
    global LASTLEN

    with PRINTLOCK:
        msg = "Running %d suites: %d remaining, %d failed" % (
            len(RUNNING),
            NUMREMAINING,
            len(FAILED),
        )
        LASTLEN = len(msg)
        print(msg, end="\r")


def add_running(suite):
    global NUMREMAINING

    with PRINTLOCK:
        NUMREMAINING -= 1
        RUNNING.append(suite)
        clean_line()
        print_running()


def remove_running(suite, failed):
    with PRINTLOCK:
        RUNNING.remove(suite)
        clean_line()
        status = 'passed'
        if failed:
            status = 'FAILED'
        print("Test suite %s: %s" % (status, suite))
        print_running()


class WorkerThread(threading.Thread):
    def __init__(self, sem, pyver, suite, results, with_cover):
        name = "py%s-%s" % (pyver, suite)
        super(WorkerThread, self).__init__(name="worker-%s" % name)
        self.name = name
        self.sem = sem
        self.pyver = pyver
        self.suite = suite
        self.failed = None
        self.results = results
        self.with_cover = with_cover

    def run(self):
        with self.sem:
            add_running(self.name)
            with open(os.path.join(self.results, self.name), "w") as resfile:
                if self.pyver == 2:
                    runner = RUNNER_PY2
                elif self.pyver == 3:
                    runner = RUNNER_PY3
                else:
                    runner = RUNNER_PY
                cmd = [runner, "-v", "tests.%s" % self.suite]
                if self.with_cover:
                    cmd.append("--with-cover")

                env = os.environ.copy()
                env.update({
                    "PAGURE_CONFIG": "../tests/test_config",
                    "COVERAGE_FILE": os.path.join(
                        self.results, "%s.coverage" % self.name
                    ),
                    "LANG": "en_US.UTF-8",
                })
                proc = subprocess.Popen(
                    cmd, cwd=".", stdout=resfile, stderr=subprocess.STDOUT, env=env
                )
                res = proc.wait()
                if res == 0:
                    self.failed = False
                else:
                    self.failed = True
            if not self.failed is not True:
                with PRINTLOCK:
                    FAILED.append(self.name)
            remove_running(self.name, self.failed)


def do_run(args):
    """ Performs some checks and runs the tests.
    """

    # Some pre-flight checks
    if not os.path.exists("./.git") or not os.path.exists("./nosetests3"):
        print("Please run from a single level into the Pagure codebase")
        return 1

    if os.path.exists(args.results):
        if not args.force:
            print(
                "Results folder exists, please remove it so we do not clobber"
                " or use --force"
            )
            return 1
        else:
            shutil.rmtree(args.results)

    os.mkdir(args.results)

    print("Pre-flight checks passed")

    suites = []

    if args.failed_tests:
        here = os.path.join(os.path.dirname(os.path.abspath(__file__)))
        failed_tests_fullpath = os.path.join(here, args.failed_tests)
        if not os.path.exists(failed_tests_fullpath):
            print("Could not find the specified file:%s" % failed_tests_fullpath)
            return 1
        print("Loading failed tests")
        try:
            with open(failed_tests_fullpath, "r") as ffile:
                suites = json.loads(ffile.read())
        except json.decoder.JSONDecodeError:
            bname = os.path.basename(args.failed_tests)
            if bname.endswith(".py") and bname.startswith("test_"):
                suites.append(bname.replace(".py", ""))

    if len(suites) == 0:
        print("Loading all tests")
        for fname in os.listdir("./tests"):
            if not fname.endswith(".py"):
                continue
            if not fname.startswith("test_"):
                continue
            suites.append(fname.replace(".py", ""))

    return _run_test_suites(args, suites)


def do_rerun(args):
    """ Re-run tests that failed the last/specified run.
    """

    # Some pre-flight checks
    if not os.path.exists("./.git") or not os.path.exists("./pagure"):
        print("Please run from a single level into the Pagure codebase")
        return 1

    if not os.path.exists(args.results):
        print("Could not find an existing results folder at: %s" % args.results)
        return 1

    if not os.path.exists(os.path.join(args.results, "newfailed")):
        print(
            "Could not find an failed tests in the results folder at: %s" % args.results
        )
        return 1

    print("Pre-flight checks passed")

    suites = []
    tmp = []

    print("Loading failed tests")
    try:
        with open(os.path.join(args.results, "newfailed"), "r") as ffile:
            tmp = json.loads(ffile.read())
    except json.decoder.JSONDecodeError:
        print("File containing the failed tests is not JSON")
        return 1

    for suite in tmp:
        if suite.startswith(("py2-", "py3-")):
            suites.append(suite[4:])

    return _run_test_suites(args, set(suites))


def _get_pyvers(args):
    pyvers = [2, 3]
    if args.py2:
        pyvers = [2,]
    elif args.py3:
        pyvers = [3,]

    un_versioned = False
    try:
        subprocess.check_call(["which", RUNNER_PY])
        un_versioned = True
    except subprocess.CalledProcessError:
        print("No %s found  no unversioned runner" % RUNNER_PY)

    if 2 in pyvers:
        nopy2 = False
        try:
            subprocess.check_call(["which", RUNNER_PY2])
        except subprocess.CalledProcessError:
            print("No %s found, removing python 2" % RUNNER_PY2)
            del pyvers[pyvers.index(2)]

    if 3 in pyvers:
        nopy3 = False
        try:
            subprocess.check_call(["which", RUNNER_PY3])
        except subprocess.CalledProcessError:
            print("No %s found, removing python 3" % RUNNER_PY3)
            del pyvers[pyvers.index(3)]

    if not pyvers and un_versioned:
        pyvers = [""]

    return pyvers


def _run_test_suites(args, suites):
    print("Using %d processes" % NUMPROCS)
    print("Start timing")
    start = time.time()

    global PRINTLOCK
    PRINTLOCK = threading.RLock()
    global NUMREMAINING
    NUMREMAINING = 0

    sem = threading.BoundedSemaphore(NUMPROCS)

    # Create a worker per test
    workers = {}

    pyvers = _get_pyvers(args)

    if not pyvers:
        return 1

    for suite in suites:
        for pyver in pyvers:
            NUMREMAINING += 1
            workers["py%s-%s" % (pyver, suite)] = WorkerThread(
                sem, pyver, suite, args.results, args.with_coverage
            )

    # Start the workers
    print("Starting the workers")
    print()
    print()
    for worker in workers.values():
        worker.start()

    # Wait for them to terminate
    for worker in workers:
        workers[worker].join()
    print_running()
    print()
    print("All work done")

    # Gather results
    print()
    print()

    if FAILED:
        print("Failed tests:")
        for worker in workers:
            if not workers[worker].failed:
                continue
            print("FAILED test: %s" % (worker))

    # Write failed
    if FAILED:
        with open(os.path.join(args.results, "newfailed"), "w") as ffile:
            ffile.write(json.dumps(FAILED))

    # Exit
    outcode = 0
    if len(FAILED) == 0:
        print("ALL PASSED! CONGRATULATIONS!")
    else:
        outcode = 1

    # Stats
    end = time.time()
    print()
    print()
    print(
        "Ran %d tests in %f seconds, of which %d failed"
        % (len(workers), (end - start), len(FAILED))
    )

    if outcode == 0 and args.with_coverage:
        do_show_coverage(args)

    return outcode


def do_list(args):
    """ List tests that failed the last/specified run.
    """

    # Some pre-flight checks
    if not os.path.exists("./.git") or not os.path.exists("./pagure"):
        print("Please run from a single level into the Pagure codebase")
        return 1

    if not os.path.exists(args.results):
        print("Could not find an existing results folder at: %s" % args.results)
        return 1

    if not os.path.exists(os.path.join(args.results, "newfailed")):
        print(
            "Could not find an failed tests in the results folder at: %s" % args.results
        )
        return 1

    print("Pre-flight checks passed")

    suites = []
    tmp = []

    print("Loading failed tests")
    try:
        with open(os.path.join(args.results, "newfailed"), "r") as ffile:
            suites = json.loads(ffile.read())
    except json.decoder.JSONDecodeError:
        print("File containing the failed tests is not JSON")
        return 1

    print("Failed tests")
    failed_tests = len(suites)

    if args.n:
        suites = suites[:args.n]
    print("- " + "\n- ".join(suites))
    print("Total: %s test failed" % failed_tests)

    if args.show:
        for suite in suites:
            cmd = ["less", os.path.join(args.results, suite)]
            subprocess.check_call(cmd)


def do_show_coverage(args):
    print()
    print("Combining coverage results...")

    pyvers = _get_pyvers(args)

    for pyver in pyvers:
        coverfiles = []
        for fname in os.listdir(args.results):
            if fname.endswith(".coverage") and fname.startswith("py%s-" % pyver):
                coverfiles.append(os.path.join(args.results, fname))

        cover = None
        if pyver == 2:
            cover = COVER_PY2
        elif pyver == 3:
            cover = COVER_PY3
        else:
            cover = COVER_PY

        env = {"COVERAGE_FILE": os.path.join(args.results, "combined.coverage")}
        cmd = [cover, "combine"] + coverfiles
        subprocess.check_call(cmd, env=env)
        print()
        print("Python %s coverage: " % pyver)
        cmd = [cover, "report", "--include=./pagure/*", "-m"]
        subprocess.check_call(cmd, env=env)


def main():
    """ Main function """
    # Set up parser for global args
    parser = setup_parser()
    # Parse the commandline
    try:
        arg = parser.parse_args()
    except argparse.ArgumentTypeError as err:
        print("\nError: {0}".format(err))
        return 2

    logging.basicConfig()
    if arg.debug:
        LOG.setLevel(logging.DEBUG)

    if "func" not in arg:
        parser.print_help()
        return 1

    arg.results = os.path.abspath(arg.results)

    return_code = 0

    try:
        return_code = arg.func(arg)
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
        return_code = 1
    except Exception as err:
        print("Error: {0}".format(err))
        logging.exception("Generic error caught:")
        return_code = 5

    return return_code


if __name__ == "__main__":
    sys.exit(main())
