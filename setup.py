#!/usr/bin/env python

"""
Setup script
"""

# Required to build on EL6
__requires__ = ['SQLAlchemy >= 0.8', 'jinja2 >= 2.4']
import pkg_resources
import os
import re

from setuptools import setup


pagurefile = os.path.join(os.path.dirname(__file__), 'pagure', '__init__.py')

# Thanks to SQLAlchemy:
# https://github.com/zzzeek/sqlalchemy/blob/master/setup.py#L104
with open(pagurefile) as stream:
    __version__ = re.compile(
        r".*__version__ = '(.*?)'", re.S
    ).match(stream.read()).group(1)


def get_requirements(requirements_file='requirements.txt'):
    """Get the contents of a file listing the requirements.

    :arg requirements_file: path to a requirements file
    :type requirements_file: string
    :returns: the list of requirements, or an empty list if
              `requirements_file` could not be opened or read
    :return type: list
    """

    with open(requirements_file) as f:
        return [
            line.rstrip().split('#')[0]
            for line in f.readlines()
            if not line.startswith('#')
        ]


setup(
    name='pagure',
    description='A light-weight git-centered forge based on pygit2.',
    version=__version__,
    author='Pierre-Yves Chibon',
    author_email='pingou@pingoured.fr',
    maintainer='Pierre-Yves Chibon',
    maintainer_email='pingou@pingoured.fr',
    license='GPLv2+',
    download_url='https://pagure.io/releases/pagure/',
    url='https://pagure.io/pagure/',
    packages=['pagure'],
    include_package_data=True,
    install_requires=get_requirements(),
    entry_points="""
    [pygments.styles]
    diffstyle = pagure.ui.diff_style:DiffStyle
    """,
    classifiers=[
        'License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Topic :: Internet :: WWW/HTTP :: WSGI :: Application',
        'Topic :: Software Development :: Bug Tracking',
        'Topic :: Software Development :: Version Control',
    ]
)
