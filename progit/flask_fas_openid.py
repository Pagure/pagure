# -*- coding: utf-8 -*-
# Flask-FAS-OpenID - A Flask extension for authorizing users with FAS-OpenID
#
# Primary maintainer: Patrick Uiterwijk <puiterwijk@fedoraproject.org>
#
# Copyright (c) 2013, Patrick Uiterwijk
# This file is part of python-fedora
#
# python-fedora is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# python-fedora is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with python-fedora; if not, see <http://www.gnu.org/licenses/>

'''
FAS-OpenID authentication plugin for the flask web framework

.. moduleauthor:: Patrick Uiterwijk <puiterwijk@fedoraproject.org>

..versionadded:: 0.3.33
'''
from functools import wraps

from bunch import Bunch
import flask
try:
    from flask import _app_ctx_stack as stack
except ImportError:
    from flask import _request_ctx_stack as stack

import openid
from openid.consumer import consumer
from openid.fetchers import setDefaultFetcher, Urllib2Fetcher
from openid.extensions import pape, sreg
from openid_cla import cla
from openid_teams import teams

from fedora import __version__


class FASJSONEncoder(flask.json.JSONEncoder):
    """ Dedicated JSON encoder for the FAS openid information. """

    def default(self, o):
        """Implement this method in a subclass such that it returns a
        serializable object for ``o``, or calls the base implementation (to
        raise a ``TypeError``).

        For example, to support arbitrary iterators, you could implement
        default like this::

        def default(self, o):
            try:
                iterable = iter(o)
            except TypeError:
                pass
            else:
                return list(iterable)
            return JSONEncoder.default(self, o)
        """
        if isinstance(o, (set, frozenset)):
            return list(o)
        return flask.json.JSONEncoder.default(self, o)


class FAS(object):

    def __init__(self, app=None):
        self.postlogin_func = None
        self.app = app
        if self.app is not None:
            self._init_app(app)
        # json_encoder is only available from flask 0.10
        version = flask.__version__.split('.')
        assume_recent = False
        try:
            major = int(version[0])
            minor = int(version[1])
        except ValueError:
            # We'll assume we're using a recent enough flask as the packages
            # of old versions used sane version numbers.
            assume_recent = True
        if assume_recent or (major >= 0 and minor >= 10):
            self.app.json_encoder = FASJSONEncoder

    def _init_app(self, app):
        app.config.setdefault('FAS_OPENID_ENDPOINT',
                              'http://id.fedoraproject.org/')
        app.config.setdefault('FAS_OPENID_CHECK_CERT', True)

        if not self.app.config['FAS_OPENID_CHECK_CERT']:
            setDefaultFetcher(Urllib2Fetcher())

        @app.route('/_flask_fas_openid_handler/', methods=['GET', 'POST'])
        def flask_fas_openid_handler():
            return self._handle_openid_request()

        app.before_request(self._check_session)

    def postlogin(self, f):
        """Marks a function as post login handler. This decorator calls your
        function after the login has been performed.
        """
        self.postlogin_func = f
        return f

    def _handle_openid_request(self):
        return_url = flask.session.get('FLASK_FAS_OPENID_RETURN_URL', None)
        cancel_url = flask.session.get('FLASK_FAS_OPENID_CANCEL_URL', None)
        base_url = self.normalize_url(flask.request.base_url)
        oidconsumer = consumer.Consumer(flask.session, None)
        info = oidconsumer.complete(flask.request.values, base_url)
        display_identifier = info.getDisplayIdentifier()

        if info.status == consumer.FAILURE and display_identifier:
            return 'FAILURE. display_identifier: %s' % display_identifier
        elif info.status == consumer.CANCEL:
            if cancel_url:
                return flask.redirect(cancel_url)
            return 'OpenID request was cancelled'
        elif info.status == consumer.SUCCESS:
            sreg_resp = sreg.SRegResponse.fromSuccessResponse(info)
            pape_resp = pape.Response.fromSuccessResponse(info)
            teams_resp = teams.TeamsResponse.fromSuccessResponse(info)
            cla_resp = cla.CLAResponse.fromSuccessResponse(info)
            user = {'fullname': '', 'username': '', 'email': '',
                    'timezone': '', 'cla_done': False, 'groups': []}
            if not sreg_resp:
                # If we have no basic info, be gone with them!
                return flask.redirect(cancel_url)
            user['username'] = sreg_resp.get('nickname')
            user['fullname'] = sreg_resp.get('fullname')
            user['email'] = sreg_resp.get('email')
            user['timezone'] = sreg_resp.get('timezone')
            if cla_resp:
                user['cla_done'] = cla.CLA_URI_FEDORA_DONE in cla_resp.clas
            if teams_resp:
                # The groups do not contain the cla_ groups
                user['groups'] = frozenset(teams_resp.teams)
            flask.session['FLASK_FAS_OPENID_USER'] = user
            flask.session.modified = True
            if self.postlogin_func is not None:
                self._check_session()
                return self.postlogin_func(return_url)
            else:
                return flask.redirect(return_url)
        else:
            return 'Strange state: %s' % info.status

    def _check_session(self):
        if not 'FLASK_FAS_OPENID_USER' in flask.session \
                or flask.session['FLASK_FAS_OPENID_USER'] is None:
            flask.g.fas_user = None
        else:
            user = flask.session['FLASK_FAS_OPENID_USER']
            # Add approved_memberships to provide backwards compatibility
            # New applications should only use g.fas_user.groups
            user['approved_memberships'] = []
            for group in user['groups']:
                membership = dict()
                membership['name'] = group
                user['approved_memberships'].append(Bunch.fromDict(membership))
            flask.g.fas_user = Bunch.fromDict(user)
            flask.g.fas_user.groups = frozenset(flask.g.fas_user.groups)
        flask.g.fas_session_id = 0

    def login(self, username=None, password=None, return_url=None,
              cancel_url=None, groups=['_FAS_ALL_GROUPS_']):
        """Tries to log in a user.

        Sets the user information on :attr:`flask.g.fas_user`.
        Will set 0 to :attr:`flask.g.fas_session_id, for compatibility
        with flask_fas.

        :kwarg username: Not used, but accepted for compatibility with the
            flask_fas module
        :kwarg password: Not used, but accepted for compatibility with the
            flask_fas module
        :kwarg return_url: The URL to forward the user to after login
        :kwarg groups: A string or a list of group the user should belong
            to to be authentified.
        :returns: True if the user was succesfully authenticated.
        :raises: Might raise an redirect to the OpenID endpoint
        """
        if return_url is None and return_func is None:
            return_url = flask.request.args.get('next', flask.request.url)
        session = {}
        oidconsumer = consumer.Consumer(session, None)
        try:
            request = oidconsumer.begin(self.app.config['FAS_OPENID_ENDPOINT'])
        except consumer.DiscoveryFailure, exc:
            # VERY strange, as this means it could not discover an OpenID
            # endpoint at FAS_OPENID_ENDPOINT
            return 'discoveryfailure'
        if request is None:
            # Also very strange, as this means the discovered OpenID
            # endpoint is no OpenID endpoint
            return 'no-request'

        if isinstance(groups, basestring):
            groups = [groups]

        request.addExtension(sreg.SRegRequest(
            required=['nickname', 'fullname', 'email', 'timezone']))
        request.addExtension(pape.Request([]))
        request.addExtension(teams.TeamsRequest(requested=groups))
        request.addExtension(cla.CLARequest(
            requested=[cla.CLA_URI_FEDORA_DONE]))

        trust_root = self.normalize_url(flask.request.url_root)
        return_to = trust_root + '_flask_fas_openid_handler/'

        flask.session['FLASK_FAS_OPENID_RETURN_URL'] = return_url
        flask.session['FLASK_FAS_OPENID_CANCEL_URL'] = cancel_url
        if request.shouldSendRedirect():
            redirect_url = request.redirectURL(
                trust_root, return_to, False)
            return flask.redirect(redirect_url)
        else:
            return request.htmlMarkup(
                trust_root, return_to,
                form_tag_attrs={'id': 'openid_message'}, immediate=False)

    def logout(self):
        '''Logout the user associated with this session
        '''
        flask.session['FLASK_FAS_OPENID_USER'] = None
        flask.g.fas_session_id = None
        flask.g.fas_user = None
        flask.session.modified = True

    def normalize_url(self, url):
        ''' Replace the scheme prefix of a url with our preferred scheme.
        '''
        scheme = self.app.config['PREFERRED_URL_SCHEME']
        scheme_index = url.index('://')
        return scheme + url[scheme_index:]


# This is a decorator we can use with any HTTP method (except login, obviously)
# to require a login.
# If the user is not logged in, it will redirect them to the login form.
# http://flask.pocoo.org/docs/patterns/viewdecorators/#login-required-decorator
def fas_login_required(function):
    """ Flask decorator to ensure that the user is logged in against FAS.
    To use this decorator you need to have a function named 'auth_login'.
    Without that function the redirect if the user is not logged in will not
    work.
    """
    @wraps(function)
    def decorated_function(*args, **kwargs):
        if flask.g.fas_user is None:
            return flask.redirect(flask.url_for('auth_login',
                                                next=flask.request.url))
        return function(*args, **kwargs)
    return decorated_function


def cla_plus_one_required(function):
    """ Flask decorator to retrict access to CLA+1.
    To use this decorator you need to have a function named 'auth_login'.
    Without that function the redirect if the user is not logged in will not
    work.
    """
    @wraps(function)
    def decorated_function(*args, **kwargs):
        if flask.g.fas_user is None or not flask.g.fas_user.cla_done \
                or len(flask.g.fas_user.groups) < 1:
            # FAS-OpenID does not return cla_ groups
            return flask.redirect(flask.url_for('auth_login',
                                                next=flask.request.url))
        else:
            return function(*args, **kwargs)
    return decorated_function
