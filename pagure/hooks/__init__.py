# -*- coding: utf-8 -*-

"""
 (c) 2014-2017 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals, absolute_import

import subprocess
import sys
import traceback
import os

import six
import wtforms

from pagure.config import config as pagure_config
from pagure.exceptions import FileNotFoundException
import pagure.lib.query
import pagure.lib.git
from pagure.lib.git_auth import get_git_auth_helper
from pagure.lib.plugins import get_enabled_plugins


class RequiredIf(wtforms.validators.DataRequired):
    """Wtforms validator setting a field as required if another field
    has a value.
    """

    def __init__(self, fields, *args, **kwargs):
        if isinstance(fields, six.string_types):
            fields = [fields]
        self.fields = fields
        super(RequiredIf, self).__init__(*args, **kwargs)

    def __call__(self, form, field):
        for fieldname in self.fields:
            nfield = form._fields.get(fieldname)
            if nfield is None:
                raise Exception('no field named "%s" in form' % fieldname)
            if bool(nfield.data):
                if (
                    not field.data
                    or isinstance(field.data, six.string_types)
                    and not field.data.strip()
                ):
                    if self.message is None:
                        message = field.gettext("This field is required.")
                    else:
                        message = self.message

                    field.errors[:] = []
                    raise wtforms.validators.StopValidation(message)


class BaseRunner(object):
    dbobj = None

    @classmethod
    def runhook(
        cls,
        session,
        username,
        hooktype,
        project,
        repotype,
        repodir,
        changes,
        pull_request,
    ):
        """Run a specific hook on a project.

        By default, this calls out to the pre_receive, update or post_receive
        functions as appropriate.

        Args:
            session (Session): Database session
            username (string): The user performing a push
            project (model.Project): The project this call is made for
            repotype (string): Value of lib.query.get_repotypes() indicating
                for which repo the current call is
            repodir (string): Directory where a clone of the specified repo is
                located. Do note that this might or might not be a writable
                clone.
            changes (dict): A dict with keys being the ref to update, values
                being a tuple of (from, to).
                For example: {'refs/heads/master': (hash_from, hash_to), ...}
            pull_request (model.PullRequest or None): The pull request whose
                merge is initiating this hook run.
        """
        if hooktype == "pre-receive":
            cls.pre_receive(
                session=session,
                username=username,
                project=project,
                repotype=repotype,
                repodir=repodir,
                changes=changes,
                pull_request=pull_request,
            )
        elif hooktype == "update":
            cls.update(
                session=session,
                username=username,
                project=project,
                repotype=repotype,
                repodir=repodir,
                changes=changes,
                pull_request=pull_request,
            )

        elif hooktype == "post-receive":
            cls.post_receive(
                session=session,
                username=username,
                project=project,
                repotype=repotype,
                repodir=repodir,
                changes=changes,
                pull_request=pull_request,
            )
        else:
            raise ValueError('Invalid hook type "%s"' % hooktype)

    @staticmethod
    def pre_receive(
        session, username, project, repotype, repodir, changes, pull_request
    ):
        """Run the pre-receive tasks of a hook.

        For args, see BaseRunner.runhook.
        """
        pass

    @staticmethod
    def update(
        session, username, project, repotype, repodir, changes, pull_request
    ):
        """Run the update tasks of a hook.

        For args, see BaseRunner.runhook.
        Note that the "changes" list has exactly one element.
        """
        pass

    @staticmethod
    def post_receive(
        session, username, project, repotype, repodir, changes, pull_request
    ):
        """Run the post-receive tasks of a hook.

        For args, see BaseRunner.runhook.
        """
        pass


class BaseHook(object):
    """ Base class for pagure's hooks. """

    name = None
    form = None
    description = None
    backref = None
    db_object = None
    # hook_type is not used in hooks that use a Runner class, as those can
    # implement run actions on whatever is useful to them.
    hook_type = "post-receive"
    runner = None

    @classmethod
    def set_up(cls, project):
        """Install the generic post-receive hook that allow us to call
        multiple post-receive hooks as set per plugin.
        """
        if project.is_on_repospanner:
            # If the project is on repoSpanner, there's nothing to set up,
            # as the hook script will be arranged by repo creation.
            return

        hook_files = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "files"
        )

        for repotype in pagure.lib.query.get_repotypes():
            repopath = project.repopath(repotype)
            if repopath is None:
                continue

            # Make sure the hooks folder exists
            hookfolder = os.path.join(repopath, "hooks")
            if not os.path.exists(hookfolder):
                os.makedirs(hookfolder)

            for hooktype in ("pre-receive", "update", "post-receive"):
                # Install the main hook file
                target = os.path.join(hookfolder, hooktype)
                if not os.path.exists(target):
                    if os.path.islink(target):
                        os.unlink(target)
                    os.symlink(os.path.join(hook_files, "hookrunner"), target)

    @classmethod
    def base_install(cls, repopaths, dbobj, hook_name, filein):
        """Method called to install the hook for a project.

        :arg project: a ``pagure.model.Project`` object to which the hook
            should be installed
        :arg dbobj: the DB object the hook uses to store the settings
            information.

        """
        if cls.runner:
            # In the case of a new-style hook (with a Runner), there is no
            # need to copy any files into place
            return

        for repopath in repopaths:
            if not os.path.exists(repopath):
                raise FileNotFoundException("Repo %s not found" % repopath)

            hook_files = os.path.join(
                os.path.dirname(os.path.realpath(__file__)), "files"
            )

            # Make sure the hooks folder exists
            hookfolder = os.path.join(repopath, "hooks")
            if not os.path.exists(hookfolder):
                os.makedirs(hookfolder)

            # Install the hook itself
            hook_file = os.path.join(
                repopath, "hooks", cls.hook_type + "." + hook_name
            )

            if not os.path.exists(hook_file):
                os.symlink(os.path.join(hook_files, filein), hook_file)

    @classmethod
    def base_remove(cls, repopaths, hook_name):
        """Method called to remove the hook of a project.

        :arg project: a ``pagure.model.Project`` object to which the hook
            should be installed

        """
        for repopath in repopaths:
            if not os.path.exists(repopath):
                raise FileNotFoundException("Repo %s not found" % repopath)

            hook_path = os.path.join(
                repopath, "hooks", cls.hook_type + "." + hook_name
            )
            if os.path.exists(hook_path):
                os.unlink(hook_path)

    @classmethod
    def install(cls, *args):
        """In sub-classess, this can be used for installation of the hook.

        However, this is not required anymore for hooks with a Runner.
        This class is here as backwards compatibility.

        All args are ignored.
        """
        if not cls.runner:
            raise ValueError("BaseHook.install called for runner-less hook")

    @classmethod
    def remove(cls, *args):
        """In sub-classess, this can be used for removal of the hook.

        However, this is not required anymore for hooks with a Runner.
        This class is here as backwards compatibility.

        All args are ignored.
        """
        if not cls.runner:
            raise ValueError("BaseHook.remove called for runner-less hook")

    @classmethod
    def is_enabled_for(cls, project):
        """Determine if this hook should be run for given project.

        On some Pagure instances, some hooks should be run on all projects
        that fulfill certain criteria. It is therefore not necessary to keep
        database objects for them.

        If a hook's backref is set to None, this method is run to determine
        whether the hook should be run or not. These hooks also won't show
        up on settings page, since they can't be turned off.

        :arg project: The project to inspect
        :type project: pagure.lib.model.Project
        :return: True if this hook should be run on the given project,
            False otherwise

        """
        return False


def run_project_hooks(
    session,
    username,
    project,
    hooktype,
    repotype,
    repodir,
    changes,
    is_internal,
    pull_request,
):
    """Function to run the hooks on a project

    This will first call all the plugins with a Runner on the project,
    and afterwards, for a non-repoSpanner repo, run all hooks/<hooktype>.*
    scripts in the repo.

    Args:
        session: Database session
        username (string): The user performing a push
        project (model.Project): The project this call is made for
        repotype (string): Value of lib.query.get_repotypes() indicating
            for which repo the currnet call is
        repodir (string): Directory where a clone of the specified repo is
            located. Do note that this might or might not be a writable
            clone.
        hooktype (string): The type of hook to run: pre-receive, update
            or post-receive
        changes (dict): A dict with keys being the ref to update, values being
            a tuple of (from, to).
        is_internal (bool): Whether this push originated from Pagure internally
        pull_request (model.PullRequest or None): The pull request whose merge
            is initiating this hook run.
    """
    debug = pagure_config.get("HOOK_DEBUG", False)

    # First we run dynamic ACLs
    authbackend = get_git_auth_helper()

    if is_internal and username == "pagure":
        if debug:
            print("This is an internal push, dynamic ACL is pre-approved")
    elif not authbackend.is_dynamic:
        if debug:
            print("Auth backend %s is static-only" % authbackend)
    elif hooktype == "post-receive":
        if debug:
            print("Skipping auth backend during post-receive")
    else:
        if debug:
            print(
                "Checking push request against auth backend %s" % authbackend
            )
        todeny = []
        for refname in changes:
            change = changes[refname]
            authresult = authbackend.check_acl(
                session,
                project,
                username,
                refname,
                is_update=hooktype == "update",
                revfrom=change[0],
                revto=change[1],
                is_internal=is_internal,
                pull_request=pull_request,
                repotype=repotype,
                repodir=repodir,
            )
            if debug:
                print(
                    "Auth result for ref %s: %s"
                    % (refname, "Accepted" if authresult else "Denied")
                )
            if not authresult:
                print(
                    "Denied push for ref '%s' for user '%s'"
                    % (refname, username)
                )
                todeny.append(refname)
        for toremove in todeny:
            del changes[toremove]
        if not changes:
            print("All changes have been rejected")
            sys.exit(1)

    # Now we run the hooks for plugins
    haderrors = False
    for plugin, _ in get_enabled_plugins(project):
        if not plugin.runner:
            if debug:
                print(
                    "Hook plugin %s should be ported to Runner" % plugin.name
                )
        else:
            if debug:
                print("Running plugin %s" % plugin.name)

            try:
                plugin.runner.runhook(
                    session=session,
                    username=username,
                    hooktype=hooktype,
                    project=project,
                    repotype=repotype,
                    repodir=repodir,
                    changes=changes,
                    pull_request=pull_request,
                )
            except Exception as e:
                if hooktype != "pre-receive" or debug:
                    traceback.print_exc()
                else:
                    print(str(e))
                haderrors = True

    if project.is_on_repospanner:
        # We are done. We are not doing any legacy hooks for repoSpanner
        return

    hookdir = os.path.join(repodir, "hooks")
    if not os.path.exists(hookdir):
        return

    stdin = ""
    args = []
    if hooktype == "update":
        refname = six.next(six.iterkeys(changes))
        (revfrom, revto) = changes[refname]
        args = [refname, revfrom, revto]
    else:
        stdin = (
            "\n".join(
                [
                    "%s %s %s" % (changes[refname] + (refname,))
                    for refname in changes
                ]
            )
            + "\n"
        )
    stdin = stdin.encode("utf-8")

    if debug:
        print(
            "Running legacy hooks (if any) with args: %s, stdin: %s"
            % (args, stdin)
        )

    for hook in os.listdir(hookdir):
        # This is for legacy hooks, which create symlinks in the form of
        # "post-receive.$pluginname"
        if hook.startswith(hooktype + "."):
            hookfile = os.path.join(hookdir, hook)

            # By-pass all the old hooks that pagure may have created before
            # moving to the runner architecture
            if hook in pagure.lib.query.ORIGINAL_PAGURE_HOOK:
                continue

            if hook.endswith(".sample"):
                # Ignore the samples that Git inserts
                continue

            # Execute
            print(
                "Running legacy hook %s. "
                "Please ask your admin to port this to the new plugin "
                "format, as the current system will cease functioning "
                "in a future Pagure release" % hook
            )

            # Using subprocess.Popen rather than check_call so that stdin
            # can be passed without having to use a temporary file.
            proc = subprocess.Popen(
                [hookfile] + args, cwd=repodir, stdin=subprocess.PIPE
            )
            proc.communicate(stdin)
            ecode = proc.wait()
            if ecode != 0:
                print("Hook %s errored out" % hook)
                haderrors = True

    if haderrors:
        session.close()
        raise SystemExit(1)


def extract_changes(from_stdin):
    """Extracts a changes dict from either stdin or argv

    Args:
        from_stdin (bool): Whether to use stdin. If false, uses argv
    """
    changes = {}
    if from_stdin:
        for line in sys.stdin:
            (oldrev, newrev, refname) = str(line).strip().split(str(" "), 2)
            if six.PY2:
                refname = refname.decode("utf-8")
            changes[refname] = (oldrev, newrev)
    else:
        (refname, oldrev, newrev) = sys.argv[1:]
        if six.PY2:
            refname = refname.decode("utf-8")
        changes[refname] = (oldrev, newrev)
    return changes


def run_hook_file(hooktype):
    """Runs a specific hook by grabbing the changes and running functions.

    Args:
        hooktype (string): The name of the hook to run: pre-receive, update
            or post-receive
    """
    if pagure_config.get("NOGITHOOKS") or False:
        return

    if hooktype not in ("pre-receive", "update", "post-receive"):
        raise ValueError("Hook type %s not valid" % hooktype)
    changes = extract_changes(from_stdin=hooktype != "update")

    session = pagure.lib.model_base.create_session(pagure_config["DB_URL"])
    if not session:
        raise Exception("Unable to initialize db session")

    pushuser = os.environ.get("GL_USER")
    is_internal = os.environ.get("internal", False) == "yes"
    pull_request = None
    if "pull_request_uid" in os.environ:
        pull_request = pagure.lib.query.get_request_by_uid(
            session, os.environ["pull_request_uid"]
        )

    if pagure_config.get("HOOK_DEBUG", False):
        print("Changes: %s" % changes)

    gitdir = os.path.abspath(os.environ["GIT_DIR"])
    (
        repotype,
        username,
        namespace,
        repo,
    ) = pagure.lib.git.get_repo_info_from_path(gitdir)

    project = pagure.lib.query._get_project(
        session, repo, user=username, namespace=namespace
    )
    if not project:
        raise Exception(
            "Not able to find the project corresponding to: %s - %s - "
            "%s - %s" % (repotype, username, namespace, repo)
        )

    if pagure_config.get("HOOK_DEBUG", False):
        print("Running %s hooks for %s" % (hooktype, project.fullname))
    run_project_hooks(
        session,
        pushuser,
        project,
        hooktype,
        repotype,
        gitdir,
        changes,
        is_internal,
        pull_request,
    )
    session.close()
