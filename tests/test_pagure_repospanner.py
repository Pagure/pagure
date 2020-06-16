# -*- coding: utf-8 -*-

"""
 (c) 2015-2018 - Copyright Red Hat Inc

 Authors:
   Patrick Uiterwijk <puiterwijk@redhat.com>

"""

from __future__ import unicode_literals, absolute_import

import datetime
import functools
import munch
import unittest
import shutil
import subprocess
import sys
import tempfile
import time
import os

import six
import json
import pygit2
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from mock import patch, MagicMock

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
)

import pagure.lib.query
import pagure.cli.admin
import tests


REPOSPANNER_CONFIG_TEMPLATE = """
---
ca:
  path: %(path)s/repospanner/pki
admin:
  url:  https://localhost.localdomain:%(gitport)s/
  ca:   %(path)s/repospanner/pki/ca.crt
  cert: %(path)s/repospanner/pki/admin.crt
  key:  %(path)s/repospanner/pki/admin.key
storage:
  state: %(path)s/repospanner/state
  git:
    type: tree
    clustered: true
    directory: %(path)s/repospanner/git
listen:
  rpc:  127.0.0.1:%(rpcport)s
  http: 127.0.0.1:%(gitport)s
certificates:
  ca: %(path)s/repospanner/pki/ca.crt
  client:
    cert: %(path)s/repospanner/pki/repospanner.localhost.crt
    key:  %(path)s/repospanner/pki/repospanner.localhost.key
  server:
    default:
      cert: %(path)s/repospanner/pki/repospanner.localhost.crt
      key:  %(path)s/repospanner/pki/repospanner.localhost.key
hooks:
  debug: true
  bubblewrap:
    enabled: false
    unshare:
    - net
    - ipc
    - pid
    - uts
    share_net: false
    mount_proc: true
    mount_dev: true
    uid:
    gid:
    hostname: myhostname
    bind:
    ro_bind:
    - - /usr
      - /usr
    - - %(codepath)s
      - %(codepath)s
    - - %(path)s
      - %(path)s
    - - %(crosspath)s
      - %(crosspath)s
    symlink:
    - - usr/lib64
      - /lib64
    - - usr/bin
      - /bin
  runner: %(hookrunner_bin)s
  user: 0
"""


class PagureRepoSpannerTests(tests.Modeltests):
    """ Tests for repoSpanner integration of pagure """

    repospanner_binary = None
    repospanner_runlog = None
    repospanner_proc = None

    def run_cacmd(self, logfile, *args):
        """ Run a repoSpanner CA command. """
        subprocess.check_call(
            [
                self.repospanner_binary,
                "--config",
                os.path.join(self.path, "repospanner", "config.yml"),
                # NEVER use this in a production system! It makes repeatable keys
                "ca",
            ]
            + list(args)
            + ["--very-insecure-weak-keys"],
            stdout=logfile,
            stderr=subprocess.STDOUT,
        )

    def setUp(self):
        """ set up the environment. """
        possible_paths = ["./repospanner", "/usr/bin/repospanner"]

        for option in possible_paths:
            option = os.path.abspath(option)
            if os.path.exists(option):
                self.repospanner_binary = option
                break

        if not self.repospanner_binary:
            raise unittest.SkipTest("repoSpanner not found")

        hookrunbins = [
            os.path.join(
                os.path.dirname(self.repospanner_binary), "repohookrunner"
            ),
            os.path.join("/usr", "libexec", "repohookrunner"),
        ]
        found = False
        for hookrunbin in hookrunbins:
            if os.path.exists(hookrunbin):
                found = True
                break
        if not found:
            raise Exception("repoSpanner found, but repohookrunner not")

        repobridgebins = [
            os.path.join(
                os.path.dirname(self.repospanner_binary), "repobridge"
            ),
            os.path.join("/usr", "libexec", "repobridge"),
        ]
        found = False
        for repobridgebin in repobridgebins:
            if os.path.exists(repobridgebin):
                found = True
                break
        if not found:
            raise Exception("repoSpanner found, but repobridge not")

        self.config_values["repobridge_binary"] = repobridgebin

        codepath = os.path.normpath(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "../")
        )

        # Only run the setUp() function if we are actually going ahead and run
        # this test. The reason being that otherwise, setUp will set up a
        # database, but because we "error out" from setUp, the tearDown()
        # function never gets called, leaving it behind.
        super(PagureRepoSpannerTests, self).setUp()

        # TODO: Find free ports
        configvals = {
            "path": self.path,
            "crosspath": self.dbfolder,
            "gitport": 8443 + sys.version_info.major,
            "rpcport": 8445 + sys.version_info.major,
            "codepath": codepath,
            "hookrunner_bin": hookrunbin,
        }

        os.mkdir(os.path.join(self.path, "repospanner"))
        cfgpath = os.path.join(self.path, "repospanner", "config.yml")
        with open(cfgpath, "w") as cfg:
            cfg.write(REPOSPANNER_CONFIG_TEMPLATE % configvals)

        with open(
            os.path.join(self.path, "repospanner", "keylog"), "w"
        ) as keylog:
            # Create the CA
            self.run_cacmd(
                keylog,
                "init",
                "localdomain",
                "--no-name-constraint",
                "--random-cn",
            )
            # Create the node cert
            self.run_cacmd(keylog, "node", "localhost", "repospanner")
            # Create the admin cert
            self.run_cacmd(
                keylog,
                "leaf",
                "admin",
                "--admin",
                "--region",
                "*",
                "--repo",
                "*",
            )
            # Create the Pagure cert
            self.run_cacmd(
                keylog,
                "leaf",
                "pagure",
                "--read",
                "--write",
                "--region",
                "*",
                "--repo",
                "*",
            )

        with open(
            os.path.join(self.path, "repospanner", "spawnlog"), "w"
        ) as spawnlog:
            # Initialize state
            subprocess.check_call(
                [
                    self.repospanner_binary,
                    "--config",
                    cfgpath,
                    "serve",
                    "--spawn",
                ],
                stdout=spawnlog,
                stderr=subprocess.STDOUT,
            )

        self.repospanner_runlog = open(
            os.path.join(self.path, "repospanner", "runlog"), "w+"
        )

        try:
            self.repospanner_proc = subprocess.Popen(
                [
                    self.repospanner_binary,
                    "--config",
                    cfgpath,
                    "serve",
                    "--debug",
                ],
                stdout=self.repospanner_runlog,
                stderr=subprocess.STDOUT,
            )
        except:
            # Make sure to clean up repoSpanner, since we did start it
            self.tearDown()
            raise

        attempts = 0
        while True:
            try:
                # Wait for the instance to become available
                resp = requests.get(
                    "https://repospanner.localhost.localdomain:%d/"
                    % configvals["gitport"],
                    verify=os.path.join(
                        self.path, "repospanner", "pki", "ca.crt"
                    ),
                    cert=(
                        os.path.join(
                            self.path, "repospanner", "pki", "pagure.crt"
                        ),
                        os.path.join(
                            self.path, "repospanner", "pki", "pagure.key"
                        ),
                    ),
                )
                resp.raise_for_status()

                print("repoSpanner identification: %s" % resp.text)
                break
            except:
                if attempts < 5:
                    attempts += 1
                    time.sleep(1)
                    continue
                # Make sure to clean up repoSpanner, since we did start it
                self.tearDown()
                raise

        # Upload the hook script to repoSpanner
        args = munch.Munch({"region": "default"})
        hookid = pagure.cli.admin.do_upload_repospanner_hooks(args)
        pagure.config.config["REPOSPANNER_REGIONS"]["default"]["hook"] = hookid

    def tearDown(self):
        """ Tear down the repoSpanner instance. """
        if self.repospanner_proc:
            # Tear down
            self.repospanner_proc.terminate()
            exitcode = self.repospanner_proc.wait()
            if exitcode != 0:
                print("repoSpanner exit code: %d" % exitcode)

        if self.repospanner_runlog:
            self.repospanner_runlog.close()

        super(PagureRepoSpannerTests, self).tearDown()


def print_repospanner_log(fn):
    @functools.wraps(fn)
    def wrapper(self, *args, **kwargs):
        try:
            return fn(self, *args, **kwargs)
        finally:
            if self.repospanner_runlog:
                self.repospanner_runlog.seek(0, 0)
                print("repoSpanner log follows:")
                print(self.repospanner_runlog.read())

    return wrapper


class PagureRepoSpannerTestsNewRepoDefault(PagureRepoSpannerTests):
    config_values = {
        "repospanner_new_repo": "'default'",
        "authbackend": "test_auth",
    }

    @print_repospanner_log
    @patch("pagure.ui.app.admin_session_timedout")
    def test_new_project(self, ast):
        """ Test creating a new repo by default on repoSpanner works. """
        ast.return_value = False

        user = tests.FakeUser(username="foo")
        with tests.user_set(self.app.application, user):
            output = self.app.get("/new/")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn("<strong>Create new Project</strong>", output_text)

            data = {
                "name": "project-1",
                "description": "Project #1",
                "create_readme": "y",
                "csrf_token": self.get_csrf(),
            }

            output = self.app.post("/new/", data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<div class="projectinfo my-3">\nProject #1', output_text
            )
            self.assertIn(
                "<title>Overview - project-1 - Pagure</title>", output_text
            )
            self.assertIn("Added the README", output_text)

            output = self.app.get("/project-1/settings")
            self.assertIn(
                "This repository is on repoSpanner region default",
                output.get_data(as_text=True),
            )

        with tests.user_set(
            self.app.application, tests.FakeUser(username="pingou")
        ):
            # Verify that for forking, Git auth status is ignored (hooks should not be run)
            self.set_auth_status(False)

            data = {"csrf_token": self.get_csrf()}

            output = self.app.post(
                "/do_fork/project-1", data=data, follow_redirects=True
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<div class="projectinfo my-3">\nProject #1', output_text
            )
            self.assertIn(
                "<title>Overview - project-1 - Pagure</title>", output_text
            )
            self.assertIn("Added the README", output_text)
            self.assertIn(
                "/?next=http://localhost/fork/pingou/project-1", output_text
            )

            output = self.app.get("/fork/pingou/project-1/settings")
            self.assertIn(
                "This repository is on repoSpanner region default",
                output.get_data(as_text=True),
            )

        # Verify that only pseudo repos exist, and no on-disk repos got created
        repodirlist = os.listdir(os.path.join(self.path, "repos"))
        self.assertEqual(repodirlist, ["pseudo"])

    @print_repospanner_log
    @patch.dict(
        "pagure.config.config",
        {
            "ALLOW_HTTP_PULL_PUSH": True,
            "ALLOW_HTTP_PUSH": True,
            "HTTP_REPO_ACCESS_GITOLITE": False,
        },
    )
    def test_http_pull(self):
        """ Test that the HTTP pull endpoint works for repoSpanner. """
        tests.create_projects(self.session)
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)
        self.create_project_full("clonetest", {"create_readme": "y"})

        # Verify the new project is indeed on repoSpanner
        project = pagure.lib.query._get_project(self.session, "clonetest")
        self.assertTrue(project.is_on_repospanner)

        # Unfortunately, actually testing a git clone would need the app to
        # run on a TCP port, which the test environment doesn't do.
        output = self.app.get(
            "/clonetest.git/info/refs?service=git-upload-pack"
        )
        self.assertEqual(output.status_code, 200)
        self.assertEqual(
            output.content_type, "application/x-git-upload-pack-advertisement"
        )
        output_text = output.get_data(as_text=True)
        self.assertIn("# service=git-upload-pack", output_text)
        self.assertIn("agent=repoSpanner", output_text)
        self.assertIn("symref=HEAD:refs/heads/master", output_text)
        self.assertIn(" refs/heads/master\x00", output_text)

        output = self.app.post(
            "/clonetest.git/git-upload-pack",
            headers={"Content-Type": "application/x-git-upload-pack-request"},
        )
        self.assertEqual(output.status_code, 400)
        output_text = output.get_data(as_text=True)
        self.assertIn("Error processing your request", output_text)

    @print_repospanner_log
    @patch.dict(
        "pagure.config.config",
        {
            "ALLOW_HTTP_PULL_PUSH": True,
            "ALLOW_HTTP_PUSH": True,
            "HTTP_REPO_ACCESS_GITOLITE": False,
        },
    )
    def test_http_push(self):
        """ Test that the HTTP push endpoint works for repoSpanner. """
        tests.create_projects(self.session)
        tests.create_tokens(self.session)
        tests.create_tokens_acl(self.session)
        self.create_project_full("clonetest", {"create_readme": "y"})

        # Verify the new project is indeed on repoSpanner
        project = pagure.lib.query._get_project(self.session, "clonetest")
        self.assertTrue(project.is_on_repospanner)

        # Unfortunately, actually testing a git clone would need the app to
        # run on a TCP port, which the test environment doesn't do.
        output = self.app.get(
            "/clonetest.git/info/refs?service=git-receive-pack",
            environ_overrides={"REMOTE_USER": "pingou"},
        )
        self.assertEqual(output.status_code, 200)
        self.assertEqual(
            output.content_type, "application/x-git-receive-pack-advertisement"
        )
        output_text = output.get_data(as_text=True)
        self.assertIn("# service=git-receive-pack", output_text)
        self.assertIn("agent=repoSpanner", output_text)
        self.assertIn("symref=HEAD:refs/heads/master", output_text)
        self.assertIn(" refs/heads/master\x00", output_text)

    @print_repospanner_log
    @patch("pagure.ui.app.admin_session_timedout")
    def test_hooks(self, ast):
        """ Test hook setting and running works. """
        ast.return_value = False
        pagure.cli.admin.session = self.session

        user = tests.FakeUser(username="foo")
        with tests.user_set(self.app.application, user):
            data = {
                "name": "project-1",
                "description": "Project #1",
                "create_readme": "y",
                "csrf_token": self.get_csrf(),
            }

            output = self.app.post("/new/", data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<div class="projectinfo my-3">\nProject #1', output_text
            )
            self.assertIn(
                "<title>Overview - project-1 - Pagure</title>", output_text
            )
            self.assertIn("Added the README", output_text)

            output = self.app.get("/project-1/settings")
            self.assertIn(
                "This repository is on repoSpanner region default",
                output.get_data(as_text=True),
            )

            # Check file before the commit:
            output = self.app.get("/project-1/raw/master/f/README.md")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertEqual(output_text, "# project-1\n\nProject #1")

        with tests.user_set(self.app.application, user):
            # Set editing Denied
            self.set_auth_status(False)

            # Try to make an edit in the repo
            data = {
                "content": "foo\n bar\n  baz",
                "commit_title": "test commit",
                "commit_message": "Online commit",
                "email": "foo@bar.com",
                "branch": "master",
                "csrf_token": self.get_csrf(),
            }

            output = self.app.post(
                "/project-1/edit/master/f/README.md",
                data=data,
                follow_redirects=True,
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn("Remote hook declined the push: ", output_text)
            self.assertIn(
                "Denied push for ref &#39;refs/heads/master&#39; for user &#39;foo&#39;",
                output_text,
            )

            # Check file after the commit:
            output = self.app.get("/project-1/raw/master/f/README.md")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertEqual(output_text, "# project-1\n\nProject #1")

            # Set editing Allowed
            self.set_auth_status(True)

            # Try to make an edit in the repo
            data = {
                "content": "foo\n bar\n  baz",
                "commit_title": "test commit",
                "commit_message": "Online commit",
                "email": "foo@bar.com",
                "branch": "master",
                "csrf_token": self.get_csrf(),
            }

            output = self.app.post(
                "/project-1/edit/master/f/README.md",
                data=data,
                follow_redirects=True,
            )
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "<title>Commits - project-1 - Pagure</title>", output_text
            )

            # Check file after the commit:
            output = self.app.get("/project-1/raw/master/f/README.md")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertEqual(output_text, "foo\n bar\n  baz")

    @print_repospanner_log
    @patch.dict(
        "pagure.config.config",
        {
            "PAGURE_ADMIN_USERS": ["pingou"],
            "ALLOW_ADMIN_IGNORE_EXISTING_REPOS": True,
        },
    )
    @patch("pagure.ui.app.admin_session_timedout")
    def test_adopt_project(self, ast):
        """ Test adopting a project in repoSpanner works. """
        ast.return_value = False

        user = tests.FakeUser(username="foo")
        with tests.user_set(self.app.application, user):
            output = self.app.get("/new/")
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn("<strong>Create new Project</strong>", output_text)

            data = {
                "name": "project-1",
                "description": "Project #1",
                "create_readme": "y",
                "csrf_token": self.get_csrf(),
            }

            output = self.app.post("/new/", data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<div class="projectinfo my-3">\nProject #1', output_text
            )
            self.assertIn(
                "<title>Overview - project-1 - Pagure</title>", output_text
            )
            self.assertIn("Added the README", output_text)

            output = self.app.get("/project-1/settings")
            self.assertIn(
                "This repository is on repoSpanner region default",
                output.get_data(as_text=True),
            )

        # Delete the project instance so that the actual repo remains
        project = pagure.lib.query._get_project(self.session, "project-1")
        self.session.delete(project)
        self.session.commit()
        shutil.rmtree(os.path.join(self.path, "repos", "pseudo"))

        user = tests.FakeUser(username="pingou")
        with tests.user_set(self.app.application, user):
            output = self.app.get("/project-1/")
            self.assertEqual(output.status_code, 404)

            data = {
                "name": "project-1",
                "description": "Recreated project #1",
                "create_readme": "false",
                "csrf_token": self.get_csrf(),
            }
            output = self.app.post("/new/", data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                "Repo pagure/main/project-1 already exists", output_text
            )

            data["ignore_existing_repos"] = "y"
            output = self.app.post("/new/", data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            output_text = output.get_data(as_text=True)
            self.assertIn(
                '<div class="projectinfo my-3">\nRecreated project #1',
                output_text,
            )
            self.assertIn(
                "<title>Overview - project-1 - Pagure</title>", output_text
            )
            self.assertIn("Added the README", output_text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
