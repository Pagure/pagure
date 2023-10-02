# -*- coding: utf-8 -*-

"""
 (c) 2014-2020 - Copyright Red Hat Inc

 Authors:
   Ralph Bean <rbean@redhat.com>
   Pierre-Yves Chibon <pingou@pingoured.fr>
   Julen Landa Alustiza <jlanda@fedoraproject.org>

"""

from __future__ import absolute_import, unicode_literals

import textwrap

import docutils
import docutils.core
import docutils.examples

try:
    from markupsafe import escape
except ImportError:
    from jinja2 import escape
import kitchen.text.converters as ktc
from markupsafe import Markup

import pagure.lib.encoding_utils
import pagure.lib.query
from pagure.config import config as pagure_config


def modify_rst(rst, view_file_url=None):
    """Downgrade some of our rst directives if docutils is too old."""
    if view_file_url:
        rst = rst.replace(".. image:: ", ".. image:: %s" % view_file_url)

    # We catch Exception if we want :-p
    # pylint: disable=broad-except
    try:
        # The rst features we need were introduced in this version
        minimum = [0, 9]
        version = [int(cpt) for cpt in docutils.__version__.split(".")]

        # If we're at or later than that version, no need to downgrade
        if version >= minimum:
            return rst
    except Exception:  # pragma: no cover
        # If there was some error parsing or comparing versions, run the
        # substitutions just to be safe.
        pass

    # On Fedora this will never work as the docutils version is to recent
    # Otherwise, make code-blocks into just literal blocks.
    substitutions = {".. code-block:: javascript": "::"}  # pragma: no cover

    for old, new in substitutions.items():  # pragma: no cover
        rst = rst.replace(old, new)

    return rst  # pragma: no cover


def modify_html(html):
    """Perform style substitutions where docutils doesn't do what we want."""

    substitutions = {
        '<tt class="docutils literal">': "<code>",
        "</tt>": "</code>",
        "$$FLAG_STATUSES_COMMAS$$": ", ".join(
            sorted(pagure_config["FLAG_STATUSES_LABELS"].keys())
        ),
        "$$FLAG_SUCCESS$$": pagure_config["FLAG_SUCCESS"],
        "$$FLAG_FAILURE$$": pagure_config["FLAG_FAILURE"],
        "$$FLAG_PENDING$$": pagure_config["FLAG_PENDING"],
    }
    for old, new in substitutions.items():
        html = html.replace(old, new)

    return html


def convert_doc(rst_string, view_file_url=None):
    """Utility to load an RST file and turn it into fancy HTML."""
    rst = modify_rst(rst_string, view_file_url)

    overrides = {"report_level": "quiet"}
    try:
        html = docutils.core.publish_parts(
            source=rst, writer_name="html", settings_overrides=overrides
        )
    except Exception:
        return "<pre>%s</pre>" % escape(rst)

    else:

        html_string = html["html_body"]

        html_string = modify_html(html_string)

        html_string = Markup(html_string)
        return html_string


def convert_readme(content, ext, view_file_url=None):
    """Convert the provided content according to the extension of the file
    provided.
    """
    output = pagure.lib.encoding_utils.decode(ktc.to_bytes(content))
    safe = False
    if ext and ext in [".rst"]:
        safe = True
        output = convert_doc(output, view_file_url)
    elif ext and ext in [".mk", ".md", ".markdown"]:
        output = pagure.lib.query.text2markdown(output, readme=True)
        safe = True
    elif not ext or (ext and ext in [".text", ".txt"]):
        safe = True
        output = "<pre>%s</pre>" % escape(output)
    return output, safe


def load_doc(endpoint):
    """Utility to load an RST file and turn it into fancy HTML."""

    rst = modify_rst(textwrap.dedent(endpoint.__doc__))

    api_docs = docutils.examples.html_body(rst)

    api_docs = modify_html(api_docs)

    api_docs = Markup(api_docs)
    return api_docs


def load_doc_title(endpoint):
    """Utility to load docstring title from a method"""
    rst = modify_rst(textwrap.dedent(endpoint.__doc__))

    parts = docutils.examples.html_parts(rst)
    fragment = parts["title"]

    return fragment


def load_doc_title_and_name(endpoint):
    """Utility to load the HTML doc version and the title from a method."""

    result = {
        "doc": load_doc(endpoint),
        "title": load_doc_title(endpoint),
        "name": endpoint.__name__,
    }

    return result
