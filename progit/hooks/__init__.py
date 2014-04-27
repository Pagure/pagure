#-*- coding: utf-8 -*-

"""
 (c) 2014 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""


class BaseHook(object):
    ''' Base class for progit's hooks. '''

    name = None
    form = None

    def install():
        ''' Method called to install the hook for a project. '''
        pass

    def remove():
        ''' Method called to remove the hook of a project. '''
        pass

