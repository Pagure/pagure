# -*- coding: utf-8 -*-

"""
 (c) 2014 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""


class PagureException(Exception):
    ''' Parent class of all the exception for all Pagure specific
    exceptions.
    '''
    pass


class RepoExistsException(PagureException):
    ''' Exception thrown when trying to create a repository that already
    exists.
    '''
    pass


class FileNotFoundException(PagureException):
    ''' Exception thrown when trying to create a repository that already
    exists.
    '''
    pass


class APIError(PagureException):
    ''' Exception raised by the API when something goes wrong. '''

    def __init__(self, status_code, error_code, error=None):
        self.status_code = status_code
        self.error_code = error_code
        self.error = error
