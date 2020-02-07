# -*- coding: utf-8 -*-

"""
 (c) 2015-2017 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""
from __future__ import print_function, unicode_literals, absolute_import

import abc
import json
import logging
import os
import pkg_resources
import subprocess
import tempfile
from io import open

import werkzeug.utils
from six import with_metaclass
from six.moves import dbm_gnu

import pagure.exceptions
import pagure.lib.model_base
import pagure.lib.query
from pagure.config import config as pagure_config
from pagure.lib import model
from pagure.utils import is_repo_committer, lookup_deploykey


# logging.config.dictConfig(pagure_config.get('LOGGING') or {'version': 1})
_log = logging.getLogger(__name__)

GIT_AUTH_BACKEND_NAME = None
GIT_AUTH_BACKEND_INSTANCE = None


def get_git_auth_helper(backend=None):
    """ Instantiate and return the appropriate git auth helper backend.

    :arg backend: The name of the backend to find on the system (declared via
        the entry_points in setup.py).
        Pagure comes by default with the following backends:
            test_auth, gitolite2, gitolite3
    :type backend: str

    """
    global GIT_AUTH_BACKEND_NAME
    global GIT_AUTH_BACKEND_INSTANCE

    if backend is None:
        backend = pagure_config["GIT_AUTH_BACKEND"]

    if (
        GIT_AUTH_BACKEND_NAME
        and GIT_AUTH_BACKEND_INSTANCE
        and backend == GIT_AUTH_BACKEND_NAME
    ):
        # This got previously instantiated, return that instance to avoid
        # having to instantiate it multiple times as long as the same backend
        # is used.
        return GIT_AUTH_BACKEND_INSTANCE

    _log.info("Looking for backend: %s", backend)
    points = pkg_resources.iter_entry_points("pagure.git_auth.helpers")
    classes = dict([(point.name, point) for point in points])
    _log.debug("Found the following installed helpers %r" % classes)
    if len(classes) == 0:
        _log.debug("Was unable to find any helpers, registering built-in")
        cls = {
            "test_auth": GitAuthTestHelper,
            "gitolite2": Gitolite2Auth,
            "gitolite3": Gitolite3Auth,
            "pagure": PagureGitAuth,
        }[backend]
    else:
        cls = classes[backend].load()
    _log.debug("Returning helper %r from backend key %r" % (cls, backend))

    GIT_AUTH_BACKEND_NAME = backend
    GIT_AUTH_BACKEND_INSTANCE = cls()
    return GIT_AUTH_BACKEND_INSTANCE


class GitAuthHelper(with_metaclass(abc.ABCMeta, object)):
    """ The class to inherit from when creating your own git authentication
    helper.
    """

    is_dynamic = False

    @classmethod
    @abc.abstractmethod
    def generate_acls(self, project, group=None):
        """ This is the method that is called by pagure to generate the
        configuration file.

        :arg project: the project of which to update the ACLs. This argument
            can take three values: ``-1``, ``None`` and a project.
            If project is ``-1``, the configuration should be refreshed for
            *all* projects.
            If project is ``None``, there no specific project to refresh
            but the ssh key of an user was added and updated or a group
            was removed.
            If project is a pagure.lib.model.Project, the configuration of
            this project should be updated.
        :type project: None, int or pagure.lib.model.Project
        :kwarg group: the group to refresh the members of
        :type group: None or pagure.lib.model.PagureGroup

        (This behaviour is based on the workflow of gitolite, if you are
        implementing a different auth backend and need more granularity,
        feel free to let us know.)

        """
        pass

    @classmethod
    @abc.abstractmethod
    def remove_acls(self, session, project):
        """ This is the method that is called by pagure to remove a project
        from the configuration file.

        :arg cls: the current class
        :type: GitAuthHelper
        :arg session: the session with which to connect to the database
        :arg project: the project to remove from the gitolite configuration
            file.
        :type project: pagure.lib.model.Project

        """
        pass

    @classmethod
    # This method can't be marked as abstract, since it's new and that would
    # break backwards compatibility
    def check_acl(cls, session, project, username, refname, **info):
        """ This method is used in Dynamic Git Auth helpers to check acls.

        It is acceptable for implementations to print things, which will be
        returned to the user.

        Please make sure to add a **kwarg in any implementation, even if
        specific keyword arguments are added for the known fields, to make
        sure your implementation remains working if new items are added.

        Args:
            session (sqlalchemy.Session): Database session
            project (model.Project): Project instance push is for
            username (string): The name of the user trying to push
            refname (string): The name of the ref being pushed to
        Kwargs:
            Extra arguments to help in deciding whether to approve or deny a
            push. This may get additional possible values later on, but will
            have at least:
            - is_update (bool): Whether this is being run at the "update" hook
                moment. See the return type notes to see the differences.
            - revfrom (string): The commit hash the update is happening from.
            - revto (string): The commit hash the update is happening to.
            - pull_request (model.PullRequest or None): The PR that is trying
                to be merged.
            - repotype (string): The pagure.lib.query.get_repotypes() value
                for the repo being pushed to.
            - repodir (string): A directory containing the current
                repository, including the new objects to be approved.
                Note that this might or might not be directly writable, and any
                writes might or might not be accepted. ACL checks MUST not make
                any changes in this repository. (added after 5.0.1)
        Returns (bool): Whether to allow this push.
            If is_update is False and the ACL returns False, the entire push
                is aborted. If is_update is True and the ACL returns True, only
                a single ref update is blocked. So if you want to block just a
                single ref from being updated, only return False if is_update
                is True.
        """
        raise NotImplementedError(
            "check_acl on static Git Auth Backend called"
        )


def _read_file(filename):
    """ Reads the specified file and return its content.
    Returns None if it could not read the file for any reason.
    """
    if not os.path.exists(filename):
        _log.info("Could not find file: %s", filename)
    else:
        with open(filename) as stream:
            return stream.read()


class Gitolite2Auth(GitAuthHelper):
    """ A gitolite 2 authentication module. """

    @classmethod
    def _process_project(cls, project, config, global_pr_only):
        """ Generate the gitolite configuration for the specified project.

        :arg project: the project to generate the configuration for
        :type project: pagure.lib.model.Project
        :arg config: a list containing the different lines of the
            configuration file
        :type config: list
        :arg groups: a dictionary containing the group name as key and the
            users member of the group as values
        :type groups: dict(str: list)
        :arg global_pr_only: boolean on whether the pagure instance enforces
            the PR workflow only or not
        :type global_pr_only: bool
        :return: the updated config
        :return type: list

        """
        _log.debug("    Processing project: %s", project.fullname)

        # Check if the project or the pagure instance enforce the PR only
        # development model.
        pr_only = project.settings.get("pull_request_access_only", False)

        repos_to_create = ["repos"]
        if pagure_config.get("ENABLE_DOCS", True):
            repos_to_create.append("docs/")
        if pagure_config.get("ENABLE_TICKETS", True):
            repos_to_create.append("tickets/")
        # no setting yet to disable pull-requests
        repos_to_create.append("requests/")
        for repos in repos_to_create:
            if repos == "repos":
                # Do not grant access to project enforcing the PR model
                if pr_only or (global_pr_only and not project.is_fork):
                    continue
                repos = ""

            config.append("repo %s%s" % (repos, project.fullname))
            if not project.private and repos not in ["tickets/", "requests/"]:
                config.append("  R   = @all")
            if project.committer_groups:
                config.append(
                    "  RW+ = @%s"
                    % " @".join(
                        [
                            group.group_name
                            for group in project.committer_groups
                        ]
                    )
                )
            config.append("  RW+ = %s" % project.user.user)
            for user in project.committers:
                # This should never be the case (that the project.user
                # is in the committers) but better safe than sorry
                if user.user != project.user.user:
                    config.append("  RW+ = %s" % user.user)
            for deploykey in project.deploykeys:
                access = "R"
                if deploykey.pushaccess:
                    access = "RW+"
                # Note: the replace of / with _ is because gitolite
                # users can't contain a /. At first, this might look
                # like deploy keys in a project called
                # $namespace_$project would give access to the repos of
                # a project $namespace/$project or vica versa, however
                # this is NOT the case because we add the deploykey.id
                # to the end of the deploykey name, which means it is
                # unique. The project name is solely there to make it
                # easier to determine what project created the deploykey
                # for admins.
                config.append(
                    "  %s = deploykey_%s_%s"
                    % (
                        access,
                        werkzeug.utils.secure_filename(project.fullname),
                        deploykey.id,
                    )
                )
            config.append("")

        return config

    @classmethod
    def _clean_current_config(cls, current_config, project):
        """ Remove the specified project from the current configuration file

        :arg current_config: the content of the current/actual gitolite
            configuration file read from the disk
        :type current_config: list
        :arg project: the project to update in the configuration file
        :type project: pagure.lib.model.Project

        """
        keys = [
            "repo %s%s" % (repos, project.fullname)
            for repos in ["", "docs/", "tickets/", "requests/"]
        ]

        keep = True
        config = []
        for line in current_config:
            line = line.rstrip()

            if line in keys:
                keep = False
                continue

            if keep is False and line == "":
                keep = True

            if keep:
                config.append(line)

        return config

    @classmethod
    def _clean_groups(cls, config, group=None):
        """ Removes the groups in the given configuration file.

        :arg config: the current configuration
        :type config: list
        :kwarg group: the group to refresh the members of
        :type group: None or pagure.lib.model.PagureGroup
        :return: the configuration without the groups
        :return type: list

        """

        if group is None:
            output = [
                row.rstrip()
                for row in config
                if not row.startswith("@") and row.strip() != "# end of groups"
            ]
        else:
            end_grp = None
            seen = False
            output = []
            for idx, row in enumerate(config):
                if end_grp is None and row.startswith("repo "):
                    end_grp = idx

                if row.startswith("@%s " % group.group_name):
                    seen = True
                    row = "@%s  = %s" % (
                        group.group_name,
                        " ".join(
                            sorted([user.username for user in group.users])
                        ),
                    )
                output.append(row)

            if not seen:
                row = "@%s  = %s" % (
                    group.group_name,
                    " ".join(sorted([user.username for user in group.users])),
                )
                output.insert(end_grp, "")
                output.insert(end_grp, row)

        return output

    @classmethod
    def _generate_groups_config(cls, session):
        """ Generate the gitolite configuration for all of the groups.

        :arg session: the session with which to connect to the database
        :return: the gitolite configuration for the groups
        :return type: list

        """
        query = session.query(model.PagureGroup).order_by(
            model.PagureGroup.group_name
        )

        groups = {}
        for grp in query.all():
            groups[grp.group_name] = [user.username for user in grp.users]

        return groups

    @classmethod
    def _get_current_config(cls, configfile, preconfig=None, postconfig=None):
        """ Load the current gitolite configuration file from the disk.

        :arg configfile: the name of the configuration file to load
        :type configfile: str
        :kwarg preconf: the content of the file to include at the top of the
            gitolite configuration file, used here to determine that a part of
            the configuration file should be cleaned at the top.
        :type preconf: None or str
        :kwarg postconf: the content of the file to include at the bottom of
            the gitolite configuration file, used here to determine that a part
            of the configuration file should be cleaned at the bottom.
        :type postconf: None or str

        """
        _log.info("Reading in the current configuration: %s", configfile)
        with open(configfile) as stream:
            current_config = [line.rstrip() for line in stream]
        if current_config and current_config[-1] == "# end of body":
            current_config = current_config[:-1]

        if preconfig:
            idx = None
            for idx, row in enumerate(current_config):
                if row.strip() == "# end of header":
                    break
            if idx is not None:
                idx = idx + 1
                _log.info("Removing the first %s lines", idx)
                current_config = current_config[idx:]

        if postconfig:
            idx = None
            for idx, row in enumerate(current_config):
                if row.strip() == "# end of body":
                    break
            if idx is not None:
                _log.info(
                    "Keeping the first %s lines out of %s",
                    idx,
                    len(current_config),
                )
                current_config = current_config[:idx]

        return current_config

    @classmethod
    def write_gitolite_acls(
        cls,
        session,
        configfile,
        project,
        preconf=None,
        postconf=None,
        group=None,
    ):
        """ Generate the configuration file for gitolite for all projects
        on the forge.

        :arg cls: the current class
        :type: Gitolite2Auth
        :arg session: a session to connect to the database with
        :arg configfile: the name of the configuration file to generate/write
        :type configfile: str
        :arg project: the project to update in the gitolite configuration
            file. It can be of three types/values.
            If it is ``-1`` or if the file does not exist on disk, the
            entire gitolite configuration will be re-generated.
            If it is ``None``, the gitolite configuration will have its
            groups information updated but not the projects and will be
            re-compiled.
            If it is a ``pagure.lib.model.Project``, the gitolite
            configuration will be updated for just this project.
        :type project: None, int or spagure.lib.model.Project
        :kwarg preconf: a file to include at the top of the configuration
            file
        :type preconf: None or str
        :kwarg postconf: a file to include at the bottom of the
            configuration file
        :type postconf: None or str
        :kwarg group: the group to refresh the members of
        :type group: None or pagure.lib.model.PagureGroup

        """
        _log.info("Write down the gitolite configuration file")

        preconfig = None
        if preconf:
            _log.info(
                "Loading the file to include at the top of the generated one"
            )
            preconfig = _read_file(preconf)

        postconfig = None
        if postconf:
            _log.info(
                "Loading the file to include at the end of the generated one"
            )
            postconfig = _read_file(postconf)

        global_pr_only = pagure_config.get("PR_ONLY", False)
        config = []
        groups = {}
        if group is None:
            groups = cls._generate_groups_config(session)

        if project == -1 or not os.path.exists(configfile):
            _log.info("Refreshing the configuration for all projects")
            query = session.query(model.Project).order_by(model.Project.id)
            for project in query.all():
                config = cls._process_project(project, config, global_pr_only)
        elif project:
            _log.info("Refreshing the configuration for one project")
            config = cls._process_project(project, config, global_pr_only)

            current_config = cls._get_current_config(
                configfile, preconfig, postconfig
            )

            current_config = cls._clean_current_config(current_config, project)

            config = current_config + config

        if config:
            _log.info("Cleaning the group %s from the loaded config", group)
            config = cls._clean_groups(config, group=group)

        else:
            current_config = cls._get_current_config(
                configfile, preconfig, postconfig
            )

            _log.info("Cleaning the group %s from the config on disk", group)
            config = cls._clean_groups(current_config, group=group)

        if not config:
            return

        _log.info("Writing the configuration to: %s", configfile)
        with open(configfile, "w", encoding="utf-8") as stream:
            if preconfig:
                stream.write(preconfig + "\n")
                stream.write("# end of header\n")

            if groups:
                for key in sorted(groups):
                    stream.write("@%s  = %s\n" % (key, " ".join(groups[key])))
                stream.write("# end of groups\n\n")

            prev = None
            for row in config:
                if prev is None:
                    prev = row
                if prev == row == "":
                    continue
                stream.write(row + "\n")
                prev = row

            stream.write("# end of body\n")

            if postconfig:
                stream.write(postconfig + "\n")

    @classmethod
    def _remove_from_gitolite_cache(cls, cache_file, project):
        """Removes project from gitolite cache file (gl-conf.cache)

        Gitolite has no notion of "deleting" a project and it can only
        add values to gl-conf.cache. Therefore we must manually wipe all
        entries related to a project when deleting it.
        If this method is not executed and if someone creates a project
        with the same fullname again then its `gl-conf` file won't get
        created (see link to commit below) and any subsequent invocation of
        `gitolite trigger POST_COMPILE` will fail, thus preventing creation
        of new repos/forks at the whole pagure instance.

        See https://github.com/sitaramc/gitolite/commit/41b7885b77c
        (later reverted upstream, but still used in most Pagure deployments)

        :arg cls: the current class
        :type: Gitolite2Auth
        :arg cache_file: path to the cache file
        :type cache_file: str
        :arg project: the project to remove from gitolite cache file
        :type project: pagure.lib.model.Project
        """
        _log.info("Remove project from the gitolite cache file")
        cf = None
        try:
            # unfortunately dbm_gnu.open isn't a context manager in Python 2 :(
            cf = dbm_gnu.open(cache_file, "ws")
            for repo in ["", "docs/", "tickets/", "requests/"]:
                to_remove = repo + project.fullname
                if to_remove.encode("ascii") in cf:
                    del cf[to_remove]
        except dbm_gnu.error as e:
            msg = "Failed to remove project from gitolite cache: {msg}".format(
                msg=e[1]
            )
            raise pagure.exceptions.PagureException(msg)
        finally:
            if cf:
                cf.close()

    @classmethod
    def remove_acls(cls, session, project):
        """ Remove a project from the configuration file for gitolite.

        :arg cls: the current class
        :type: Gitolite2Auth
        :arg session: the session with which to connect to the database
        :arg project: the project to remove from the gitolite configuration
            file.
        :type project: pagure.lib.model.Project

        """
        _log.info("Remove project from the gitolite configuration file")

        if not project:
            raise RuntimeError("Project undefined")

        configfile = pagure_config["GITOLITE_CONFIG"]
        preconf = pagure_config.get("GITOLITE_PRE_CONFIG") or None
        postconf = pagure_config.get("GITOLITE_POST_CONFIG") or None

        if not os.path.exists(configfile):
            _log.info(
                "Not configuration file found at: %s... bailing" % configfile
            )
            return

        preconfig = None
        if preconf:
            _log.info(
                "Loading the file to include at the top of the generated one"
            )
            preconfig = _read_file(preconf)

        postconfig = None
        if postconf:
            _log.info(
                "Loading the file to include at the end of the generated one"
            )
            postconfig = _read_file(postconf)

        config = []
        groups = cls._generate_groups_config(session)

        _log.info("Removing the project from the configuration")

        current_config = cls._get_current_config(
            configfile, preconfig, postconfig
        )

        current_config = cls._clean_current_config(current_config, project)

        config = current_config + config

        if config:
            _log.info("Cleaning the groups from the loaded config")
            config = cls._clean_groups(config)

        else:
            current_config = cls._get_current_config(
                configfile, preconfig, postconfig
            )

            _log.info("Cleaning the groups from the config on disk")
            config = cls._clean_groups(config)

        if not config:
            return

        _log.info("Writing the configuration to: %s", configfile)
        with open(configfile, "w", encoding="utf-8") as stream:
            if preconfig:
                stream.write(preconfig + "\n")
                stream.write("# end of header\n")

            if groups:
                for key in sorted(groups):
                    stream.write("@%s  = %s\n" % (key, " ".join(groups[key])))
                stream.write("# end of groups\n\n")

            prev = None
            for row in config:
                if prev is None:
                    prev = row
                if prev == row == "":
                    continue
                stream.write(row + "\n")
                prev = row

            stream.write("# end of body\n")

            if postconfig:
                stream.write(postconfig + "\n")

        gl_cache_path = os.path.join(
            os.path.dirname(configfile), "..", "gl-conf.cache"
        )
        if os.path.exists(gl_cache_path):
            cls._remove_from_gitolite_cache(gl_cache_path, project)

    @staticmethod
    def _get_gitolite_command():
        """ Return the gitolite command to run based on the info in the
        configuration file.
        """
        _log.info("Compiling the gitolite configuration")
        gitolite_folder = pagure_config.get("GITOLITE_HOME", None)
        if gitolite_folder:
            cmd = "GL_RC=%s GL_BINDIR=%s gl-compile-conf" % (
                pagure_config.get("GL_RC"),
                pagure_config.get("GL_BINDIR"),
            )
            _log.debug("Command: %s", cmd)
            return cmd

    @classmethod
    def _repos_from_lines(cls, lines):
        """ Return list of strings representing complete repo entries from list
        of lines as returned by _process_project.
        """
        repos = []
        for l in lines:
            if l.startswith("repo "):
                repos.append([l])
            else:
                repos[-1].append(l)
        for i, repo_lines in enumerate(repos):
            repos[i] = "\n".join(repo_lines)
        return repos

    @classmethod
    def _run_gitolite_cmd(cls, cmd):
        """ Run gitolite command as subprocess, raise PagureException
        if it fails.
        """
        if cmd:
            proc = subprocess.Popen(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=pagure_config["GITOLITE_HOME"],
            )
            stdout, stderr = proc.communicate()
            if proc.returncode != 0:
                error_msg = (
                    'The command "{0}" failed with'
                    '\n\n  out: "{1}\n\n  err:"{2}"'.format(
                        cmd, stdout, stderr
                    )
                )
                raise pagure.exceptions.PagureException(error_msg)

    @classmethod
    def generate_acls(cls, project, group=None):
        """ Generate the gitolite configuration file for all repos

        :arg project: the project to update in the gitolite configuration
            file. It can be of three types/values.
            If it is ``-1`` or if the file does not exist on disk, the
            entire gitolite configuration will be re-generated.
            If it is ``None``, the gitolite configuration will not be
            changed but will be re-compiled.
            If it is a ``pagure.lib.model.Project``, the gitolite
            configuration will be updated for just this project.
        :type project: None, int or pagure.lib.model.Project
        :kwarg group: the group to refresh the members of
        :type group: None or pagure.lib.model.PagureGroup

        """
        _log.info("Refresh gitolite configuration")

        if project is not None or group is not None:
            session = pagure.lib.model_base.create_session(
                pagure_config["DB_URL"]
            )
            cls.write_gitolite_acls(
                session,
                project=project,
                configfile=pagure_config["GITOLITE_CONFIG"],
                preconf=pagure_config.get("GITOLITE_PRE_CONFIG") or None,
                postconf=pagure_config.get("GITOLITE_POST_CONFIG") or None,
                group=group,
            )
            session.remove()

        if (
            not group
            and project not in [None, -1]
            and hasattr(cls, "_individual_repos_command")
            and pagure_config.get("GITOLITE_HAS_COMPILE_1", False)
        ):
            # optimization for adding single repo - we don't want to recompile
            # whole gitolite.conf
            repos_config = []
            cls._process_project(
                project, repos_config, pagure_config.get("PR_ONLY", False)
            )
            # repos_config will contain lines for repo itself as well as
            # docs, requests, tickets; compile-1 only accepts one repo,
            # so we have to run it separately for all of them
            for repo in cls._repos_from_lines(repos_config):
                repopath = repo.splitlines()[0][len("repo ") :].strip()
                repotype = repopath.split("/")[0]
                if (
                    repotype == "docs" and not pagure_config.get("ENABLE_DOCS")
                ) or (
                    repotype == "tickets"
                    and not pagure_config.get("ENABLE_TICKETS")
                ):
                    continue
                with tempfile.NamedTemporaryFile() as f:
                    f.write(repo)
                    f.flush()
                    cmd = cls._individual_repos_command(f.name)
                    cls._run_gitolite_cmd(cmd)
        else:
            cmd = cls._get_gitolite_command()
            cls._run_gitolite_cmd(cmd)


class Gitolite3Auth(Gitolite2Auth):
    """ A gitolite 3 authentication module. """

    @staticmethod
    def _individual_repos_command(config_file):
        _log.info(
            "Compiling gitolite configuration %s for single repository",
            config_file,
        )
        gitolite_folder = pagure_config.get("GITOLITE_HOME", None)
        if gitolite_folder:
            cmd = "HOME=%s gitolite compile-1 %s" % (
                gitolite_folder,
                config_file,
            )
            _log.debug("Command: %s", cmd)
            return cmd

    @staticmethod
    def _get_gitolite_command():
        """ Return the gitolite command to run based on the info in the
        configuration file.
        """
        _log.info("Compiling the gitolite configuration")
        gitolite_folder = pagure_config.get("GITOLITE_HOME", None)
        if gitolite_folder:
            cmd = (
                "HOME=%s gitolite compile && HOME=%s gitolite trigger "
                "POST_COMPILE" % (gitolite_folder, gitolite_folder)
            )
            _log.debug("Command: %s", cmd)
            return cmd

    @classmethod
    def post_compile_only(cls):
        """ This method runs `gitolite trigger POST_COMPILE` without touching
        any other gitolite configuration. Most importantly, this will process
        SSH keys used by gitolite.
        """
        _log.info("Triggering gitolite POST_COMPILE")
        gitolite_folder = pagure_config.get("GITOLITE_HOME", None)
        if gitolite_folder:
            cmd = "HOME=%s gitolite trigger POST_COMPILE" % gitolite_folder
            _log.debug("Command: %s", cmd)
            cls._run_gitolite_cmd(cmd)


class PagureGitAuth(GitAuthHelper):
    """ Standard Pagure git auth implementation. """

    is_dynamic = True

    @classmethod
    def generate_acls(self, project, group=None):
        """ This function is required but not used. """
        pass

    @classmethod
    def remove_acls(self, session, project):
        """ This function is required but not used. """
        pass

    def info(self, msg):
        """ Function that prints info about decisions to clients.

        This is a function to make it possible to override for test suite. """
        print(msg)

    def check_acl(
        self,
        session,
        project,
        username,
        refname,
        pull_request,
        repotype,
        is_internal,
        **info
    ):
        if is_internal:
            self.info("Internal push allowed")
            return True

        # Check whether a PR is required for this repo or in general
        global_pr_only = pagure_config.get("PR_ONLY", False)
        pr_only = project.settings.get("pull_request_access_only", False)
        if repotype == "main":
            if (
                pr_only or (global_pr_only and not project.is_fork)
            ) and not pull_request:
                self.info("Pull request required")
                return False

        # Determine whether the current user is allowed to push
        is_committer = is_repo_committer(project, username, session)
        deploykey = lookup_deploykey(project, username)
        if deploykey is not None:
            self.info("Deploykey used. Push access: %s" % deploykey.pushaccess)
            is_committer = deploykey.pushaccess
        self.info("Has commit access: %s" % is_committer)

        return is_committer


class GitAuthTestHelper(GitAuthHelper):
    """ Simple test auth module to check the auth customization system. """

    is_dynamic = True

    @classmethod
    def generate_acls(cls, project, group=None):
        """ Print a statement when called, useful for debugging, only.

        :arg project: this variable is just printed out but not used
            in any real place.
        :type project: None, int or spagure.lib.model.Project
        :kwarg group: the group to refresh the members of
        :type group: None or pagure.lib.model.PagureGroup

        """
        out = (
            "Called GitAuthTestHelper.generate_acls() "
            "with args: project=%s, group=%s" % (project, group)
        )
        print(out)
        return out

    @classmethod
    def remove_acls(cls, session, project):
        """ Print a statement about which a project would be removed from
        the configuration file for gitolite.

        :arg cls: the current class
        :type: GitAuthHelper
        :arg session: the session with which to connect to the database
        :arg project: the project to remove from the gitolite configuration
            file.
        :type project: pagure.lib.model.Project

        """

        out = (
            "Called GitAuthTestHelper.remove_acls() "
            "with args: project=%s" % (project.fullname)
        )
        print(out)
        return out

    @classmethod
    def check_acl(
        cls, session, project, username, refname, pull_request, **info
    ):
        testfile = pagure_config.get("TEST_AUTH_STATUS", None)
        if not testfile or not os.path.exists(testfile):
            # If we are not configured, we will assume allowed
            return True

        with open(testfile, "r") as statusfile:
            status = json.loads(statusfile.read())

        if status is True or status is False:
            return status

        # Other option would be a dict with ref->allow
        # (with allow True, pronly), missing means False)
        if refname not in status:
            print("ref '%s' not in status" % refname)
            return False
        elif status[refname] is True:
            return True
        elif status[refname] == "pronly":
            return pull_request is not None
