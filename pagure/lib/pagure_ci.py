# -*- coding: utf-8 -*-
import os
import flask
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy import create_engine
from pagure.hooks import jenkins_hook
from pagure.lib import model
from pagure import APP

import json
import logging

import requests
import jenkins

os.environ.setdefault('INTEGRATOR_SETTINGS', '/etc/poormanci.conf')


APP.config.from_envvar('INTEGRATOR_SETTINGS', silent=True)
APP.logger.setLevel(logging.INFO)

PAGURE_URL = '{base}api/0/{repo}/pull-request/{pr}/flag'
JENKINS_TRIGGER_URL = '{base}job/{project}/buildWithParameters'


db_session = None

def connect_db():
    global db_session
    engine = create_engine(APP.config['DB_URL'], convert_unicode=True)
    db_session = scoped_session(sessionmaker(autocommit=False,
                                             autoflush=False,
                                             bind=engine))
    model.BASE.query = db_session.query_property()



def process_pr(logger, cfg, pr_id, repo, branch):
    post_data(logger,
              JENKINS_TRIGGER_URL.format(base=cfg.jenkins_url, project=cfg.jenkins_name),
              {'token': cfg.jenkins_token,
               'cause': pr_id,
               'REPO': repo,
               'BRANCH': branch})


def process_build(logger, cfg, build_id):
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
        post_flag(logger, cfg.display_name, cfg.pagure_url, cfg.pagure_token,
                  cfg.pagure_name, pr_id, result, url)
    except KeyError as exc:
        logger.warning('Unknown build status', exc_info=exc)


def post_flag(logger, name, base, token, repo, pr, result, url):
    comment, percent = {
        'SUCCESS': ('Build successful', 100),
        'FAILURE': ('Build failed', 0),
    }[result]
    payload = {
        'username': name,
        'percent': percent,
        'comment': comment,
        'url': url,
    }
    post_data(logger, PAGURE_URL.format(base=base, repo=repo, pr=pr), payload,
              headers={'Authorization': 'token ' + token})


def post_data(logger, *args, **kwargs):
    resp = requests.post(*args, **kwargs)
    logger.debug('Received response status %s', resp.status_code)
    if resp.status_code < 200 or resp.status_code >= 300:
        logger.error('Network request failed: %d: %s', resp.status_code, resp.text)


@APP.route('/hooks/<token>/build-finished', methods=['POST'])
def hook_finished(token):
    try:
        data = json.loads(flask.request.get_data())
        cfg = jenkins_hook.get_configs(data['name'], jenkins_hook.Service.JENKINS)[0]
        build_id = data['build']['number']
        if token != cfg.hook_token:
            raise ValueError('Token mismatch')
    except (TypeError, ValueError, KeyError, jenkins_hook.ConfigNotFound) as exc:
        APP.logger.error('Error processing jenkins notification', exc_info=exc)
        return ('Bad request...\n', 400, {'Content-Type': 'text/plain'})
    APP.logger.info('Received jenkins notification')
    process_build(APP.logger, cfg, build_id)
    return ('', 204)

def cleanup_url(url):
    """Make sure there is trailing slash."""
    return url.rstrip('/') + '/'


@APP.before_request
def before_request():
    if db_session is None:
        connect_db()


@APP.teardown_appcontext
def shutdown_session(exception=None):
    db_session.remove()
