#!/usr/bin/env python

"""
Setup script
"""

import os
import re

from setuptools import setup


pagurefile = os.path.join(os.path.dirname(__file__), "pagure", "__init__.py")

# Thanks to SQLAlchemy:
# https://github.com/zzzeek/sqlalchemy/blob/master/setup.py#L104
with open(pagurefile) as stream:
    __version__ = (
        re.compile(r".*__version__ = \"(.*?)\"", re.S)
        .match(stream.read())
        .group(1)
    )


def get_requirements(requirements_file="requirements.txt"):
    """Get the contents of a file listing the requirements.

    :arg requirements_file: path to a requirements file
    :type requirements_file: string
    :returns: the list of requirements, or an empty list if
              `requirements_file` could not be opened or read
    :return type: list
    """

    with open(requirements_file) as f:
        return [
            line.rstrip().split("#")[0]
            for line in f.readlines()
            if not line.startswith("#")
        ]


setup(
    name="pagure",
    description="A light-weight git-centered forge based on pygit2.",
    version=__version__,
    author="Pierre-Yves Chibon",
    author_email="pingou@pingoured.fr",
    maintainer="Pierre-Yves Chibon",
    maintainer_email="pingou@pingoured.fr",
    license="GPLv2+",
    download_url="https://pagure.io/releases/pagure/",
    url="https://pagure.io/pagure/",
    packages=["pagure"],
    include_package_data=True,
    install_requires=get_requirements(),
    entry_points="""
    [console_scripts]
    pagure-admin=pagure.cli.admin:main

    [pagure.git_auth.helpers]
    test_auth = pagure.lib.git_auth:GitAuthTestHelper
    gitolite2 = pagure.lib.git_auth:Gitolite2Auth
    gitolite3 = pagure.lib.git_auth:Gitolite3Auth
    pagure = pagure.lib.git_auth:PagureGitAuth
    pagure_authorized_keys = pagure.lib.git_auth:PagureGitAuth
    """,
    classifiers=[
        "License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
        "Topic :: Software Development :: Bug Tracking",
        "Topic :: Software Development :: Version Control",
    ],
)
