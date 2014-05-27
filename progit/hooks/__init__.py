#-*- coding: utf-8 -*-

"""
 (c) 2014 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

import os

from progit import APP


class BaseHook(object):
    ''' Base class for progit's hooks. '''

    name = None
    form = None

    @classmethod
    def set_up(cls, project):
        ''' Install the generic post-receive hook that allow us to call
        multiple post-receive hooks as set per plugin.
        '''
        repopath = os.path.join(APP.config['GIT_FOLDER'], project.path)
        if project.is_fork:
            repopath = os.path.join(APP.config['FORK_FOLDER'], project.path)

        hook_files = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), 'files')

        # Install the main post-receive file
        postreceive = os.path.join(repopath, 'hooks', 'post-receive')
        if not os.path.exists(postreceive):
            shutil.copyfile(
                os.path.join(hook_files, 'post-receive'),
                postreceive)
            os.chmod(postreceive, 0755)

    @classmethod
    def install(cls, project):
        ''' Method called to install the hook for a project.

        :arg project: a ``progit.model.Project`` object to which the hook
            should be installed

        '''
        pass

    @classmethod
    def remove(cls, project):
        ''' Method called to remove the hook of a project.

        :arg project: a ``progit.model.Project`` object to which the hook
            should be installed

        '''
        pass
