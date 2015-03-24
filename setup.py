#!/usr/bin/env python

"""
Setup script
"""

# Required to build on EL6
__requires__ = ['SQLAlchemy >= 0.8', 'jinja2 >= 2.4']
import pkg_resources

from setuptools import setup
from pagure import __version__


def get_requirements(requirements_file='requirements.txt'):
    """Get the contents of a file listing the requirements.

    :arg requirements_file: path to a requirements file
    :type requirements_file: string
    :returns: the list of requirements, or an empty list if
              `requirements_file` could not be opened or read
    :return type: list
    """

    lines = open(requirements_file).readlines()
    return [
        line.rstrip().split('#')[0]
        for line in lines
        if not line.startswith('#')
    ]


setup(
    name='pagure',
    description='A light-weight git-centered forge based on pygit2..',
    version=__version__,
    author='Pierre-Yves Chibon',
    author_email='pingou@pingoured.fr',
    maintainer='Pierre-Yves Chibon',
    maintainer_email='pingou@pingoured.fr',
    license='GPLv2+',
    download_url='https://fedorahosted.org/releases/p/r/pagure/',
    url='https://fedorahosted.org/pagure/',
    packages=['pagure'],
    include_package_data=True,
    install_requires=get_requirements(),
)
