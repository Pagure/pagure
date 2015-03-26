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
"""

import flask

import markdown.inlinepatterns
import markdown.util


def inject():
    """ Hack out python-markdown to do the autolinking that we want. """

    # First, make it so that bare links get automatically linkified.
    markdown.inlinepatterns.AUTOLINK_RE = '(%s)' % '|'.join([
        r'<(?:f|ht)tps?://[^>]*>',
        r'\b(?:f|ht)tps?://[^)<>\s]+[^.,)<>\s]',
        r'\bwww\.[^)<>\s]+[^.,)<>\s]',
        r'[^(<\s]+\.(?:com|net|org)\b',
    ])

    # Second, build some Pattern objects for @mentions, #bugs, etc...
    class MentionPattern(markdown.inlinepatterns.Pattern):
        def handleMatch(self, m):
            el = markdown.util.etree.Element("a")
            name = markdown.util.AtomicString(m.group(2))
            el.set('href', _user_url(name[1:]))
            el.text = name
            return el

    class ExplicitIssuePattern(markdown.inlinepatterns.Pattern):
        def handleMatch(self, m):
            el = markdown.util.etree.Element("a")
            user = markdown.util.AtomicString(m.group(2))
            repo = markdown.util.AtomicString(m.group(3))
            idx = markdown.util.AtomicString(m.group(4))
            el.set('href', _issue_url(user, repo, idx))
            el.text = '%s/%s#%s' % (user, repo, idx)
            return el

    MENTION_RE = r'(@\w+)'
    EXPLICIT_ISSUE_RE = r'(\w+)/(\w+)#([0-9]+)'

    # Lastly, monkey-patch the build_inlinepatterns func to insert our patterns
    original_builder = markdown.build_inlinepatterns

    def extended_builder(md_instance, **kwargs):
        patterns = original_builder(md_instance, **kwargs)
        patterns['mention'] = MentionPattern(
            MENTION_RE, md_instance)
        patterns['explicit_issue'] = ExplicitIssuePattern(
            EXPLICIT_ISSUE_RE, md_instance)
        return patterns

    markdown.build_inlinepatterns = extended_builder


def _user_url(name):
    return flask.url_for('view_user', username=name)


def _issue_url(user, repo, idx):
    return flask.url_for('view_issue', username=user, repo=repo, issueid=idx)
