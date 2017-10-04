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

import flask

import markdown.inlinepatterns
import markdown.util
import pygit2

import pagure
import pagure.lib


MENTION_RE = r'@(\w+)'
# Each line below correspond to a line of the regex:
#  1) Ensure we catch the motif from the start
#  2) See if there is a `forks/` at the start
#  3) See if we have a `user/`
#  4) See if we have a `namespace/`
#  5) Get the last part `project`
#  6) Get the identifier `#<id>`
EXPLICIT_LINK_RE = \
    r'(?<!\w)'\
    '(fork[s]?/)?'\
    '([a-zA-Z0-9_-]*?/)?'\
    '([a-zA-Z0-9_-]*?/)?'\
    '([a-zA-Z0-9_-]+)'\
    '#(?P<id>[0-9]+)'
COMMIT_LINK_RE = \
    r'(?<!\w)'\
    '(fork[s]?/)?'\
    '([a-zA-Z0-9_-]*?/)?'\
    '([a-zA-Z0-9_-]*?/)?'\
    '([a-zA-Z0-9_-]+)'\
    '#(?P<id>[\w]{40})'
IMPLICIT_ISSUE_RE = r'[^|\w](?<!\w)#([0-9]+)'
IMPLICIT_PR_RE = r'[^|\w](?<!\w)PR#([0-9]+)'
IMPLICIT_COMMIT_RE = r'(?<![<\w#])([a-f0-9]{7,40})'
STRIKE_THROUGH_RE = r'~~(.*?)~~'


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


class ExplicitLinkPattern(markdown.inlinepatterns.Pattern):
    """ Explicit link pattern. """

    def handleMatch(self, m):
        """ When the pattern matches, update the text. """
        is_fork = m.group(2)
        user = m.group(3)
        namespace = m.group(4)
        repo = m.group(5)
        idx = m.group(6)
        text = '%s#%s' % (repo, idx)

        if not is_fork and user:
            namespace = user
            user = None

        if namespace:
            namespace = namespace.rstrip('/')
            text = '%s/%s' % (namespace, text)
        if user:
            user = user.rstrip('/')
            text = '%s/%s' % (user.rstrip('/'), text)

        try:
            idx = int(idx)
        except (ValueError, TypeError):
            return text

        issue = _issue_exists(user, namespace, repo, idx)
        if issue:
            return _obj_anchor_tag(user, namespace, repo, issue, text)

        request = _pr_exists(user, namespace, repo, idx)
        if request:
            return _obj_anchor_tag(user, namespace, repo, request, text)

        return text


class CommitLinkPattern(markdown.inlinepatterns.Pattern):
    """ Commit link pattern. """

    def handleMatch(self, m):
        """ When the pattern matches, update the text. """
        is_fork = m.group(2)
        user = m.group(3)
        namespace = m.group(4)
        repo = m.group(5)
        commitid = m.group(6)
        text = '%s#%s' % (repo, commitid)

        if not is_fork and user:
            namespace = user
            user = None

        if namespace:
            namespace = namespace.rstrip('/')
            text = '%s/%s' % (namespace, text)
        if user:
            user = user.rstrip('/')
            text = '%s/%s' % (user.rstrip('/'), text)

        if pagure.lib.search_projects(
                pagure.SESSION,
                username=user,
                fork=is_fork,
                namespace=namespace,
                pattern=repo):
            return _obj_anchor_tag(user, namespace, repo, commitid, text)

        return text


class ImplicitIssuePattern(markdown.inlinepatterns.Pattern):
    """ Implicit issue pattern. """

    def handleMatch(self, m):
        """ When the pattern matches, update the text. """
        idx = markdown.util.AtomicString(m.group(2))
        text = ' #%s' % idx
        try:
            idx = int(idx)
        except (ValueError, TypeError):
            return text

        try:
            namespace, repo, user = _get_ns_repo_user()
        except RuntimeError:
            return text

        issue = _issue_exists(user, namespace, repo, idx)
        if issue:
            return _obj_anchor_tag(user, namespace, repo, issue, text)

        request = _pr_exists(user, namespace, repo, idx)
        if request:
            return _obj_anchor_tag(user, namespace, repo, request, text)

        return text


class ImplicitPRPattern(markdown.inlinepatterns.Pattern):
    """ Implicit pull-request pattern. """

    def handleMatch(self, m):
        """ When the pattern matches, update the text. """
        idx = markdown.util.AtomicString(m.group(2))
        text = ' PR#%s' % idx
        try:
            idx = int(idx)
        except (ValueError, TypeError):
            return text

        try:
            namespace, repo, user = _get_ns_repo_user()
        except RuntimeError:
            return text

        issue = _issue_exists(user, namespace, repo, idx)
        if issue:
            return _obj_anchor_tag(user, namespace, repo, issue, text)

        request = _pr_exists(user, namespace, repo, idx)
        if request:
            return _obj_anchor_tag(user, namespace, repo, request, text)

        return text


class ImplicitCommitPattern(markdown.inlinepatterns.Pattern):
    """ Implicit commit pattern. """

    def handleMatch(self, m):
        """ When the pattern matches, update the text. """

        githash = markdown.util.AtomicString(m.group(2))
        text = '%s' % githash

        try:
            namespace, repo, user = _get_ns_repo_user()
        except RuntimeError:
            return text

        if pagure.lib.search_projects(
                pagure.SESSION,
                username=user,
                namespace=namespace,
                pattern=repo) \
                and _commit_exists(user, namespace, repo, githash):
            return _obj_anchor_tag(user, namespace, repo, githash, text[:7])

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
            r'<((?:[Ff]|[Hh][Tt])[Tt][Pp][Ss]?://[^>]*)>',
            r'\b(?:[Ff]|[Hh][Tt])[Tt][Pp][Ss]?://[^)<>\s]+[^.,)<>\s]',
            r'<(Ii][Rr][Cc][Ss]?://[^>]*)>',
            r'\b[Ii][Rr][Cc][Ss]?://[^)<>\s]+[^.,)<>\s]',
        ])

        md.inlinePatterns['mention'] = MentionPattern(MENTION_RE)

        md.inlinePatterns['implicit_commit'] = ImplicitCommitPattern(
            IMPLICIT_COMMIT_RE)
        md.inlinePatterns['commit_links'] = CommitLinkPattern(
            COMMIT_LINK_RE)

        if pagure.APP.config.get('ENABLE_TICKETS', True):
            md.inlinePatterns['implicit_pr'] = \
                ImplicitPRPattern(IMPLICIT_PR_RE)
            md.inlinePatterns['explicit_fork_issue'] = \
                ExplicitLinkPattern(EXPLICIT_LINK_RE)
            md.inlinePatterns['implicit_issue'] = \
                ImplicitIssuePattern(IMPLICIT_ISSUE_RE)

        md.inlinePatterns['striked'] = StrikeThroughPattern(
            STRIKE_THROUGH_RE)

        md.registerExtension(self)


def makeExtension(*arg, **kwargs):
    return PagureExtension(**kwargs)


def _issue_exists(user, namespace, repo, idx):
    """ Utility method checking if a given issue exists. """

    repo_obj = pagure.get_authorized_project(
        pagure.SESSION, project_name=repo, user=user, namespace=namespace)

    if not repo_obj:
        return False

    issue_obj = pagure.lib.search_issues(
        pagure.SESSION, repo=repo_obj, issueid=idx)
    if not issue_obj:
        return False

    return issue_obj


def _pr_exists(user, namespace, repo, idx):
    """ Utility method checking if a given PR exists. """
    repo_obj = pagure.get_authorized_project(
        pagure.SESSION, project_name=repo, user=user, namespace=namespace)

    if not repo_obj:
        return False

    pr_obj = pagure.lib.search_pull_requests(
        pagure.SESSION, project_id=repo_obj.id, requestid=idx)
    if not pr_obj:
        return False

    return pr_obj


def _commit_exists(user, namespace, repo, githash):
    """ Utility method checking if a given commit exists. """
    repo_obj = pagure.get_authorized_project(
        pagure.SESSION, project_name=repo, user=user, namespace=namespace)
    if not repo_obj:
        return False

    reponame = pagure.get_repo_path(repo_obj)
    git_repo = pygit2.Repository(reponame)
    return githash in git_repo


def _obj_anchor_tag(user, namespace, repo, obj, text):
    """
    Utility method generating the link to an issue or a PR.

    :return: An element tree containing the href to the issue or PR
    :rtype:  xml.etree.ElementTree.Element
    """
    if isinstance(obj, basestring):
        url = flask.url_for(
            'view_commit', username=user, namespace=namespace, repo=repo,
            commitid=obj)
        title = 'Commit %s' % obj
    elif obj.isa == 'issue':
        url = flask.url_for(
            'view_issue', username=user, namespace=namespace, repo=repo,
            issueid=obj.id)
        if obj.private:
            title = 'Private issue'
        else:
            if obj.status:
                title = '[%s] %s' % (obj.status, obj.title)
            else:
                title = obj.title
    else:
        url = flask.url_for(
            'request_pull', username=user, namespace=namespace, repo=repo,
            requestid=obj.id)
        if obj.status:
            title = '[%s] %s' % (obj.status, obj.title)
        else:
            title = obj.title

    element = markdown.util.etree.Element("a")
    element.set('href', url)
    element.set('title', title)
    element.text = text
    return element


def _get_ns_repo_user():
    """ Return the namespace, repo, user corresponding to the given request

    :return: A tuple of three string corresponding to namespace, repo, user
    :rtype: tuple(str, str, str)
    """

    root = flask.request.url_root
    url = flask.request.url

    user = flask.request.args.get('user')
    namespace = flask.request.args.get('namespace')
    repo = flask.request.args.get('repo')

    if not user and not repo:
        if 'fork/' in url:
            user, ext = url.split('fork/')[1].split('/', 1)
        else:
            ext = url.split(root)[1]

        if ext.count('/') >= 3:
            namespace, repo = ext.split('/', 2)[:2]
        else:
            repo = ext.split('/', 1)[0]

    return (namespace, repo, user)
