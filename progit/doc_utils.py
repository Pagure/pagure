#-*- coding: utf-8 -*-

"""
 (c) 2014 - Copyright Red Hat Inc

 Authors:
   Ralph Bean <rbean@redhat.com>
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

import docutils
import docutils.core
import markupsafe
import markdown


def modify_rst(rst):
    """ Downgrade some of our rst directives if docutils is too old. """

    ## We catch Exception if we want :-p
    # pylint: disable=W0703
    try:
        # The rst features we need were introduced in this version
        minimum = [0, 9]
        version = [int(cpt) for cpt in docutils.__version__.split('.')]

        # If we're at or later than that version, no need to downgrade
        if version >= minimum:
            return rst
    except Exception:  # pragma: no cover
        # If there was some error parsing or comparing versions, run the
        # substitutions just to be safe.
        pass

    # On Fedora this will never work as the docutils version is to recent
    # Otherwise, make code-blocks into just literal blocks.
    substitutions = {  # pragma: no cover
        '.. code-block:: javascript': '::',
    }
    for old, new in substitutions.items():  # pragma: no cover
        rst = rst.replace(old, new)

    return rst  # pragma: no cover


def modify_html(html):
    """ Perform style substitutions where docutils doesn't do what we want.
    """

    substitutions = {
        '<tt class="docutils literal">': '<code>',
        '</tt>': '</code>',
    }
    for old, new in substitutions.items():
        html = html.replace(old, new)

    return html


def convert_doc(rst_string):
    """ Utility to load an RST file and turn it into fancy HTML. """
    rst = modify_rst(rst_string)

    overrides = {'report_level': 'quiet'}
    html = docutils.core.publish_parts(
        source=rst,
        writer_name='html',
        settings_overrides=overrides)

    html_string = html['html_body']

    html_string = modify_html(html_string)

    html_string = markupsafe.Markup(html_string)
    return html_string


def convert_readme(content, ext):
    ''' Convert the provided content according to the extension of the file
    provided.
    '''
    output = content
    if ext and ext in ['.rst']:
        output = convert_doc(unicode(content))
    elif ext and ext in ['.mk']:
        output = markdown.markdown(content)
    return output
