# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301,
# USA.

""" Pagure-flavored Markdown

Author: Ralph Bean <rbean@redhat.com>
        Pierre-Yves Chibon <pingou@pingoured.fr>
"""

import re

import flask

import markdown.inlinepatterns
import markdown.util

import pagure
import pagure.lib


MENTION_RE = r'@(\w+)'
EXPLICIT_FORK_ISSUE_RE = r'(\w+)/(\w+)#([0-9]+)'
EXPLICIT_MAIN_ISSUE_RE = r'[^|\w](?<!\/)(\w+)#([0-9]+)'
IMPLICIT_ISSUE_RE = r'[^|\w](?<!\w)#([0-9]+)'
IMPLICIT_PR_RE = r'[^|\w](?<!\w)PR#([0-9]+)'
STRIKE_THROUGH_RE = r'~~(\w+)~~'


class MentionPattern(markdown.inlinepatterns.Pattern):
    """ @user pattern class. """

    def handleMatch(self, m):
        """ When the pattern matches, update the text. """
        name = markdown.util.AtomicString(m.group(2))
        text = ' @%s' % name
        user = pagure.lib.search_user(pagure.SESSION, username=name)
        if not user:
            return text

        element = markdown.util.etree.Element("a")
        base_url = pagure.APP.config['APP_URL']
        if base_url.endswith('/'):
            base_url = base_url[:-1]
        url = '%s/user/%s' % (base_url, user.username)
        element.set('href', url)
        element.text = text
        return element


class ExplicitForkIssuePattern(markdown.inlinepatterns.Pattern):
    """ Explicit fork issue pattern. """

    def handleMatch(self, m):
        """ When the pattern matches, update the text. """
        user = markdown.util.AtomicString(m.group(2))
        repo = markdown.util.AtomicString(m.group(3))
        idx = markdown.util.AtomicString(m.group(4))
        text = '%s/%s#%s' % (user, repo, idx)
        try:
            idx = int(idx)
        except:
            return text

        issue = _issue_exists(user, repo, idx)
        if not issue:
            return text

        return _obj_anchor_tag(user, repo, issue, text)


class ExplicitMainIssuePattern(markdown.inlinepatterns.Pattern):
    """ Explicit issue pattern (for non-fork project). """

    def handleMatch(self, m):
        """ When the pattern matches, update the text. """
        repo = markdown.util.AtomicString(m.group(2))
        idx = markdown.util.AtomicString(m.group(3))
        text = ' %s#%s' % (repo, idx)
        try:
            idx = int(idx)
        except:
            return text

        issue = _issue_exists(None, repo, idx)
        if not issue:
            return text

        return _obj_anchor_tag(None, repo, issue, text)


class ImplicitIssuePattern(markdown.inlinepatterns.Pattern):
    """ Implicit issue pattern. """

    def handleMatch(self, m):
        """ When the pattern matches, update the text. """
        idx = markdown.util.AtomicString(m.group(2))
        text = ' #%s' % idx
        try:
            idx = int(idx)
        except:
            return text

        try:
            root = flask.request.url_root
            url = flask.request.url
        except RuntimeError:
            return text
        repo = user = None

        if flask.request.args.get('user'):
            user = flask.request.args.get('user')
        if flask.request.args.get('repo'):
            repo = flask.request.args.get('repo')

        if not user and not repo:
            if 'fork/' in url:
                user, repo = url.split('fork/')[1].split('/', 2)[:2]
            else:
                repo = url.split(root)[1].split('/', 1)[0]

        issue = _issue_exists(user, repo, idx)
        if issue:
            return _obj_anchor_tag(user, repo, issue, text)

        request = _pr_exists(user, repo, idx)
        if request:
            return _obj_anchor_tag(user, repo, request, text)

        return text


class ImplicitPRPattern(markdown.inlinepatterns.Pattern):
    """ Implicit pull-request pattern. """

    def handleMatch(self, m):
        """ When the pattern matches, update the text. """
        idx = markdown.util.AtomicString(m.group(2))
        text = ' PR#%s' % idx
        try:
            idx = int(idx)
        except:
            return text

        try:
            root = flask.request.url_root
            url = flask.request.url
        except RuntimeError:
            return text
        repo = user = None

        if flask.request.args.get('user'):
            user = flask.request.args.get('user')
        if flask.request.args.get('repo'):
            repo = flask.request.args.get('repo')

        if not user and not repo:
            if 'fork/' in url:
                user, repo = url.split('fork/')[1].split('/', 2)[:2]
            else:
                repo = url.split(root)[1].split('/', 1)[0]

        issue = _issue_exists(user, repo, idx)
        if issue:
            return _obj_anchor_tag(user, repo, issue, text)

        request = _pr_exists(user, repo, idx)
        if request:
            return _obj_anchor_tag(user, repo, request, text)

        return text


class StrikeThroughPattern(markdown.inlinepatterns.Pattern):
    """ ~~striked~~ pattern class. """

    def handleMatch(self, m):
        """ When the pattern matches, update the text. """
        text = markdown.util.AtomicString(m.group(2))

        element = markdown.util.etree.Element("del")
        element.text = text
        return element


class PagureExtension(markdown.extensions.Extension):

    def extendMarkdown(self, md, md_globals):
        # First, make it so that bare links get automatically linkified.
        markdown.inlinepatterns.AUTOLINK_RE = '(%s)' % '|'.join([
            r'<(?:f|ht)tps?://[^>]*>',
            r'\b(?:f|ht)tps?://[^)<>\s]+[^.,)<>\s]',
        ])

        md.inlinePatterns['mention'] = MentionPattern(MENTION_RE)
        if pagure.APP.config.get('ENABLE_TICKETS', True):
            md.inlinePatterns['implicit_pr'] = \
                ImplicitPRPattern(IMPLICIT_PR_RE)
            md.inlinePatterns['explicit_fork_issue'] = \
                ExplicitForkIssuePattern(EXPLICIT_FORK_ISSUE_RE)
            md.inlinePatterns['explicit_main_issue'] = \
                ExplicitMainIssuePattern(EXPLICIT_MAIN_ISSUE_RE)
            md.inlinePatterns['implicit_issue'] = \
                ImplicitIssuePattern(IMPLICIT_ISSUE_RE)

        md.inlinePatterns['striked'] = StrikeThroughPattern(
            STRIKE_THROUGH_RE)

        md.registerExtension(self)


def makeExtension(*arg, **kwargs):
    return PagureExtension(**kwargs)


def _issue_exists(user, repo, idx):
    """ Utility method checking if a given issue exists. """
    repo_obj = pagure.lib.get_project(
        pagure.SESSION, name=repo, user=user)
    if not repo_obj:
        return False

    issue_obj = pagure.lib.search_issues(
        pagure.SESSION, repo=repo_obj, issueid=idx)
    if not issue_obj:
        return False

    return issue_obj


def _pr_exists(user, repo, idx):
    """ Utility method checking if a given PR exists. """
    repo_obj = pagure.lib.get_project(
        pagure.SESSION, name=repo, user=user)
    if not repo_obj:
        return False

    pr_obj = pagure.lib.search_pull_requests(
        pagure.SESSION, project_id=repo_obj.id, requestid=idx)
    if not pr_obj:
        return False

    return pr_obj


def _obj_anchor_tag(user, repo, obj, text):
    """ Utility method generating the link to an issue or a PR. """
    if obj.isa == 'issue':
        url = flask.url_for(
            'view_issue', username=user, repo=repo, issueid=obj.id)
    else:
        url = flask.url_for(
            'request_pull', username=user, repo=repo, requestid=obj.id)

    element = markdown.util.etree.Element("a")
    element.set('href', url)
    element.set('title', obj.title)
    element.text = text
    return element
