#!/usr/bin/env python2
# -*- coding: utf-8 -*-

# Milter calls methods of your class at milter events.
# Return REJECT,TEMPFAIL,ACCEPT to short circuit processing for a message.
# You can also add/del recipients, replacebody, add/del headers, etc.

import base64
import email
import os
import StringIO
import sys
import time
from socket import AF_INET, AF_INET6

import Milter
if True:
    from multiprocessing import Process as Thread, Queue
else:
    from threading import Thread
    from Queue import Queue

from Milter.utils import parse_addr
from sqlalchemy.exc import SQLAlchemyError

logq = Queue(maxsize=4)


if 'PAGURE_CONFIG' not in os.environ \
        and os.path.exists('/etc/pagure/pagure.cfg'):
    print 'Using configuration file `/etc/pagure/pagure.cfg`'
    os.environ['PAGURE_CONFIG'] = '/etc/pagure/pagure.cfg'

sys.path.insert(0, os.path.expanduser('/srv/progit'))


import pagure
import pagure.exceptions
import pagure.lib


def get_email_body(emailobj):
    ''' Return the body of the email, preferably in text.
    '''
    body = None
    if emailobj.is_multipart():
        for payload in emailobj.get_payload():
            body = payload.get_payload()
            if payload.get_content_type() == 'text/plain':
                break
    else:
        body = emailobj.get_payload()

    enc = emailobj['Content-Transfer-Encoding']
    if enc == 'base64':
        body = base64.decodestring(body)

    return body


def clean_item(item):
    ''' For an item provided as <item> return the content, if there are no
    <> then return the string.
    '''
    if '<' in item:
        item = item.split('<')[1]
    if '>' in item:
        item = item.split('>')[0]

    return item


class PagureMilter(Milter.Base):

    def __init__(self):  # A new instance with each new connection.
        self.id = Milter.uniqueID()  # Integer incremented with each call.
        self.fp = None

    def envfrom(self, mailfrom, *str):
        self.log("mail from:", mailfrom, *str)
        self.fromparms = Milter.dictfromlist(str)
        # NOTE: self.fp is only an *internal* copy of message data.  You
        # must use addheader, chgheader, replacebody to change the message
        # on the MTA.
        self.fp = StringIO.StringIO()
        self.canon_from = '@'.join(parse_addr(mailfrom))
        self.fp.write('From %s %s\n' % (self.canon_from, time.ctime()))
        return Milter.CONTINUE

    @Milter.noreply
    def header(self, name, hval):
        self.fp.write("%s: %s\n" % (name, hval))     # add header to buffer
        return Milter.CONTINUE

    @Milter.noreply
    def eoh(self):
        self.fp.write("\n")                         # terminate headers
        return Milter.CONTINUE

    @Milter.noreply
    def body(self, chunk):
        self.fp.write(chunk)
        return Milter.CONTINUE

    @Milter.noreply
    def envrcpt(self, to, *str):
        rcptinfo = to, Milter.dictfromlist(str)
        print rcptinfo

        return Milter.CONTINUE

    def eom(self):
        self.fp.seek(0)
        msg = email.message_from_file(self.fp)

        msg_id = msg.get('In-Reply-To', None)
        if msg_id is None:
            self.log('No In-Reply-To, keep going')
            return Milter.CONTINUE

        self.log('msg-ig', msg_id)
        self.log('To', msg['to'])
        self.log('From', msg['From'])

        msg_id = clean_item(msg_id)

        if msg_id and '-ticket-' in msg_id:
            return self.handle_ticket_email(msg, msg_id)
        elif msg_id and '-pull-request-' in msg_id:
            return self.handle_request_email(msg, msg_id)
        else:
            self.log('Not a pagure ticket or pull-request email, let it go')
            return Milter.CONTINUE

    def log(self,*msg):
        logq.put((msg, self.id,time.time()))

    def handle_ticket_email(self, emailobj, msg_id):
        ''' Add the email as a comment on a ticket. '''
        uid  = msg_id.split('-ticket-')[-1].split('@')[0]
        parent_id = None
        if '-' in uid:
            uid, parent_id = uid.rsplit('-', 1)
        if '/' in uid:
            uid = uid.split('/')[0]
        self.log('uid', uid)
        self.log('parent_id', parent_id)

        issue = pagure.lib.get_issue_by_uid(
            pagure.SESSION,
            issue_uid = uid
        )

        if not issue:
            self.log('No related ticket found, let it go')
            return Milter.CONTINUE

        try:
            message = pagure.lib.add_issue_comment(
                pagure.SESSION,
                issue=issue,
                comment=get_email_body(emailobj),
                user=clean_item(emailobj['From']),
                ticketfolder=pagure.APP.config['TICKETS_FOLDER'],
            )
            pagure.SESSION.commit()
        except pagure.exceptions.PagureException, err:
            self.log(str(err))
        except SQLAlchemyError, err:  # pragma: no cover
            pagure.SESSION.rollback()
            self.log(str(err))

        return Milter.ACCEPT

    def handle_request_email(self, emailobj, msg_id):
        ''' Add the email as a comment on a request. '''
        msg_id = msg['In-Reply-To']
        uid  = msg_id.split('-pull-request-')[-1].split('@')[0]
        parent_id = None
        if '-' in uid:
            uid, parent_id = uid.rsplit('-', 1)
        if '/' in uid:
            uid = uid.split('/')[0]
        self.log('uid', uid)
        self.log('parent_id', parent_id)

        request = pagure.lib.get_request_by_uid(
            pagure.SESSION,
            request_uid = uid
        )

        if not request:
            self.log('No related pull-request found, let it go')
            return Milter.CONTINUE

        try:
            message = pagure.lib.add_pull_request_comment(
                pagure.SESSION,
                request=request,
                comment=get_email_body(emailobj),
                user=clean_item(emailobj['From']),
                requestfolder=pagure.APP.config['REQUESTS_FOLDER'],
            )
            pagure.SESSION.commit()
        except pagure.exceptions.PagureException, err:
            self.log(str(err))
        except SQLAlchemyError, err:  # pragma: no cover
            pagure.SESSION.rollback()
            self.log(str(err))

        return Milter.ACCEPT


def background():
    while True:
        t = logq.get()
        if not t: break
        msg,id,ts = t
        print "%s [%d]" % (time.strftime('%Y%b%d %H:%M:%S',time.localtime(ts)),id),
        # 2005Oct13 02:34:11 [1] msg1 msg2 msg3 ...
        for i in msg: print i,
        print


def main():
    bt = Thread(target=background)
    bt.start()
    socketname = "/var/run/pagure/paguresock"
    timeout = 600
    # Register to have the Milter factory create instances of your class:
    Milter.factory = PagureMilter
    print "%s pagure milter startup" % time.strftime('%Y%b%d %H:%M:%S')
    sys.stdout.flush()
    Milter.runmilter("paguremilter", socketname, timeout)
    logq.put(None)
    bt.join()
    print "%s pagure milter shutdown" % time.strftime('%Y%b%d %H:%M:%S')


if __name__ == "__main__":
    main()
