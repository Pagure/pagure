""" This is an example pagure configuration for fedmsg.
By convention, it is normally installed as ``/etc/fedmsg.d/pagure.py``

For Fedora Infrastructure, our own version of this file is kept in
``ansible/roles/fedmsg/base/templates/``

It needs to be globally available so remote consumers know how to find the
pagure producer (wsgi process).
"""

import socket

hostname = socket.gethostname().split(".")[0]

config = dict(endpoints={"pagure.%s" % hostname: ["tcp://127.0.0.1:3005"]})
