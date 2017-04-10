Using Markdown in Pagure
========================

Pagure uses `Markdown syntax highlighting
<https://daringfireball.net/projects/markdown/syntax>`_ as the base for
formatting comments in issues, pull requests, and in Markdown files in
repositories. For basic formatting, Pagure follows common Markdown
formatting, but it also has some unique syntax for more advanced
formatting. This help page helps demonstrate how to use Markdown in Pagure.


Pagure relies on the `Markdown <http://pythonhosted.org/Markdown/>`_ python
module to do the convertion.
It has enabled a few extensions:

- `Definition Lists <http://pythonhosted.org/Markdown/extensions/definition_lists.html>`_
- `Fenced Code Blocks <http://pythonhosted.org/Markdown/extensions/fenced_code_blocks.html>`_
- `Tables <http://pythonhosted.org/Markdown/extensions/tables.html>`_
- `Smart Strong <http://pythonhosted.org/Markdown/extensions/smart_strong.html>`_
- `Admonition <http://pythonhosted.org/Markdown/extensions/admonition.html>`_
- `CodeHilite <http://pythonhosted.org/Markdown/extensions/code_hilite.html>`_
- `Sane lists <http://pythonhosted.org/Markdown/extensions/sane_lists.html>`_

README files can also rely on:

- `Abbreviations <http://pythonhosted.org/Markdown/extensions/abbreviations.html>`_
- `Foonotes <http://pythonhosted.org/Markdown/extensions/footnotes.html>`_
- `Table of Contents <http://pythonhosted.org/Markdown/extensions/toc.html>`_

While comments use:

- `New Line to Break <http://pythonhosted.org/Markdown/extensions/nl2br.html>`_


Styling
-------

..  role:: strike
     :class: strike

You can mark up text with bold, italics, or strikethrough.

* **Style**: Bold
    * Syntax: `** **` or `__ __`
    * Example: `**This is bold text**`
    * Output: **This is bold text**
* **Style**: Italics
    * Syntax: `* *` or `_ _`
    * Example: `_This is italicized text_`
    * Output: *This is italicized text*
* **Style**: Strikethrough
    * Syntax: `~~ ~~`
    * Example: `~~This text is no longer relevant~~`
    * Output: :strike:`This text is no longer relevant`
* **Style**: Bold and italics
    * Syntax: `** **` and `_ _`
    * Example: `** This text is the _most important thing ever_ **`
    * Output: ** This text is the *most important thing ever* **


Quoting
-------

You can show text as being quoted with the `>` character.

::

    Before merging this pull request, remember Clark Kent mentioned this:
    > Double-check there's no reference to the Kryptonite library in the program since we removed that a few versions ago.


Before merging this pull request, remember Clark Kent mentioned this:
> Double-check there's no reference to the Kryptonite library in the program since we removed that a few versions ago.


Code
----

You can highlight parts of a line as code or create entire code blocks in
your Markdown documents. You can do this with the backtick character (`).
Text inside of backticks will not be formatted.

::

    When running the program for the first time, use `superman --initialize`.


When running the program for the first time, use ``superman --initialize``.

To format multiple lines of code into its own block, you can wrap the text
block with four tilde (~) characters

::

    Install the needed system libraries:
    `~~~~`
    sudo dnf install git python-virtualenv libgit2-devel \
                    libjpeg-devel gcc libffi-devel redhat-rpm-config
    `~~~~`



Install the needed system libraries:

::

    sudo dnf install git python-virtualenv libgit2-devel \
                 libjpeg-devel gcc libffi-devel redhat-rpm-config



Hyperlinks
----------

Need to embed a link to somewhere else? No problem! You can create an
in-line link by wrapping the text in `[ ]` and appending the the URL in
parentheses `( )` immediately after.

`Pagure is used by the [Fedora Project](https://fedoraproject.org).`

Pagure is used by the `Fedora Project <https://fedoraproject.org>`_.


Lists
-----

Unordered lists
^^^^^^^^^^^^^^^

You can make unordered lists spanning multiple lines with either `-` or `*`.

::

    * Superman
    * Batman
        * Protector of Gotham City!
    * Superwoman
    * Harley Quinn
        * Something on this list is unlike the others...


* Superman
* Batman
    * Protector of Gotham City!
* Superwoman
* Harley Quinn
    * Something on this list is unlike the others...

Ordered lists
^^^^^^^^^^^^^

You can make ordered lists by preceding each line with a number.

::

    1. Superman
    2. Batman
        1. Protector of Gotham City!
        2. He drives the Batmobile!
    3. Superwoman
    4. Harley Quinn
        1. Something on this list is unlike the others...
        2. Somebody evil lurks on this list!


1. Superman
2. Batman
    1. Protector of Gotham City!
    2. He drives the Batmobile!
3. Superwoman
4. Harley Quinn
    1. Something on this list is unlike the others...
    2. Somebody evil lurks on this list!


Tagging users
-------------

You can tag other users on Pagure to send them a notification about an issue
or pull request. To tag a user, use the `@` symbol followed by their username.
Typing the `@` symbol in a comment will bring up a list of users that match
the username. The list searches as you type. Once you see the name of the
person you are looking for, you can click their name to automatically
complete the tag.

`@jflory7, could you please review this pull request and leave feedback?`

`@jflory7 <https://pagure.io/user/jflory7>`_, could you please review this pull request and leave feedback?


Tagging issues or pull requests
-------------------------------

In a comment, you can automatically link a pull request or issue by its number.
To link it, use the `#` character followed by its number. Like with tagging
users, Pagure will provide suggestions for issues or pull requests as you
type the number. You can select the issue in the drop-down to automatically
tag the issue or pull request.

If you need to tag an issue or pull request that is outside of the current
project, you are also able to do this. For cross-projects links, you can tag
them by typing `<project name>#id` or `<username>/<project name>#id`.


Emoji
-----

Pagure natively supports emoji characters. To use emoji, you can use two
colons wrapped around the emoji keyword (`:emoji:`). Typing a colon by itself
will bring up a list of suggested emoji with a small preview. If you see the
one you're looking for, you can click it to automatically complete the emoji.

`I reviewed the PR and it looks good to me. :+1: Good to merge! :clapper:`

I reviewed the PR and it looks good to me. 👍 Good to merge! 🎬


Improve this documentation!
---------------------------

Notice anything that can be improved in this documentation? Find a mistake?
You can improve this page! Find it in the official
`Pagure repository <https://pagure.io/pagure/blob/master/f/doc/usage/markdown.md>`_.
