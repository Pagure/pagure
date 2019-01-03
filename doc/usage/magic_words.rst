Magic Words
===========

Magic words are words and constructs you can use in your commit message to
make pagure act on tickets or pull-requests.

Enabling magic words
--------------------

These magic words are enabled if the ``pagure`` git hook is enable. To do
so, go to your project's ``settings`` page, open the ``Hooks`` tab and
activate there the ``Pagure`` hook.


Using magic words
-----------------

To reference an issue/PR you need to use one of recognized keywords followed by
a reference to the issue or PR, separated by whitespace and and optional colon.
Such references can be either:

- The issue/PR number preceded by the # symbol
- The full URL of the issue or PR

If using the full URL, it is possible to reference issues in other projects.

The recognized keywords are:

- fix/fixed/fixes
- relate/related/relates
- merge/merges/merged
- close/closes/closed

Examples:

- Fixes #21
- related: https://pagure.io/myproject/issue/32
- this commit merges #74
- Merged: https://pagure.io/myproject/pull-request/74

Capitalization does not matter; neither does the colon (``:``) between
keyword and number.
