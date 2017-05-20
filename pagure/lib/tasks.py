# -*- coding: utf-8 -*-

"""
 (c) 2017 - Copyright Red Hat Inc

 Authors:
   Patrick Uiterwijk <puiterwijk@redhat.com>

"""

from celery import Celery
from celery.result import AsyncResult

import pagure
import pagure.lib


conn = Celery('tasks',
              broker='redis://%s' % pagure.APP.config['REDIS_HOST'],
              backend='redis://%s' % pagure.APP.config['REDIS_HOST'])


def get_result(uuid):
    return AsyncResult(uuid, conn.backend)


def ret(endpoint, **kwargs):
    toret = {'endpoint': endpoint}
    toret.update(kwargs)
    return toret


@conn.task
def generate_gitolite_acls():
    # TODO: Implement gitolite acl stuff
    return 'TODO'


@conn.task
def create_project(namespace, name, add_readme, ignore_existing_repo):
    # TODO: Implement creation (see pagure.lib.new_project after return)
    generate_gitolite_acls.delay()
    return ret('view_repo', repo=name, namespace=namespace)
