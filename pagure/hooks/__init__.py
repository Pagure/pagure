# -*- coding: utf-8 -*-

"""
 (c) 2014 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

import os
import shutil
import wtforms

from pagure import APP, get_repo_path


class RequiredIf(wtforms.validators.Required):
        """ Wtforms validator setting a field as required if another field
        has a value.
        """

        def __init__(self, fields, *args, **kwargs):
            if isinstance(fields, basestring):
                fields = [fields]
            self.fields = fields
            super(RequiredIf, self).__init__(*args, **kwargs)

        def __call__(self, form, field):
            for fieldname in self.fields:
                nfield = form._fields.get(fieldname)
                if nfield is None:
                    raise Exception(
                        'no field named "%s" in form' % fieldname)
                if bool(nfield.data):
                    super(RequiredIf, self).__call__(form, field)


class BaseHook(object):
    ''' Base class for pagure's hooks. '''

    name = None
    form = None

    @classmethod
    def set_up(cls, project):
        ''' Install the generic post-receive hook that allow us to call
        multiple post-receive hooks as set per plugin.
        '''
        repopath = get_repo_path(project)

        hook_files = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), 'files')

        # Make sure the hooks folder exists
        hookfolder = os.path.join(repopath, 'hooks')
        if not os.path.exists(hookfolder):
            os.makedirs(hookfolder)

        # Install the main post-receive file
        postreceive = os.path.join(hookfolder, 'post-receive')
        if not os.path.exists(postreceive):
            shutil.copyfile(
                os.path.join(hook_files, 'post-receive'),
                postreceive)
            os.chmod(postreceive, 0755)

    @classmethod
    def install(cls, project, dbobj):  # pragma: no cover
        ''' Method called to install the hook for a project.

        :arg project: a ``pagure.model.Project`` object to which the hook
            should be installed
        :arg dbobj: the DB object the hook uses to store the settings
            information.

        '''
        pass

    @classmethod
    def remove(cls, project):  # pragma: no cover
        ''' Method called to remove the hook of a project.

        :arg project: a ``pagure.model.Project`` object to which the hook
            should be installed

        '''
        pass
