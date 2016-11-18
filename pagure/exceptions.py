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

    def __init__(self, status_code, error_code, error=None, errors=None):
        self.status_code = status_code
        self.error_code = error_code
        self.error = error
        self.errors = errors


class BranchNotFoundException(PagureException):
    ''' Exception thrown when trying to use a branch that could not be
    found in a repository.
    '''
    pass


class PagureEvException(PagureException):
    ''' Exceptions used in the pagure_stream_server.
    '''
    pass


class GitConflictsException(PagureException):
    ''' Exception used when trying to pull on a repo and that leads to
    conflicts.
    '''
    pass


class HookInactiveException(PagureException):
    ''' Exception raised when the hook is inactive. '''
    pass


class NoCorrespondingPR(PagureException):
    ''' Exception raised when no pull-request is found with the given
    information. '''
    pass


class InvalidObjectException(PagureException):
    ''' Exception raised when a given object is not what was expected. '''
    pass
