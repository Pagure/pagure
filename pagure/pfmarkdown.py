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


MENTION_RE = r'^(.*?)@(\w+)'
EXPLICIT_FORK_ISSUE_RE = r'(\w+)/(\w+)#([0-9]+)'
EXPLICIT_MAIN_ISSUE_RE = r'[^|\w](?<!\/)(\w+)#([0-9]+)'
IMPLICIT_ISSUE_RE = r'[^|\w](?<!\w)#([0-9]+)'


class MentionPattern(markdown.inlinepatterns.Pattern):
    """ @user pattern class. """

    def handleMatch(self, m):
        """ When the pattern matches, update the text. """
        name = markdown.util.AtomicString(m.group(3))
        text = ' @%s' % name
        user = pagure.lib.search_user(pagure.SESSION, username=name)
        if not user:
            return text

        element = markdown.util.etree.Element("a")
        url = flask.url_for('view_user', username=name)
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

        if not _issue_exists(user, repo, idx):
            return text

        return _issue_anchor_tag(user, repo, idx, text)


class ExplicitMainIssuePattern(markdown.inlinepatterns.Pattern):
    """ Explicit issue pattern (for non-fork project). """

    def handleMatch(self, m):
        """ When the pattern matches, update the text. """
        repo = markdown.util.AtomicString(m.group(2))
        idx = markdown.util.AtomicString(m.group(3))
        text = ' %s#%s' % (repo, idx)

        if not _issue_exists(None, repo, idx):
            return text

        return _issue_anchor_tag(None, repo, idx, text)


class ImplicitIssuePattern(markdown.inlinepatterns.Pattern):
    """ Implicit issue pattern. """

    def handleMatch(self, m):
        """ When the pattern matches, update the text. """
        idx = markdown.util.AtomicString(m.group(2))
        text = ' #%s' % idx

        root = flask.request.url_root
        url = flask.request.url
        user = None
        if 'fork/' in flask.request.url:
            user, repo = url.split('fork/')[1].split('/', 2)[:2]
        else:
            repo = url.split(root)[1].split('/', 1)[0]

        if not _issue_exists(user, repo, idx):
            return text

        return _issue_anchor_tag(user, repo, idx, text)


class PagureExtension(markdown.extensions.Extension):

    def extendMarkdown(self, md, md_globals):
        # First, make it so that bare links get automatically linkified.
        markdown.inlinepatterns.AUTOLINK_RE = '(%s)' % '|'.join([
            r'<(?:f|ht)tps?://[^>]*>',
            r'\b(?:f|ht)tps?://[^)<>\s]+[^.,)<>\s]',
            r'\bwww\.[^)<>\s]+[^.,)<>\s]',
            r'[^(<\s]+\.(?:com|net|org)\b',
        ])

        md.inlinePatterns['mention'] = MentionPattern(MENTION_RE)
        if pagure.APP.config.get('ENABLE_TICKETS', True):
            md.inlinePatterns['explicit_fork_issue'] = \
                ExplicitForkIssuePattern(EXPLICIT_FORK_ISSUE_RE)
            md.inlinePatterns['explicit_main_issue'] = \
                ExplicitMainIssuePattern(EXPLICIT_MAIN_ISSUE_RE)
            md.inlinePatterns['implicit_issue'] = \
                ImplicitIssuePattern(IMPLICIT_ISSUE_RE)

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

    return True


def _issue_anchor_tag(user, repo, idx, text):
    """ Utility method generating the link to an issue. """
    element = markdown.util.etree.Element("a")
    url = flask.url_for('view_issue', username=user, repo=repo, issueid=idx)
    element.set('href', url)
    element.text = text
    return element
