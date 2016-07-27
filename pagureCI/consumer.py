# -*- coding: utf-8 -*-
import fedmsg.consumers
from pagure.hooks import jenkins_hook
import pagure.lib
from pagure.lib import pagure_ci
from pagure.lib.model import BASE, Project, User
from pagure import APP, SESSION
import pagure.exceptions
PAGURE_MAIN_REPO = '{base}{name}.git'
PAGURE_FORK_REPO = '{base}forks/{user}/{name}.git'


class Integrator(fedmsg.consumers.FedmsgConsumer):
    ''' Integrates Jenkins with Pagure. '''
    topic = [
        'io.pagure.prod.pagure.pull-request.comment.added',
        'io.pagure.prod.pagure.pull-request.new',
        'org.fedoraproject.prod.jenkins.build',
    ]

    config_key = 'integrator.enabled'


    def __init__(self, hub):
        super(Integrator, self).__init__(hub)

    def consume(self, msg):
        ''' Pagure CI consumer which consumes message from
        fedmsg and triggers Jenkins build.
        '''
        topic, msg = msg['topic'], msg['body']
        self.log.info("Received %r, %r", topic, msg.get('msg_id', None))
        msg = msg['msg']
        try:
            if topic.endswith('.pull-request.comment.added'):
                if is_rebase(msg):
                    self.trigger_build(msg)
            elif topic.endswith('.pull-request.new'):
                self.trigger_build(msg)
            else:
                self.process_build(msg)
        except jenkins_hook.ConfigNotFound as exc:
            self.log.info('Unconfigured project %r', str(exc))
        except pagure.exceptions.HookInactiveException as exc:
            self.log.info('Hook Inactive for project %r', str(exc))

    def trigger_build(self, msg):
        ''' Triggers or requests to start a build in Jenkins. '''
        pr_id = msg['pullrequest']['id']
        project = msg['pullrequest']['project']['name']
        branch = msg['pullrequest']['branch_from']

        for cfg in jenkins_hook.get_configs(project, jenkins_hook.Service.PAGURE):
            repo = msg['pullrequest'].get('remote_git') or get_repo(cfg, msg)
            self.log.info("Trigger on %s PR #%s from %s: %s",
                          project, pr_id, repo, branch)

            pagure_ci.process_pr(self.log, cfg, pr_id, repo, branch)

    def process_build(self, msg):
        ''' Extracts the information from the build and flag the pull-request. '''
        for cfg in jenkins_hook.get_configs(msg['project'], jenkins_hook.Service.JENKINS):
            pagure_ci.process_build(self.log, cfg, msg['build'])


def get_repo(cfg, msg):
    ''' Formats the URL for pagure repo. '''
    url = PAGURE_MAIN_REPO
    if msg['pullrequest']['repo_from']['parent']:
        url = PAGURE_FORK_REPO
    return url.format(
        base=APP.config['APP_URL'],
        user=msg['pullrequest']['repo_from']['user']['name'],
        name=msg['pullrequest']['repo_from']['name'])


def is_rebase(msg):
    ''' Returns Rebase if the Pull-request is rebased. '''
    if msg['pullrequest']['status'] != 'Open':
        return False
    try:
        return msg['pullrequest']['comments'][-1]['notification']
    except (IndexError, KeyError):
        return False
