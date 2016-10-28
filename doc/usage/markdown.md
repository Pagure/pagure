Using Markdown in Pagure
========================
<<<<<<< ec0860623a3726b654c4ad94ab755cf250ed73c6
<<<<<<< 528343f4c9211d8a01eca7650f807fc2470317da
<<<<<<< 554748685c760f70e542cdc05dc5373b56de5348
<<<<<<< 5babdd5746cc3345502180b67c7f9ae56bdbb00f
<<<<<<< bf156df08f90f220fdfa78462558ae94ee175a67
<<<<<<< ad0b1fdbfeed4d3673342cdad9a43d4b22372fe1
=======
=======
<<<<<<< 263c38469dae0fae410763fd9771669806f85a2c
>>>>>>> Include cross-project tagging in markdown doc
<<<<<<< a1b2164b3344830e82cc7e2d76734582ae511d3e
>>>>>>> Add documentation for using Markdown in Pagure

Pagure uses [Markdown syntax highlighting](https://daringfireball.net/projects/markdown/syntax) as the base for formatting comments in issues, pull requests, and in Markdown files in repositories. For basic formatting, Pagure follows common Markdown formatting, but it also has some unique syntax for more advanced formatting. This help page helps demonstrate how to use Markdown in Pagure.
<<<<<<< 0e389d26d6d16167ecd4dbe881964058fbdd7daf
<<<<<<< 7a26dcdc244c554fdf467408143a0f7850f5d1cd


## Headers

To create headings, you will use the `#` symbol before the text. The number of hashes before the text determines the header size.

~~~~
# header1
## header2
### header3
~~~~
=======
<<<<<<< ec0860623a3726b654c4ad94ab755cf250ed73c6
<<<<<<< 528343f4c9211d8a01eca7650f807fc2470317da
=======

>>>>>>> Include cross-project tagging in markdown doc
=======
>>>>>>> Add documentation for using Markdown in Pagure
=======

>>>>>>> Include cross-project tagging in markdown doc
=======
>>>>>>> Add documentation for using Markdown in Pagure
=======
=======

>>>>>>> Include cross-project tagging in markdown doc
>>>>>>> Include cross-project tagging in markdown doc
Pagure uses [Markdown syntax highlighting](https://daringfireball.net/projects/markdown/syntax)
as the base for formatting comments in issues, pull requests, and in
Markdown files in repositories. For basic formatting, Pagure follows
common Markdown formatting, but it also has some unique syntax for more
advanced formatting. This help page helps demonstrate how to use Markdown
in Pagure.
<<<<<<< 528343f4c9211d8a01eca7650f807fc2470317da
<<<<<<< 5babdd5746cc3345502180b67c7f9ae56bdbb00f
=======
>>>>>>> Update file based on hotfix to staging, update documentation for code blocks


## Headers

To create headings, you will use the `#` symbol before the text. The number of hashes before the text determines the header size.

~~~~
# header1
## header2
<<<<<<< 7a26dcdc244c554fdf467408143a0f7850f5d1cd
=======

&nbsp;

## Headers

To create headings, you will use the `#` symbol before the text. The
number of hashes before the text determines the header size.

<pre><code># header1
## header2
>>>>>>> Add documentation for using Markdown in Pagure
### header3</code></pre>

<hr />
>>>>>>> Add documentation for using Markdown in Pagure
<<<<<<< 528343f4c9211d8a01eca7650f807fc2470317da
=======
### header3
~~~~
>>>>>>> Update file based on hotfix to staging, update documentation for code blocks
=======
=======
>>>>>>> Update file based on hotfix to staging, update documentation for code blocks


## Headers

To create headings, you will use the `#` symbol before the text. The number of hashes before the text determines the header size.

~~~~
# header1
## header2
<<<<<<< 0e389d26d6d16167ecd4dbe881964058fbdd7daf
### header3</code></pre>

<hr />
>>>>>>> Add documentation for using Markdown in Pagure
=======
### header3
~~~~
>>>>>>> Update file based on hotfix to staging, update documentation for code blocks
=======
>>>>>>> Add documentation for using Markdown in Pagure

# header 1

## header2

### header3

<<<<<<< 528343f4c9211d8a01eca7650f807fc2470317da
<<<<<<< 0e389d26d6d16167ecd4dbe881964058fbdd7daf
<<<<<<< 5babdd5746cc3345502180b67c7f9ae56bdbb00f
<<<<<<< 7a26dcdc244c554fdf467408143a0f7850f5d1cd
<<<<<<< ad0b1fdbfeed4d3673342cdad9a43d4b22372fe1
=======
<<<<<<< a1b2164b3344830e82cc7e2d76734582ae511d3e
>>>>>>> Add documentation for using Markdown in Pagure
=======
<hr />

&nbsp;
>>>>>>> Add documentation for using Markdown in Pagure
<<<<<<< 528343f4c9211d8a01eca7650f807fc2470317da
=======
>>>>>>> Update file based on hotfix to staging, update documentation for code blocks
=======
<hr />

&nbsp;
>>>>>>> Add documentation for using Markdown in Pagure
=======
>>>>>>> Update file based on hotfix to staging, update documentation for code blocks
=======
>>>>>>> Add documentation for using Markdown in Pagure

## Styling

You can mark up text with bold, italics, or strikethrough.

* **Style**: Bold
    * Syntax: `** **` or `__ __`
    * Example: `**This is bold text**`
    * Output: **This is bold text**
* **Style**: Italics
    * Syntax: `* *` or `_ _`
    * Example: `_This is italicized text_`
    * Output: _This is italicized text_
* **Style**: Strikethrough
    * Syntax: `~~ ~~`
    * Example: `~~This text is no longer relevant~~`
    * Output: ~~This text is no longer relevant~~
* **Style**: Bold and italics
    * Syntax: `** **` and `_ _`
    * Example: `**This text is the _most important thing ever_**`
    * Output: **This text is the _most important thing ever_**

<<<<<<< 528343f4c9211d8a01eca7650f807fc2470317da
<<<<<<< 0e389d26d6d16167ecd4dbe881964058fbdd7daf
<<<<<<< 5babdd5746cc3345502180b67c7f9ae56bdbb00f
<<<<<<< 7a26dcdc244c554fdf467408143a0f7850f5d1cd
<<<<<<< ad0b1fdbfeed4d3673342cdad9a43d4b22372fe1
=======
&nbsp;
>>>>>>> Add documentation for using Markdown in Pagure
=======
>>>>>>> Update file based on hotfix to staging, update documentation for code blocks
=======
&nbsp;
>>>>>>> Add documentation for using Markdown in Pagure
=======
>>>>>>> Update file based on hotfix to staging, update documentation for code blocks
=======
<<<<<<< a1b2164b3344830e82cc7e2d76734582ae511d3e
=======
&nbsp;
>>>>>>> Add documentation for using Markdown in Pagure
>>>>>>> Add documentation for using Markdown in Pagure

## Quoting

You can show text as being quoted with the `>` character.

<<<<<<< 528343f4c9211d8a01eca7650f807fc2470317da
<<<<<<< 0e389d26d6d16167ecd4dbe881964058fbdd7daf
<<<<<<< 5babdd5746cc3345502180b67c7f9ae56bdbb00f
<<<<<<< 7a26dcdc244c554fdf467408143a0f7850f5d1cd
<<<<<<< ad0b1fdbfeed4d3673342cdad9a43d4b22372fe1
=======
>>>>>>> Update file based on hotfix to staging, update documentation for code blocks
=======
>>>>>>> Update file based on hotfix to staging, update documentation for code blocks
=======
<<<<<<< a1b2164b3344830e82cc7e2d76734582ae511d3e
>>>>>>> Add documentation for using Markdown in Pagure
~~~~
Before merging this pull request, remember Clark Kent mentioned this:
> Double-check there's no reference to the Kryptonite library in the program since we removed that a few versions ago.
~~~~
<<<<<<< 0e389d26d6d16167ecd4dbe881964058fbdd7daf
<<<<<<< 7a26dcdc244c554fdf467408143a0f7850f5d1cd

Before merging this pull request, remember Clark Kent mentioned this:
> Double-check there's no reference to the Kryptonite library in the program since we removed that a few versions ago.


## Code

You can highlight parts of a line as code or create entire code blocks in your Markdown documents. You can do this with the backtick character (`). Text inside of backticks will not be formatted.

~~~~
When running the program for the first time, use `superman --initialize`.
~~~~

When running the program for the first time, use `superman --initialize`.

To format multiple lines of code into its own block, you can wrap the text block with four tilde (~) characters

~~~~
Install the needed system libraries:
`~~~~`
sudo dnf install git python-virtualenv libgit2-devel \
                 libjpeg-devel gcc libffi-devel redhat-rpm-config
`~~~~`
~~~~


Install the needed system libraries:

~~~~
sudo dnf install git python-virtualenv libgit2-devel \
                 libjpeg-devel gcc libffi-devel redhat-rpm-config
~~~~


## Hyperlinks

Need to embed a link to somewhere else? No problem! You can create an in-line link by wrapping the text in `[ ]` and appending the the URL in parentheses `( )` immediately after.
=======
=======
>>>>>>> Add documentation for using Markdown in Pagure
<pre>Before merging this pull request, remember Clark Kent mentioned this:
> Double-check there's no reference to the Kryptonite library in the
> program since we removed that a few versions ago.</pre>

&nbsp;
<<<<<<< 5babdd5746cc3345502180b67c7f9ae56bdbb00f
=======
>>>>>>> Update file based on hotfix to staging, update documentation for code blocks

Before merging this pull request, remember Clark Kent mentioned this:
> Double-check there's no reference to the Kryptonite library in the program since we removed that a few versions ago.


## Code

You can highlight parts of a line as code or create entire code blocks in your Markdown documents. You can do this with the backtick character (`). Text inside of backticks will not be formatted.

~~~~
When running the program for the first time, use `superman --initialize`.
~~~~

When running the program for the first time, use `superman --initialize`.

To format multiple lines of code into its own block, you can wrap the text block with four tilde (~) characters

~~~~
Install the needed system libraries:
`~~~~`
sudo dnf install git python-virtualenv libgit2-devel \
                 libjpeg-devel gcc libffi-devel redhat-rpm-config
`~~~~`
~~~~


Install the needed system libraries:

~~~~
sudo dnf install git python-virtualenv libgit2-devel \
                 libjpeg-devel gcc libffi-devel redhat-rpm-config
~~~~


## Hyperlinks

<<<<<<< 7a26dcdc244c554fdf467408143a0f7850f5d1cd
Need to embed a link to somewhere else? No problem! You can create an in-
line link by wrapping the text in `[ ]` and appending the the URL in
parentheses `( )` immediately after.
>>>>>>> Add documentation for using Markdown in Pagure
=======
Need to embed a link to somewhere else? No problem! You can create an in-line link by wrapping the text in `[ ]` and appending the the URL in parentheses `( )` immediately after.
>>>>>>> Update file based on hotfix to staging, update documentation for code blocks
=======
=======
>>>>>>> Update file based on hotfix to staging, update documentation for code blocks

Before merging this pull request, remember Clark Kent mentioned this:
> Double-check there's no reference to the Kryptonite library in the program since we removed that a few versions ago.


## Code

You can highlight parts of a line as code or create entire code blocks in your Markdown documents. You can do this with the backtick character (`). Text inside of backticks will not be formatted.

~~~~
When running the program for the first time, use `superman --initialize`.
~~~~

When running the program for the first time, use `superman --initialize`.

To format multiple lines of code into its own block, you can wrap the text block with four tilde (~) characters

~~~~
Install the needed system libraries:
`~~~~`
sudo dnf install git python-virtualenv libgit2-devel \
                 libjpeg-devel gcc libffi-devel redhat-rpm-config
`~~~~`
~~~~


Install the needed system libraries:

~~~~
sudo dnf install git python-virtualenv libgit2-devel \
                 libjpeg-devel gcc libffi-devel redhat-rpm-config
~~~~


## Hyperlinks

<<<<<<< 0e389d26d6d16167ecd4dbe881964058fbdd7daf
Need to embed a link to somewhere else? No problem! You can create an in-
line link by wrapping the text in `[ ]` and appending the the URL in
parentheses `( )` immediately after.
>>>>>>> Add documentation for using Markdown in Pagure
=======
Need to embed a link to somewhere else? No problem! You can create an in-line link by wrapping the text in `[ ]` and appending the the URL in parentheses `( )` immediately after.
<<<<<<< 528343f4c9211d8a01eca7650f807fc2470317da
>>>>>>> Update file based on hotfix to staging, update documentation for code blocks
=======
=======
<pre>Before merging this pull request, remember Clark Kent mentioned this:
> Double-check there's no reference to the Kryptonite library in the
> program since we removed that a few versions ago.</pre>

&nbsp;

Before merging this pull request, remember Clark Kent mentioned this:
> Double-check there's no reference to the Kryptonite library in the
> program since we removed that a few versions ago.

&nbsp;

## Code

You can highlight parts of a line as code or create entire code blocks in
your Markdown documents. Text inside of backticks will not be formatted.

<pre>When running the program for the first time, use `superman --initialize`.</pre>

When running the program for the first time, use `superman --initialize`.

&nbsp;

To format multiple lines of code into its own block, you will need to use
raw HTML with the &lsaquo;pre&rsaquo;&lsaquo;/pre&rsaquo; tags.

<pre>Install the needed system libraries:
&lsaquo;pre&rsaquo;
sudo dnf install git python-virtualenv libgit2-devel \
                 libjpeg-devel gcc libffi-devel redhat-rpm-config
&lsaquo;pre&rsaquo;</pre>

&nbsp;

Install the needed system libraries:
<pre>
sudo dnf install git python-virtualenv libgit2-devel \
                 libjpeg-devel gcc libffi-devel redhat-rpm-config
</pre>

&nbsp;

## Hyperlinks

Need to embed a link to somewhere else? No problem! You can create an in-
line link by wrapping the text in `[ ]` and appending the the URL in
parentheses `( )` immediately after.
>>>>>>> Add documentation for using Markdown in Pagure
>>>>>>> Add documentation for using Markdown in Pagure

`Pagure is used by the [Fedora Project](https://fedoraproject.org).`

Pagure is used by the [Fedora Project](https://fedoraproject.org).

<<<<<<< 528343f4c9211d8a01eca7650f807fc2470317da
<<<<<<< 0e389d26d6d16167ecd4dbe881964058fbdd7daf
<<<<<<< 5babdd5746cc3345502180b67c7f9ae56bdbb00f
<<<<<<< 7a26dcdc244c554fdf467408143a0f7850f5d1cd
<<<<<<< ad0b1fdbfeed4d3673342cdad9a43d4b22372fe1

## Lists

#### Unordered lists

You can make unordered lists spanning multiple lines with either `-` or `*`.

~~~~
* Superman
=======
&nbsp;
=======
>>>>>>> Update file based on hotfix to staging, update documentation for code blocks

## Lists

#### Unordered lists

<<<<<<< 7a26dcdc244c554fdf467408143a0f7850f5d1cd
<pre>* Superman
>>>>>>> Add documentation for using Markdown in Pagure
=======
You can make unordered lists spanning multiple lines with either `-` or `*`.

~~~~
* Superman
>>>>>>> Update file based on hotfix to staging, update documentation for code blocks
=======
&nbsp;
=======
>>>>>>> Update file based on hotfix to staging, update documentation for code blocks
=======
<<<<<<< a1b2164b3344830e82cc7e2d76734582ae511d3e
>>>>>>> Add documentation for using Markdown in Pagure

## Lists

#### Unordered lists

<<<<<<< 0e389d26d6d16167ecd4dbe881964058fbdd7daf
<pre>* Superman
>>>>>>> Add documentation for using Markdown in Pagure
=======
You can make unordered lists spanning multiple lines with either `-` or `*`.

~~~~
* Superman
<<<<<<< 528343f4c9211d8a01eca7650f807fc2470317da
>>>>>>> Update file based on hotfix to staging, update documentation for code blocks
=======
=======
&nbsp;

## Lists

You can make unordered lists spanning multiple lines with either `-` or
`*`.

<pre>* Superman
>>>>>>> Add documentation for using Markdown in Pagure
>>>>>>> Add documentation for using Markdown in Pagure
* Batman
    * Protector of Gotham City!
* Superwoman
* Harley Quinn
<<<<<<< 528343f4c9211d8a01eca7650f807fc2470317da
<<<<<<< 0e389d26d6d16167ecd4dbe881964058fbdd7daf
<<<<<<< 5babdd5746cc3345502180b67c7f9ae56bdbb00f
<<<<<<< 7a26dcdc244c554fdf467408143a0f7850f5d1cd
<<<<<<< ad0b1fdbfeed4d3673342cdad9a43d4b22372fe1
    * Something on this list is unlike the others...
~~~~
=======
    * Something on this list is unlike the others...</pre>
>>>>>>> Add documentation for using Markdown in Pagure
=======
    * Something on this list is unlike the others...
~~~~
>>>>>>> Update file based on hotfix to staging, update documentation for code blocks
=======
    * Something on this list is unlike the others...</pre>
>>>>>>> Add documentation for using Markdown in Pagure
=======
    * Something on this list is unlike the others...
~~~~
>>>>>>> Update file based on hotfix to staging, update documentation for code blocks
=======
<<<<<<< a1b2164b3344830e82cc7e2d76734582ae511d3e
    * Something on this list is unlike the others...
~~~~
=======
    * Something on this list is unlike the others...</pre>
>>>>>>> Add documentation for using Markdown in Pagure
>>>>>>> Add documentation for using Markdown in Pagure

* Superman
* Batman
    * Protector of Gotham City!
* Superwoman
* Harley Quinn
    * Something on this list is unlike the others...

<<<<<<< 528343f4c9211d8a01eca7650f807fc2470317da
<<<<<<< 0e389d26d6d16167ecd4dbe881964058fbdd7daf
<<<<<<< 5babdd5746cc3345502180b67c7f9ae56bdbb00f
<<<<<<< 7a26dcdc244c554fdf467408143a0f7850f5d1cd
<<<<<<< ad0b1fdbfeed4d3673342cdad9a43d4b22372fe1
#### Ordered lists

You can make ordered lists by preceding each line with a number.

~~~~
1. Superman
=======
=======
>>>>>>> Add documentation for using Markdown in Pagure
&nbsp;

You can make ordered lists by preceding each line with a number.

<pre>1. Superman
<<<<<<< 5babdd5746cc3345502180b67c7f9ae56bdbb00f
>>>>>>> Add documentation for using Markdown in Pagure
=======
#### Ordered lists

You can make ordered lists by preceding each line with a number.

~~~~
1. Superman
>>>>>>> Update file based on hotfix to staging, update documentation for code blocks
=======
>>>>>>> Add documentation for using Markdown in Pagure
=======
=======
<<<<<<< a1b2164b3344830e82cc7e2d76734582ae511d3e
>>>>>>> Add documentation for using Markdown in Pagure
#### Ordered lists

You can make ordered lists by preceding each line with a number.

~~~~
1. Superman
<<<<<<< 528343f4c9211d8a01eca7650f807fc2470317da
>>>>>>> Update file based on hotfix to staging, update documentation for code blocks
=======
=======
&nbsp;

You can make ordered lists by preceding each line with a number.

<pre>1. Superman
>>>>>>> Add documentation for using Markdown in Pagure
>>>>>>> Add documentation for using Markdown in Pagure
2. Batman
    1. Protector of Gotham City!
    2. He drives the Batmobile!
3. Superwoman
4. Harley Quinn
    1. Something on this list is unlike the others...
<<<<<<< 528343f4c9211d8a01eca7650f807fc2470317da
<<<<<<< 0e389d26d6d16167ecd4dbe881964058fbdd7daf
<<<<<<< 5babdd5746cc3345502180b67c7f9ae56bdbb00f
<<<<<<< 7a26dcdc244c554fdf467408143a0f7850f5d1cd
<<<<<<< ad0b1fdbfeed4d3673342cdad9a43d4b22372fe1
    2. Somebody evil lurks on this list!
~~~~
=======
    2. Somebody evil lurks on this list!</pre>
>>>>>>> Add documentation for using Markdown in Pagure
=======
    2. Somebody evil lurks on this list!
~~~~
>>>>>>> Update file based on hotfix to staging, update documentation for code blocks
=======
    2. Somebody evil lurks on this list!</pre>
>>>>>>> Add documentation for using Markdown in Pagure
=======
    2. Somebody evil lurks on this list!
~~~~
>>>>>>> Update file based on hotfix to staging, update documentation for code blocks
=======
<<<<<<< a1b2164b3344830e82cc7e2d76734582ae511d3e
    2. Somebody evil lurks on this list!
~~~~
=======
    2. Somebody evil lurks on this list!</pre>
>>>>>>> Add documentation for using Markdown in Pagure
>>>>>>> Add documentation for using Markdown in Pagure

1. Superman
2. Batman
    1. Protector of Gotham City!
    2. He drives the Batmobile!
3. Superwoman
4. Harley Quinn
    1. Something on this list is unlike the others...
    2. Somebody evil lurks on this list!

<<<<<<< 528343f4c9211d8a01eca7650f807fc2470317da
<<<<<<< 0e389d26d6d16167ecd4dbe881964058fbdd7daf
<<<<<<< 5babdd5746cc3345502180b67c7f9ae56bdbb00f
<<<<<<< 7a26dcdc244c554fdf467408143a0f7850f5d1cd
<<<<<<< ad0b1fdbfeed4d3673342cdad9a43d4b22372fe1
=======
<<<<<<< a1b2164b3344830e82cc7e2d76734582ae511d3e
>>>>>>> Add documentation for using Markdown in Pagure

## Tagging users

You can tag other users on Pagure to send them a notification about an issue or pull request. To tag a user, use the `@` symbol followed by their username. Typing the `@` symbol in a comment will bring up a list of users that match the username. The list searches as you type. Once you see the name of the person you are looking for, you can click their name to automatically complete the tag.

`@jflory7, could you please review this pull request and leave feedback?`

[@jflory7](https://pagure.io/user/jflory7), could you please review this pull request and leave feedback?


## Tagging issues or pull requests

In a comment, you can automatically link a pull request or issue by its number. To link it, use the `#` character followed by its number. Like with tagging users, Pagure will provide suggestions for issues or pull requests as you type the number. You can select the issue in the drop-down to automatically tag the issue or pull request.

If you need to tag an issue or pull request that is outside of the current project, you are also able to do this. For cross-projects links, you can tag them by typing `<project name>#id` or `<username>/<project name>#id`.


## Emoji

Pagure natively supports emoji characters. To use emoji, you can use two colons wrapped around the emoji keyword (`:emoji:`). Typing a colon by itself will bring up a list of suggested emoji with a small preview. If you see the one you're looking for, you can click it to automatically complete the emoji.
=======
&nbsp;
<<<<<<< 528343f4c9211d8a01eca7650f807fc2470317da
=======
>>>>>>> Update file based on hotfix to staging, update documentation for code blocks

## Tagging users

You can tag other users on Pagure to send them a notification about an issue or pull request. To tag a user, use the `@` symbol followed by their username. Typing the `@` symbol in a comment will bring up a list of users that match the username. The list searches as you type. Once you see the name of the person you are looking for, you can click their name to automatically complete the tag.

`@jflory7, could you please review this pull request and leave feedback?`

[@jflory7](https://pagure.io/user/jflory7), could you please review this pull request and leave feedback?


## Tagging issues or pull requests

In a comment, you can automatically link a pull request or issue by its number. To link it, use the `#` character followed by its number. Like with tagging users, Pagure will provide suggestions for issues or pull requests as you type the number. You can select the issue in the drop-down to automatically tag the issue or pull request.

If you need to tag an issue or pull request that is outside of the current project, you are also able to do this. For cross-projects links, you can tag them by typing `<project name>#id` or `<username>/<project name>#id`.


## Emoji

<<<<<<< 7a26dcdc244c554fdf467408143a0f7850f5d1cd
=======
&nbsp;
=======
>>>>>>> Update file based on hotfix to staging, update documentation for code blocks

## Tagging users

You can tag other users on Pagure to send them a notification about an issue or pull request. To tag a user, use the `@` symbol followed by their username. Typing the `@` symbol in a comment will bring up a list of users that match the username. The list searches as you type. Once you see the name of the person you are looking for, you can click their name to automatically complete the tag.

`@jflory7, could you please review this pull request and leave feedback?`

[@jflory7](https://pagure.io/user/jflory7), could you please review this pull request and leave feedback?


## Tagging issues or pull requests

In a comment, you can automatically link a pull request or issue by its number. To link it, use the `#` character followed by its number. Like with tagging users, Pagure will provide suggestions for issues or pull requests as you type the number. You can select the issue in the drop-down to automatically tag the issue or pull request.

If you need to tag an issue or pull request that is outside of the current project, you are also able to do this. For cross-projects links, you can tag them by typing `<project name>#id` or `<username>/<project name>#id`.


## Emoji

<<<<<<< 0e389d26d6d16167ecd4dbe881964058fbdd7daf
>>>>>>> Add documentation for using Markdown in Pagure
=======

## Tagging users

You can tag other users on Pagure to send them a notification about an
issue or pull request. To tag a user, use the `@` symbol followed by their
username. Typing the `@` symbol in a comment will bring up a list of users
that match the username. The list searches as you type. Once you see the
name of the person you are looking for, you can click their name to
automatically complete the tag.

`@jflory7, could you please review this pull request and leave feedback?`

[@jflory7](https://pagure.io/user/jflory7), could you please review this
pull request and leave feedback?

&nbsp;

## Tagging issues or pull requests

In a comment, you can automatically link a pull request or issue by its
number. To link it, use the `#` character followed by its number. Like
with tagging users, Pagure will provide suggestions for issues or pull
requests as you type the number. You can select the issue in the drop-down
to automatically tag the issue or pull request.

If you need to tag an issue or pull request that is outside of the current
project, you are also able to do this. For cross-projects links, you can
tag them by typing `<project name>#id` or `<username>/<project name>#id`.

&nbsp;

## Emoji

>>>>>>> Add documentation for using Markdown in Pagure
Pagure natively supports emoji characters. To use emoji, you can use two
colons wrapped around the emoji keyword (`:emoji:`). Typing a colon by
itself will bring up a list of suggested emoji with a small preview. If
you see the one you're looking for, you can click it to automatically
complete the emoji.
<<<<<<< 528343f4c9211d8a01eca7650f807fc2470317da
<<<<<<< 5babdd5746cc3345502180b67c7f9ae56bdbb00f
>>>>>>> Add documentation for using Markdown in Pagure
=======
Pagure natively supports emoji characters. To use emoji, you can use two colons wrapped around the emoji keyword (`:emoji:`). Typing a colon by itself will bring up a list of suggested emoji with a small preview. If you see the one you're looking for, you can click it to automatically complete the emoji.
>>>>>>> Update file based on hotfix to staging, update documentation for code blocks
=======
>>>>>>> Add documentation for using Markdown in Pagure
=======
Pagure natively supports emoji characters. To use emoji, you can use two colons wrapped around the emoji keyword (`:emoji:`). Typing a colon by itself will bring up a list of suggested emoji with a small preview. If you see the one you're looking for, you can click it to automatically complete the emoji.
>>>>>>> Update file based on hotfix to staging, update documentation for code blocks
=======
>>>>>>> Add documentation for using Markdown in Pagure
>>>>>>> Add documentation for using Markdown in Pagure

`I reviewed the PR and it looks good to me. :+1: Good to merge! :clapper:`

I reviewed the PR and it looks good to me. :+1: Good to merge! :clapper:

<<<<<<< 528343f4c9211d8a01eca7650f807fc2470317da
<<<<<<< 0e389d26d6d16167ecd4dbe881964058fbdd7daf
<<<<<<< 5babdd5746cc3345502180b67c7f9ae56bdbb00f
<<<<<<< 7a26dcdc244c554fdf467408143a0f7850f5d1cd
<<<<<<< ad0b1fdbfeed4d3673342cdad9a43d4b22372fe1

## Improve this documentation!

Notice anything that can be improved in this documentation? Find a mistake? You can improve this page! Find it in the official [Pagure repository](https://pagure.io/pagure/blob/master/f/doc/usage/markdown.md).
=======
=======
>>>>>>> Add documentation for using Markdown in Pagure
&nbsp;

## Improve this documentation!

Notice anything that can be improved in this documentation? Find a
mistake? You can improve this page! Find it in the official [Pagure
repository](https://pagure.io/pagure/blob/master/f/doc/usage/markdown.md).
<<<<<<< 5babdd5746cc3345502180b67c7f9ae56bdbb00f
>>>>>>> Add documentation for using Markdown in Pagure
=======

## Improve this documentation!

Notice anything that can be improved in this documentation? Find a mistake? You can improve this page! Find it in the official [Pagure repository](https://pagure.io/pagure/blob/master/f/doc/usage/markdown.md).
>>>>>>> Update file based on hotfix to staging, update documentation for code blocks
=======
>>>>>>> Add documentation for using Markdown in Pagure
=======
=======
<<<<<<< a1b2164b3344830e82cc7e2d76734582ae511d3e
>>>>>>> Add documentation for using Markdown in Pagure

## Improve this documentation!

Notice anything that can be improved in this documentation? Find a mistake? You can improve this page! Find it in the official [Pagure repository](https://pagure.io/pagure/blob/master/f/doc/usage/markdown.md).
<<<<<<< 528343f4c9211d8a01eca7650f807fc2470317da
>>>>>>> Update file based on hotfix to staging, update documentation for code blocks
=======
=======
&nbsp;

## Improve this documentation!

Notice anything that can be improved in this documentation? Find a
mistake? You can improve this page! Find it in the official [Pagure
repository](https://pagure.io/pagure/blob/master/f/doc/usage/markdown.md).
>>>>>>> Add documentation for using Markdown in Pagure
>>>>>>> Add documentation for using Markdown in Pagure
