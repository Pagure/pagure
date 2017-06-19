# -*- coding: utf-8 -*-

"""
 (c) 2015-2017 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""
from __future__ import print_function

import abc
import logging
import os
import pkg_resources
import subprocess

import werkzeug

import pagure
import pagure.exceptions
from pagure import APP
from pagure.lib import model

logging.config.dictConfig(APP.config.get('LOGGING') or {'version': 1})
_log = logging.getLogger(__name__)


def get_git_auth_helper(backend, *args, **kwargs):
    """ Instantiate and return the appropriate git auth helper backend.

    :arg backend: The name of the backend to find on the system (declared via
        the entry_points in setup.py).
        Pagure comes by default with the following backends:
            test_auth, gitolite2, gitolite3
    :type backend: str

    """
    points = pkg_resources.iter_entry_points('pagure.git_auth.helpers')
    classes = dict([(point.name, point.load()) for point in points])
    _log.debug("Found the following installed helpers %r" % classes)
    cls = classes[backend]
    _log.debug("Instantiating helper %r from backend key %r" % (cls, backend))
    return cls(*args, **kwargs)


class GitAuthHelper(object):
    """ The class to inherit from when creating your own git authentication
    helper.
    """

    __metaclass__ = abc.ABCMeta

    @classmethod
    @abc.abstractmethod
    def generate_acls(self):
        """ This is the method that is called by pagure to generate the
        configuration file.
        """
        pass


def _read_file(filename):
    """ Reads the specified file and return its content.
    Returns None if it could not read the file for any reason.
    """
    if not os.path.exists(filename):
        _log.info('Could not find file: %s', filename)
    else:
        with open(filename) as stream:
            return stream.read()


class Gitolite2Auth(GitAuthHelper):
    """ A gitolite 2 authentication module. """

    @classmethod
    def write_gitolite_acls(
            cls, session, configfile, preconf=None, postconf=None):
        ''' Generate the configuration file for gitolite for all projects
        on the forge.

        :arg cls: the current class
        :type: Gitolite2Auth
        :arg session: a session to connect to the database with
        :arg configfile: the name of the configuration file to generate/write
        :type configfile: str
        :kwarg preconf: a file to include at the top of the configuration
            file
        :type preconf: None or str
        :kwarg postconf: a file to include at the bottom of the
            configuration file
        :type postconf: None or str

        '''
        _log.info('Write down the gitolite configuration file')

        preconfig = None
        if preconf:
            _log.info(
                'Loading the file to include at the top of the generated one')
            preconfig = _read_file(preconf)

        postconfig = None
        if postconf:
            _log.info(
                'Loading the file to include at the end of the generated one')
            postconfig = _read_file(postconf)

        global_pr_only = pagure.APP.config.get('PR_ONLY', False)
        config = []
        groups = {}
        query = session.query(
            model.Project
        ).order_by(
            model.Project.id
        )
        for project in query.all():
            _log.debug('    Processing project: %s', project.fullname)
            for group in project.committer_groups:
                if group.group_name not in groups:
                    groups[group.group_name] = [
                        user.username for user in group.users]

            # Check if the project or the pagure instance enforce the PR only
            # development model.
            pr_only = project.settings.get('pull_request_access_only', False)

            for repos in ['repos', 'docs/', 'tickets/', 'requests/']:
                if repos == 'repos':
                    # Do not grant access to project enforcing the PR model
                    if pr_only or (global_pr_only and not project.is_fork):
                        continue
                    repos = ''

                config.append('repo %s%s' % (repos, project.fullname))
                if repos not in ['tickets/', 'requests/']:
                    config.append('  R   = @all')
                if project.committer_groups:
                    config.append('  RW+ = @%s' % ' @'.join(
                        [
                            group.group_name
                            for group in project.committer_groups
                        ]
                    ))
                config.append('  RW+ = %s' % project.user.user)
                for user in project.committers:
                    # This should never be the case (that the project.user
                    # is in the committers) but better safe than sorry
                    if user.user != project.user.user:
                        config.append('  RW+ = %s' % user.user)
                for deploykey in project.deploykeys:
                    access = 'R'
                    if deploykey.pushaccess:
                        access = 'RW+'
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
                    config.append('  %s = deploykey_%s_%s' %
                                  (access,
                                   werkzeug.secure_filename(project.fullname),
                                   deploykey.id))
                config.append('')

        with open(configfile, 'w') as stream:
            if preconfig:
                stream.write(preconfig + '\n')

            for key, users in groups.iteritems():
                stream.write('@%s   = %s\n' % (key, ' '.join(users)))
            stream.write('\n')

            for row in config:
                stream.write(row + '\n')

            if postconfig:
                stream.write(postconfig + '\n')

    @staticmethod
    def _get_gitolite_command():
        """ Return the gitolite command to run based on the info in the
        configuration file.
        """
        _log.info('Compiling the gitolite configuration')
        gitolite_folder = pagure.APP.config.get('GITOLITE_HOME', None)
        if gitolite_folder:
            cmd = 'GL_RC=%s GL_BINDIR=%s gl-compile-conf' % (
                pagure.APP.config.get('GL_RC'),
                pagure.APP.config.get('GL_BINDIR')
            )
            _log.debug('Command: %s', cmd)
            return cmd

    @classmethod
    def generate_acls(cls):
        """ Generate the gitolite configuration file for all repos
        """
        _log.info('Refresh gitolite configuration')
        cls.write_gitolite_acls(
            pagure.SESSION,
            pagure.APP.config['GITOLITE_CONFIG'],
            preconf=pagure.APP.config.get('GITOLITE_PRE_CONFIG') or None,
            postconf=pagure.APP.config.get('GITOLITE_POST_CONFIG') or None
        )

        cmd = cls._get_gitolite_command()
        if cmd:
            proc = subprocess.Popen(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=pagure.APP.config['GITOLITE_HOME']
            )
            stdout, stderr = proc.communicate()
            if proc.returncode != 0:
                error_msg = (
                    'The command "{0}" failed with'
                    '\n\n  out: "{1}\n\n  err:"{2}"'
                    .format(' '.join(cmd), stdout, stderr))
                raise pagure.exceptions.PagureException(error_msg)


class Gitolite3Auth(Gitolite2Auth):
    """ A gitolite 3 authentication module. """

    @staticmethod
    def _get_gitolite_command():
        """ Return the gitolite command to run based on the info in the
        configuration file.
        """
        _log.info('Compiling the gitolite configuration')
        gitolite_folder = pagure.APP.config.get('GITOLITE_HOME', None)
        if gitolite_folder:
            cmd = 'HOME=%s gitolite compile && HOME=%s gitolite trigger '\
                'POST_COMPILE' % (gitolite_folder, gitolite_folder)
            _log.debug('Command: %s', cmd)
            return cmd


class GitAuthTestHelper(GitAuthHelper):
    """ Simple test auth module to check the auth customization system. """

    @classmethod
    def generate_acls(cls):
        """ Print a statement when called, useful for debugging, only. """
        out = 'Called GitAuthTestHelper.generate_acls()'
        print(out)
        return out
