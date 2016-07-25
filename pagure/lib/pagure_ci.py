# -*- coding: utf-8 -*-
import os
import flask
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import create_engine

from pagure.hooks import jenkins_hook
import pagure.lib
from pagure.lib import model
from pagure import APP, SESSION
import pagure.exceptions

import json
import logging

import requests
import jenkins

APP.logger.setLevel(logging.INFO)

PAGURE_URL = '{base}api/0/{repo}/pull-request/{pr}/flag'
JENKINS_TRIGGER_URL = '{base}job/{project}/buildWithParameters'


class HookInactive(Exception):
    pass


def process_pr(logger, cfg, pr_id, repo, branch):
    if cfg.active:
        post_data(logger,
                  JENKINS_TRIGGER_URL.format(
                      base=cfg.jenkins_url, project=cfg.jenkins_name),
                  {'token': cfg.jenkins_token,
                   'cause': pr_id,
                   'REPO': repo,
                   'BRANCH': branch})
    else:
        raise HookInactive(cfg.pagure_name)


def process_build(logger, cfg, build_id):
    if cfg.active:
        #  Get details from Jenkins
        jenk = jenkins.Jenkins(cfg.jenkins_url)
        build_info = jenk.get_build_info(cfg.jenkins_name, build_id)
        result = build_info['result']
        url = build_info['url']

        pr_id = None

        for action in build_info['actions']:
            for cause in action.get('causes', []):
                try:
                    pr_id = int(cause['note'])
                except (KeyError, ValueError):
                    continue

        if not pr_id:
            logger.info('Not a PR check')
            return

        # Comment in Pagure
        logger.info('Updating %s PR %d: %s', cfg.pagure_name, pr_id, result)
        try:
            pagure_ci_flag(logger,
                        username=cfg.display_name,
                        repo=cfg.pagure_name,
                        requestid=pr_id,
                        result=result,
                        url=url)

        except KeyError as exc:
            logger.warning('Unknown build status', exc_info=exc)
    else:
        raise HookInactive(cfg.pagure_name)


def post_data(logger, *args, **kwargs):
    resp = requests.post(*args, **kwargs)
    logger.debug('Received response status %s', resp.status_code)
    if resp.status_code < 200 or resp.status_code >= 300:
        logger.error('Network request failed: %d: %s',
                     resp.status_code, resp.text)


def pagure_ci_flag(logger, repo, username, url, result, requestid):

    comment, percent = {
        'SUCCESS': ('Build successful', 100),
        'FAILURE': ('Build failed', 0),
    }[result]

    repo = pagure.lib.get_project(SESSION, repo, user=None)
    output = {}

    if repo is None:
        raise pagure.exceptions.FileNotFoundException('Repo not found')

    request = pagure.lib.search_pull_requests(
        SESSION, project_id=repo.id, requestid=requestid)

    if not request:
        raise pagure.exceptions.FileNotFoundException('Request not found')

    try:
        message = pagure.lib.add_pull_request_flag(
            SESSION,
            request=request,
            username=username,
            percent=percent,
            comment=comment,
            url=url,
            uid=None,
            user=repo.user.username,
            requestfolder=APP.config['REQUESTS_FOLDER'],
        )
        SESSION.commit()
        logger.debug('Received response status: %s', message)
        output['message'] = message

    except SQLAlchemyError as err:  # pragma: no cover
        logger.exception(err)
        SESSION.rollback()
