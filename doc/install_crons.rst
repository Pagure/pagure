Cron Jobs
=========

Some actions in pagure are meant to the run via a cron job.


API key expiration reminder
---------------------------

One of the cron job sending reminder about API keys that are about to expire.
It will send an email 10 days, then 5 days and finally the day before the
key expires to the person who has created.

The cron job can be found in the sources in: ::

    files/api_key_expire_mail.py

In the RPM it is installed in: ::

    /usr/share/pagure/api_key_expire_mail.py

This cron job is meant to be run daily using a syntax similar to:

::

    10 0 * * * root python /usr/share/pagure/api_key_expire_mail.py

which will make the script run at 00:10 every day.
