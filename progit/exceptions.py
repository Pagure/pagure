# -*- coding: utf-8 -*-

"""
 (c) 2014 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""


class ProgitException(Exception):
    ''' Parent class of all the exception for all Progit specific
    exceptions.
    '''
    pass


class RepoExistsException(ProgitException):
    ''' Exception thrown when trying to create a repository that already
    exists.
    '''
    pass


class FileNotFoundException(ProgitException):
    ''' Exception thrown when trying to create a repository that already
    exists.
    '''
    pass
