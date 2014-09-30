ProGit
======

:Author: Pierre-Yves Chibon <pingou@pingoured.fr>


ProGit isa light-weight web-interface for git repo based on pygit2.

Ultimately, there are bigger plans for ProGit but let's start small and
improve from there.

Homepage: https://github.com/pypingou/ProGit

Dev instance: http://209.132.184.222/ (/!\ May change unexpectedly, it's a dev instance ;-))



Get it running
==============

* Retrieve the sources::

    git clone git://github.com/pypingou/progit


* Create the folder that will receive the projects, forks, docs and tickets'
  git repo::

    mkdir {repos,docs,forks,tickets}


* Run it::

    ./runserver.py


This will launch the application at http://127.0.0.1:5000
