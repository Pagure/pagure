#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Milter calls methods of your class at milter events.
# Return REJECT,TEMPFAIL,ACCEPT to short circuit processing for a message.
# You can also add/del recipients, replacebody, add/del headers, etc.

from __future__ import print_function, unicode_literals, absolute_import

import base64
import email
import hashlib
import os
import sys
import time
from io import BytesIO
from multiprocessing import Process as Thread, Queue

import Milter
import requests
import six

from Milter.utils import parse_addr

import pagure.config
import pagure.lib.model_base
import pagure.lib.query


if "PAGURE_CONFIG" not in os.environ and os.path.exists(
    "/etc/pagure/pagure.cfg"
):
    os.environ["PAGURE_CONFIG"] = "/etc/pagure/pagure.cfg"


logq = Queue(maxsize=4)
_config = pagure.config.reload_config()


def get_email_body(emailobj):
    """ Return the body of the email, preferably in text.
    """

    def _get_body(emailobj):
        """ Return the first text/plain body found if the email is multipart
        or just the regular payload otherwise.
        """
        if emailobj.is_multipart():
            for payload in emailobj.get_payload():
                # If the message comes with a signature it can be that this
                # payload itself has multiple parts, so just return the
                # first one
                if payload.is_multipart():
                    return _get_body(payload)

                body = payload.get_payload()
                if payload.get_content_type() == "text/plain":
                    return body
        else:
            return emailobj.get_payload()

    body = _get_body(emailobj)

    enc = emailobj["Content-Transfer-Encoding"]
    if enc == "base64":
        body = base64.decodestring(body)

    return body


def clean_item(item):
    """ For an item provided as <item> return the content, if there are no
    <> then return the string.
    """
    if "<" in item:
        item = item.split("<")[1]
    if ">" in item:
        item = item.split(">")[0]

    return item


class PagureMilter(Milter.Base):
    def __init__(self):  # A new instance with each new connection.
        self.id = Milter.uniqueID()  # Integer incremented with each call.
        self.fp = None

    def log(self, message):
        print(message)
        sys.stdout.flush()

    def envfrom(self, mailfrom, *str):
        self.log("mail from: %s  -  %s" % (mailfrom, str))
        self.fromparms = Milter.dictfromlist(str)
        # NOTE: self.fp is only an *internal* copy of message data.  You
        # must use addheader, chgheader, replacebody to change the message
        # on the MTA.
        self.fp = BytesIO()
        self.canon_from = "@".join(parse_addr(mailfrom))
        from_txt = "From %s %s\n" % (self.canon_from, time.ctime())
        self.fp.write(from_txt.encode("utf-8"))
        return Milter.CONTINUE

    @Milter.noreply
    def header(self, name, hval):
        """ Headers """
        # add header to buffer
        header_txt = "%s: %s\n" % (name, hval)
        self.fp.write(header_txt.encode("utf-8"))
        return Milter.CONTINUE

    @Milter.noreply
    def eoh(self):
        """ End of Headers """
        self.fp.write(b"\n")
        return Milter.CONTINUE

    @Milter.noreply
    def body(self, chunk):
        """ Body """
        self.fp.write(chunk)
        return Milter.CONTINUE

    @Milter.noreply
    def envrcpt(self, to, *str):
        rcptinfo = to, Milter.dictfromlist(str)
        print(rcptinfo)

        return Milter.CONTINUE

    def eom(self):
        """ End of Message """
        self.fp.seek(0)
        if six.PY3:
            msg = email.message_from_binary_file(self.fp)
        else:
            msg = email.message_from_file(self.fp)

        self.log("To %s" % msg["to"])
        self.log("Cc %s" % msg.get("cc"))
        self.log("From %s" % msg["From"])

        # First check whether the message is addressed to this milter.
        email_address = msg["to"]
        if "reply+" in msg.get("cc", ""):
            email_address = msg["cc"]
        if "reply+" not in email_address:
            # The message is not addressed to this milter so don't touch it.
            self.log(
                "No valid recipient email found in To/Cc: %s" % email_address
            )
            return Milter.ACCEPT

        if msg["From"] and msg["From"] == _config.get("FROM_EMAIL"):
            self.log("Let's not process the email we send")
            return Milter.ACCEPT

        msg_id = msg.get("In-Reply-To", None)
        if msg_id is None:
            self.log("No In-Reply-To, can't process this message.")
            self.setreply(
                "554",
                xcode="5.5.0",
                msg="Replies to Pagure must have an In-Reply-To header field."
            )
            return Milter.REJECT

        # Ensure we don't get extra lines in the message-id
        msg_id = msg_id.split("\n")[0].strip()

        self.log("msg-id %s" % msg_id)

        # Ensure the user replied to his/her own notification, not that
        # they are trying to forge their ID into someone else's
        salt = _config.get("SALT_EMAIL")
        from_email = clean_item(msg["From"])
        session = pagure.lib.model_base.create_session(_config["DB_URL"])
        try:
            user = pagure.lib.query.get_user(session, from_email)
        except:
            self.log(
                "Could not find an user in the DB associated with %s"
                % from_email
            )
            session.remove()
            self.setreply(
                "550",
                xcode="5.7.1",
                msg="The sender address <%s> isn't recognized." % from_email
            )
            return Milter.REJECT

        hashes = []
        for email_obj in user.emails:
            m = hashlib.sha512(
                b"%s%s%s"
                % (
                    msg_id.encode("utf-8"),
                    salt.encode("utf-8"),
                    email_obj.email.encode("utf-8"),
                )
            )
            hashes.append(m.hexdigest())

        tohash = email_address.split("@")[0].split("+")[-1]
        if tohash not in hashes:
            self.log("hash list: %s" % hashes)
            self.log("tohash:    %s" % tohash)
            self.log("Hash does not correspond to the destination")
            session.remove()
            self.setreply(
                "550", xcode="5.7.1", msg="Reply authentication failed."
            )
            return Milter.REJECT

        msg_id = clean_item(msg_id)

        try:
            if msg_id and "-ticket-" in msg_id:
                self.log("Processing issue")
                session.remove()
                return self.handle_ticket_email(msg, msg_id)
            elif msg_id and "-pull-request-" in msg_id:
                self.log("Processing pull-request")
                session.remove()
                return self.handle_request_email(msg, msg_id)
            else:
                # msg_id passed the hash check, and yet wasn't recognized as
                # a message ID generated by Pagure. This is probably a bug,
                # because it should be impossible unless an attacker has
                # acquired the secret "salt" or broken the hash algorithm.
                self.log(
                    "Not a pagure ticket or pull-request email, rejecting it."
                )
                session.remove()
                self.setreply(
                    "554",
                    xcode="5.3.5",
                    msg="Pagure couldn't determine how to handle the message."
                )
                return Milter.REJECT
        except requests.ReadTimeout as e:
            self.setreply(
                "451",
                xcode="4.4.2",
                msg="The comment couldn't be added: " + str(e)
            )
            return Milter.TEMPFAIL
        except requests.ConnectionError as e:
            self.setreply(
                "451",
                xcode="4.4.1",
                msg="The comment couldn't be added: " + str(e)
            )
            return Milter.TEMPFAIL
        except requests.RequestException as e:
            self.setreply(
                "554",
                xcode="5.3.0",
                msg="The comment couldn't be added: " + str(e)
            )
            return Milter.REJECT

    def handle_ticket_email(self, emailobj, msg_id):
        """ Add the email as a comment on a ticket. """
        uid = msg_id.split("-ticket-")[-1].split("@")[0]
        parent_id = None
        if "-" in uid:
            uid, parent_id = uid.rsplit("-", 1)
        if "/" in uid:
            uid = uid.split("/")[0]
        self.log("uid %s" % uid)
        self.log("parent_id %s" % parent_id)

        data = {
            "objid": uid,
            "comment": get_email_body(emailobj),
            "useremail": clean_item(emailobj["From"]),
        }
        url = _config.get("APP_URL")

        if url.endswith("/"):
            url = url[:-1]
        url = "%s/pv/ticket/comment/" % url
        self.log("Calling URL: %s" % url)
        req = requests.put(url, data=data)
        if req.status_code == 200:
            self.log("Comment added")
            # The message is now effectively delivered. Tell the MTA to accept
            # and discard it.
            # If you want the message to be processed by another milter after
            # this one, or delivered to a mailbox the usual way, then change
            # DROP to ACCEPT.
            return Milter.DROP
        self.log("Could not add the comment to ticket to pagure")
        self.log(req.text)

        self.setreply(
            "554",
            xcode="5.3.0",
            msg=(
                "The comment couldn't be added to the issue. "
                + "HTTP status: %d %s." % (req.status_code, req.reason)
            )
        )
        return Milter.REJECT

    def handle_request_email(self, emailobj, msg_id):
        """ Add the email as a comment on a request. """
        uid = msg_id.split("-pull-request-")[-1].split("@")[0]
        parent_id = None
        if "-" in uid:
            uid, parent_id = uid.rsplit("-", 1)
        if "/" in uid:
            uid = uid.split("/")[0]
        self.log("uid %s" % uid)
        self.log("parent_id %s" % parent_id)

        data = {
            "objid": uid,
            "comment": get_email_body(emailobj),
            "useremail": clean_item(emailobj["From"]),
        }
        url = _config.get("APP_URL")

        if url.endswith("/"):
            url = url[:-1]
        url = "%s/pv/pull-request/comment/" % url
        self.log("Calling URL: %s" % url)
        req = requests.put(url, data=data)
        if req.status_code == 200:
            self.log("Comment added on PR")
            # The message is now effectively delivered. Tell the MTA to accept
            # and discard it.
            # If you want the message to be processed by another milter after
            # this one, or delivered to a mailbox the usual way, then change
            # DROP to ACCEPT.
            return Milter.DROP
        self.log("Could not add the comment to PR to pagure")
        self.log(req.text)

        self.setreply(
            "554",
            xcode="5.3.0",
            msg=(
                "The comment couldn't be added to the pull request. "
                + "HTTP status: %d %s." % (req.status_code, req.reason)
            )
        )
        return Milter.REJECT


def background():
    while True:
        t = logq.get()
        if not t:
            break
        msg, id, ts = t
        print(
            "%s [%d]"
            % (time.strftime("%Y%b%d %H:%M:%S", time.localtime(ts)), id)
        )
        # 2005Oct13 02:34:11 [1] msg1 msg2 msg3 ...
        for i in msg:
            print(i)
        print


def main():
    bt = Thread(target=background)
    bt.start()
    socketname = "/var/run/pagure/paguresock"
    timeout = 600
    # Register to have the Milter factory create instances of your class:
    Milter.factory = PagureMilter
    print("%s pagure milter startup" % time.strftime("%Y%b%d %H:%M:%S"))
    sys.stdout.flush()
    Milter.runmilter("paguremilter", socketname, timeout)
    logq.put(None)
    bt.join()
    print("%s pagure milter shutdown" % time.strftime("%Y%b%d %H:%M:%S"))


if __name__ == "__main__":
    main()
