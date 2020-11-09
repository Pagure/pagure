%{?python_enable_dependency_generator}

%if 0%{?rhel} && 0%{?rhel} < 8
# Since the Python 3 stack in EPEL is missing too many dependencies,
# we're sticking with Python 2 there for now.
%global __python %{__python2}
%global python_pkgversion %{nil}
%else
# Default to Python 3 when not EL
%global __python %{__python3}
%global python_pkgversion %{python3_pkgversion}
%endif

# For now, to keep behavior consistent
%global _python_bytecompile_extra 1


Name:               pagure
Version:            5.11.3
Release:            1%{?dist}
Summary:            A git-centered forge

License:            GPLv2+
URL:                https://pagure.io/pagure
Source0:            https://pagure.io/releases/pagure/%{name}-%{version}.tar.gz

BuildArch:          noarch

BuildRequires:      systemd-devel
BuildRequires:      systemd
BuildRequires:      python%{python_pkgversion}-devel
BuildRequires:      python%{python_pkgversion}-setuptools

%if 0%{?rhel} && 0%{?rhel} < 8
# Required only for the `fas` and `openid` authentication backends
Requires:           python%{python_pkgversion}-fedora-flask
# Required only for the `oidc` authentication backend
# flask-oidc
# Required only if `USE_FLASK_SESSION_EXT` is set to `True`
# flask-session
%else
Recommends:         python%{python_pkgversion}-fedora-flask
%endif

# We require OpenSSH 7.4+ for SHA256 support
Requires:           openssh >= 7.4

%if %{undefined python_enable_dependency_generator} && %{undefined python_disable_dependency_generator}
Requires:           python%{python_pkgversion}-alembic
Requires:           python%{python_pkgversion}-arrow
Requires:           python%{python_pkgversion}-bcrypt
Requires:           python%{python_pkgversion}-binaryornot
Requires:           python%{python_pkgversion}-bleach
Requires:           python%{python_pkgversion}-blinker
Requires:           python%{python_pkgversion}-celery
Requires:           python%{python_pkgversion}-chardet
Requires:           python%{python_pkgversion}-cryptography
Requires:           python%{python_pkgversion}-docutils
%if ! (0%{?rhel} && 0%{?rhel} < 8)
Requires:           python%{python_pkgversion}-email-validator
%endif
Requires:           python%{python_pkgversion}-enum34
Requires:           python%{python_pkgversion}-flask
Requires:           python%{python_pkgversion}-flask-wtf
Requires:           python%{python_pkgversion}-flask-oidc
Requires:           python%{python_pkgversion}-markdown
Requires:           python%{python_pkgversion}-munch
Requires:           python%{python_pkgversion}-pillow
Requires:           python%{python_pkgversion}-psutil
Requires:           python%{python_pkgversion}-pygit2 >= 0.26.0
Requires:           python%{python_pkgversion}-openid
Requires:           python%{python_pkgversion}-openid-cla
Requires:           python%{python_pkgversion}-openid-teams
Requires:           python%{python_pkgversion}-redis
Requires:           python%{python_pkgversion}-requests
Requires:           python%{python_pkgversion}-six
Requires:           python%{python_pkgversion}-sqlalchemy >= 0.8
Requires:           python%{python_pkgversion}-straight-plugin
Requires:           python%{python_pkgversion}-whitenoise
Requires:           python%{python_pkgversion}-wtforms
%endif

%{?systemd_requires}

# No dependency of the app per se, but required to make it working.
Requires:           gitolite3

%description
Pagure is a light-weight git-centered forge based on pygit2.

Currently, Pagure offers a web-interface for git repositories, a ticket
system and possibilities to create new projects, fork existing ones and
create/merge pull-requests across or within projects.


%package            web-apache-httpd
Summary:            Apache HTTPD configuration for Pagure
BuildArch:          noarch
Requires:           %{name} = %{version}-%{release}
%if 0%{?rhel} && 0%{?rhel} < 8
Requires:           mod_wsgi
%else
Requires:           httpd-filesystem
Requires:           python%{python_pkgversion}-mod_wsgi
%endif
%description        web-apache-httpd
This package provides the configuration files for deploying
a Pagure server using the Apache HTTPD server.


%package            web-nginx
Summary:            Nginx configuration for Pagure
BuildArch:          noarch
Requires:           %{name} = %{version}-%{release}
Requires:           nginx-filesystem
Requires:           python%{python_pkgversion}-gunicorn
%description        web-nginx
This package provides the configuration files for deploying
a Pagure server using the Nginx web server.


%package            theme-pagureio
Summary:            Web interface theme used for Pagure.io
BuildArch:          noarch
Requires:           %{name} = %{version}-%{release}
%description        theme-pagureio
This package provides the web interface assets for styling
a Pagure server with the same look and feel as Pagure.io.


%package            theme-srcfpo
Summary:            Web interface theme used for src.fedoraproject.org
BuildArch:          noarch
Requires:           %{name} = %{version}-%{release}
%description        theme-srcfpo
This package provides the web interface assets for styling
a Pagure server with the same look and feel as src.fedoraproject.org.


%package            theme-chameleon
Summary:            Web interface based on openSUSE's chameleon theme
BuildArch:          noarch
Requires:           %{name} = %{version}-%{release}
%description        theme-chameleon
This package provides the web interface assets for styling
a Pagure server with the same look and feel as openSUSE Infrastructure.


%package            milters
Summary:            Milter to integrate pagure with emails
BuildArch:          noarch
Requires:           %{name} = %{version}-%{release}
Requires:           python%{python_pkgversion}-pymilter
%{?systemd_requires}
# It would work with sendmail but we configure things (like the tempfile)
# to work with postfix
Requires:           postfix
%description        milters
Milters (Mail filters) allowing the integration of pagure and emails.
This is useful for example to allow commenting on a ticket by email.


%package            ev
Summary:            EventSource server for pagure
BuildArch:          noarch
Requires:           %{name} = %{version}-%{release}
Requires:           python%{python_pkgversion}-trololio
%{?systemd_requires}
%description        ev
Pagure comes with an eventsource server allowing live update of the pages
supporting it. This package provides it.


%package            webhook
Summary:            Web-Hook server for pagure
BuildArch:          noarch
Requires:           %{name} = %{version}-%{release}
%{?systemd_requires}
%description        webhook
Pagure comes with an webhook server allowing http callbacks for any action
done on a project. This package provides it.


%package            ci
Summary:            A CI service for pagure
BuildArch:          noarch
Requires:           %{name} = %{version}-%{release}
Requires:           python%{python_pkgversion}-cryptography
Requires:           python%{python_pkgversion}-jenkins
%{?systemd_requires}
%description        ci
Pagure comes with a continuous integration service, currently supporting
only jenkins but extendable to others.
With this service, your CI server will be able to report the results of the
build on the pull-requests opened to your project.


%package            logcom
Summary:            The logcom service for pagure
BuildArch:          noarch
Requires:           %{name} = %{version}-%{release}
%{?systemd_requires}
%description        logcom
pagure-logcom contains the service that logs commits into the database so that
the activity calendar heatmap is filled.


%package            loadjson
Summary:            The loadjson service for pagure
BuildArch:          noarch
Requires:           %{name} = %{version}-%{release}
%{?systemd_requires}
%description        loadjson
pagure-loadjson is the service allowing to update the database with the
information provided in the JSON blobs that are stored in the tickets (and
in the future pull-requests) git repo.


%package            mirror
Summary:            The mirroring service for pagure
BuildArch:          noarch
Requires:           %{name} = %{version}-%{release}
%{?systemd_requires}
%description        mirror
pagure-mirror is the service mirroring projects that asked for it outside
of this pagure instance.


%prep
%autosetup -p1

%if 0%{?rhel} && 0%{?rhel} < 8
# Fix requirements.txt for EL7 setuptools
## Remove environment markers, as they're not supported
sed -e "s/;python_version.*$//g" -i requirements.txt
## Drop email-validator requirement
sed -e "s/^email_validator.*//g" -i requirements.txt
## Drop python3-openid requirement
sed -e "s/^python3-openid$//g" -i requirements.txt
%endif


%build
%py_build


%install
%py_install

# Install apache configuration file
mkdir -p $RPM_BUILD_ROOT/%{_sysconfdir}/httpd/conf.d/
install -p -m 644 files/pagure-apache-httpd.conf $RPM_BUILD_ROOT/%{_sysconfdir}/httpd/conf.d/pagure.conf

# Install nginx configuration file
mkdir -p $RPM_BUILD_ROOT/%{_sysconfdir}/nginx/conf.d/
install -p -m 644 files/pagure-nginx.conf $RPM_BUILD_ROOT/%{_sysconfdir}/nginx/conf.d/pagure.conf

# Install configuration file
mkdir -p $RPM_BUILD_ROOT/%{_sysconfdir}/pagure
install -p -m 644 files/pagure.cfg.sample $RPM_BUILD_ROOT/%{_sysconfdir}/pagure/pagure.cfg

# Install WSGI file
mkdir -p $RPM_BUILD_ROOT/%{_datadir}/pagure
install -p -m 644 files/pagure.wsgi $RPM_BUILD_ROOT/%{_datadir}/pagure/pagure.wsgi
install -p -m 644 files/doc_pagure.wsgi $RPM_BUILD_ROOT/%{_datadir}/pagure/doc_pagure.wsgi

# Install the createdb script
install -p -m 644 createdb.py $RPM_BUILD_ROOT/%{_datadir}/pagure/pagure_createdb.py

# Install the api_key_expire_mail.py script
install -p -m 644 files/api_key_expire_mail.py $RPM_BUILD_ROOT/%{_datadir}/pagure/api_key_expire_mail.py

# Install the mirror_project_in.py script
install -p -m 644 files/mirror_project_in.py $RPM_BUILD_ROOT/%{_datadir}/pagure/mirror_project_in.py

# Install the keyhelper and aclcheck scripts
mkdir -p $RPM_BUILD_ROOT/%{_libexecdir}/pagure/
install -p -m 755 files/aclchecker.py $RPM_BUILD_ROOT/%{_libexecdir}/pagure/aclchecker.py
install -p -m 755 files/keyhelper.py $RPM_BUILD_ROOT/%{_libexecdir}/pagure/keyhelper.py

# Install the alembic configuration file
install -p -m 644 files/alembic.ini $RPM_BUILD_ROOT/%{_sysconfdir}/pagure/alembic.ini

# Install the alembic revisions
cp -r alembic $RPM_BUILD_ROOT/%{_datadir}/pagure

# Install the systemd file for the web frontend
mkdir -p $RPM_BUILD_ROOT/%{_unitdir}
install -p -m 644 files/pagure_web.service \
    $RPM_BUILD_ROOT/%{_unitdir}/pagure_web.service

# Install the systemd file for the docs web frontend
mkdir -p $RPM_BUILD_ROOT/%{_unitdir}
install -p -m 644 files/pagure_docs_web.service \
    $RPM_BUILD_ROOT/%{_unitdir}/pagure_docs_web.service

# Install the systemd file for the worker
mkdir -p $RPM_BUILD_ROOT/%{_unitdir}
install -p -m 644 files/pagure_worker.service \
    $RPM_BUILD_ROOT/%{_unitdir}/pagure_worker.service

# Install the systemd file for the gitolite worker
install -p -m 644 files/pagure_gitolite_worker.service \
    $RPM_BUILD_ROOT/%{_unitdir}/pagure_gitolite_worker.service

# Install the systemd file for the web-hook
install -p -m 644 files/pagure_webhook.service \
    $RPM_BUILD_ROOT/%{_unitdir}/pagure_webhook.service

# Install the systemd file for the ci service
install -p -m 644 files/pagure_ci.service \
    $RPM_BUILD_ROOT/%{_unitdir}/pagure_ci.service

# Install the systemd file for the logcom service
install -p -m 644 files/pagure_logcom.service \
    $RPM_BUILD_ROOT/%{_unitdir}/pagure_logcom.service

# Install the systemd file for the loadjson service
install -p -m 644 files/pagure_loadjson.service \
    $RPM_BUILD_ROOT/%{_unitdir}/pagure_loadjson.service

# Install the systemd file for the mirror service
install -p -m 644 files/pagure_mirror.service \
    $RPM_BUILD_ROOT/%{_unitdir}/pagure_mirror.service

# Install the systemd file for the script sending reminder about API key
# expiration
install -p -m 644 files/pagure_api_key_expire_mail.service \
    $RPM_BUILD_ROOT/%{_unitdir}/pagure_api_key_expire_mail.service
install -p -m 644 files/pagure_api_key_expire_mail.timer \
    $RPM_BUILD_ROOT/%{_unitdir}/pagure_api_key_expire_mail.timer

# Install the systemd file for the script updating mirrored project
install -p -m 644 files/pagure_mirror_project_in.service \
    $RPM_BUILD_ROOT/%{_unitdir}/pagure_mirror_project_in.service
install -p -m 644 files/pagure_mirror_project_in.timer \
    $RPM_BUILD_ROOT/%{_unitdir}/pagure_mirror_project_in.timer

# Install the milter files
mkdir -p $RPM_BUILD_ROOT/%{_localstatedir}/run/pagure
mkdir -p $RPM_BUILD_ROOT/%{_tmpfilesdir}
install -p -m 0644 pagure-milters/milter_tempfile.conf \
    $RPM_BUILD_ROOT/%{_tmpfilesdir}/%{name}-milter.conf
install -p -m 644 pagure-milters/pagure_milter.service \
    $RPM_BUILD_ROOT/%{_unitdir}/pagure_milter.service
install -p -m 644 pagure-milters/comment_email_milter.py \
    $RPM_BUILD_ROOT/%{_datadir}/pagure/comment_email_milter.py

# Install the eventsource
mkdir -p $RPM_BUILD_ROOT/%{_libexecdir}/pagure-ev
install -p -m 755 pagure-ev/pagure_stream_server.py \
    $RPM_BUILD_ROOT/%{_libexecdir}/pagure-ev/pagure_stream_server.py
install -p -m 644 pagure-ev/pagure_ev.service \
    $RPM_BUILD_ROOT/%{_unitdir}/pagure_ev.service

# Fix the shebang for various scripts
sed -e "s|#!/usr/bin/env python|#!%{__python}|" -i \
    $RPM_BUILD_ROOT/%{_libexecdir}/pagure-ev/*.py \
    $RPM_BUILD_ROOT/%{_libexecdir}/pagure/*.py \
    $RPM_BUILD_ROOT/%{_datadir}/pagure/*.py \
    $RPM_BUILD_ROOT/%{python_sitelib}/pagure/hooks/files/*.py \
    $RPM_BUILD_ROOT/%{python_sitelib}/pagure/hooks/files/hookrunner \
    $RPM_BUILD_ROOT/%{python_sitelib}/pagure/hooks/files/post-receive \
    $RPM_BUILD_ROOT/%{python_sitelib}/pagure/hooks/files/pre-receive \
    $RPM_BUILD_ROOT/%{python_sitelib}/pagure/hooks/files/repospannerhook

# Switch interpreter for systemd units
sed -e "s|/usr/bin/python|%{__python}|g" -i $RPM_BUILD_ROOT/%{_unitdir}/*.service

%if ! (0%{?rhel} && 0%{?rhel} < 8)
# Switch all systemd units to use the correct celery
sed -e "s|/usr/bin/celery|/usr/bin/celery-3|g" -i $RPM_BUILD_ROOT/%{_unitdir}/*.service

# Switch all systemd units to use the correct gunicorn
sed -e "s|/usr/bin/gunicorn|/usr/bin/gunicorn-3|g" -i $RPM_BUILD_ROOT/%{_unitdir}/*.service
%endif

# Make log directories
mkdir -p $RPM_BUILD_ROOT/%{_localstatedir}/log/pagure
logfiles="web docs_web"

for logfile in $logfiles; do
   touch $RPM_BUILD_ROOT/%{_localstatedir}/log/pagure/access_${logfile}.log
   touch $RPM_BUILD_ROOT/%{_localstatedir}/log/pagure/error_${logfile}.log
done

# Regenerate missing symlinks (really needed for upgrades from pagure < 5.0)
runnerhooks="post-receive pre-receive"

for runnerhook in $runnerhooks; do
   rm -rf $RPM_BUILD_ROOT/%{python_sitelib}/pagure/hooks/files/$runnerhook
   ln -sf hookrunner $RPM_BUILD_ROOT/%{python_sitelib}/pagure/hooks/files/$runnerhook
done

%if 0%{?fedora} || 0%{?rhel} >= 8
# Byte compile everything not in sitelib
%py_byte_compile %{__python} %{buildroot}%{_datadir}/pagure/
%py_byte_compile %{__python} %{buildroot}%{_libexecdir}/pagure/
%py_byte_compile %{__python} %{buildroot}%{_libexecdir}/pagure-ev/
%endif

%post
%systemd_post pagure_worker.service
%systemd_post pagure_gitolite_worker.service
%systemd_post pagure_api_key_expire_mail.timer
%systemd_post pagure_mirror_project_in.timer
%post web-nginx
%systemd_post pagure_web.service
%systemd_post pagure_docs_web.service
%post milters
%systemd_post pagure_milter.service
%post ev
%systemd_post pagure_ev.service
%post webhook
%systemd_post pagure_webhook.service
%post ci
%systemd_post pagure_ci.service
%post logcom
%systemd_post pagure_logcom.service
%post loadjson
%systemd_post pagure_loadjson.service
%post mirror
%systemd_post pagure_mirror.service

%preun
%systemd_preun pagure_worker.service
%systemd_preun pagure_gitolite_worker.service
%systemd_preun pagure_api_key_expire_mail.timer
%systemd_preun pagure_mirror_project_in.timer
%preun web-nginx
%systemd_preun pagure_web.service
%systemd_preun pagure_docs_web.service
%preun milters
%systemd_preun pagure_milter.service
%preun ev
%systemd_preun pagure_ev.service
%preun webhook
%systemd_preun pagure_webhook.service
%preun ci
%systemd_preun pagure_ci.service
%preun logcom
%systemd_preun pagure_logcom.service
%preun loadjson
%systemd_preun pagure_loadjson.service
%preun mirror
%systemd_preun pagure_mirror.service

%postun
%systemd_postun_with_restart pagure_worker.service
%systemd_postun_with_restart pagure_gitolite_worker.service
%systemd_postun pagure_api_key_expire_mail.timer
%systemd_postun pagure_mirror_project_in.timer
%postun web-nginx
%systemd_postun_with_restart pagure_web.service
%systemd_postun_with_restart pagure_docs_web.service
%postun milters
%systemd_postun_with_restart pagure_milter.service
%postun ev
%systemd_postun_with_restart pagure_ev.service
%postun webhook
%systemd_postun_with_restart pagure_webhook.service
%postun ci
%systemd_postun_with_restart pagure_ci.service
%postun logcom
%systemd_postun_with_restart pagure_logcom.service
%postun loadjson
%systemd_postun_with_restart pagure_loadjson.service
%postun mirror
%systemd_postun_with_restart pagure_mirror.service


%files
%doc README.rst UPGRADING.rst doc/
%license LICENSE
%config(noreplace) %{_sysconfdir}/pagure/pagure.cfg
%config(noreplace) %{_sysconfdir}/pagure/alembic.ini
%dir %{_sysconfdir}/pagure/
%dir %{_datadir}/pagure/
%{_datadir}/pagure/*.py*
%if ! (0%{?rhel} && 0%{?rhel} < 8)
%{_datadir}/pagure/__pycache__/
%endif
%{_datadir}/pagure/alembic/
%{_libexecdir}/pagure/
%{python_sitelib}/pagure/
%exclude %{python_sitelib}/pagure/themes/pagureio
%exclude %{python_sitelib}/pagure/themes/srcfpo
%exclude %{python_sitelib}/pagure/themes/chameleon
%{python_sitelib}/pagure*.egg-info
%{_bindir}/pagure-admin
%{_unitdir}/pagure_worker.service
%{_unitdir}/pagure_gitolite_worker.service
%{_unitdir}/pagure_api_key_expire_mail.service
%{_unitdir}/pagure_api_key_expire_mail.timer
%{_unitdir}/pagure_mirror_project_in.service
%{_unitdir}/pagure_mirror_project_in.timer
%dir %{_localstatedir}/log/pagure


%files web-apache-httpd
%license LICENSE
%config(noreplace) %{_sysconfdir}/httpd/conf.d/pagure.conf
%config(noreplace) %{_datadir}/pagure/*.wsgi


%files web-nginx
%license LICENSE
%config(noreplace) %{_sysconfdir}/nginx/conf.d/pagure.conf
%{_unitdir}/pagure_web.service
%{_unitdir}/pagure_docs_web.service
%ghost %{_localstatedir}/log/pagure/access_*.log
%ghost %{_localstatedir}/log/pagure/error_*.log


%files theme-pagureio
%license LICENSE
%{python_sitelib}/pagure/themes/pagureio/


%files theme-srcfpo
%license LICENSE
%{python_sitelib}/pagure/themes/srcfpo/


%files theme-chameleon
%license LICENSE
%{python_sitelib}/pagure/themes/chameleon/


%files milters
%license LICENSE
%attr(755,postfix,postfix) %dir %{_localstatedir}/run/pagure
%dir %{_datadir}/pagure/
%{_tmpfilesdir}/%{name}-milter.conf
%{_unitdir}/pagure_milter.service
%{_datadir}/pagure/comment_email_milter.py*


%files ev
%license LICENSE
%{_libexecdir}/pagure-ev/
%{_unitdir}/pagure_ev.service


%files webhook
%license LICENSE
%{_unitdir}/pagure_webhook.service


%files ci
%license LICENSE
%{_unitdir}/pagure_ci.service


%files logcom
%license LICENSE
%{_unitdir}/pagure_logcom.service


%files loadjson
%license LICENSE
%{_unitdir}/pagure_loadjson.service


%files mirror
%license LICENSE
%{_unitdir}/pagure_mirror.service


%changelog
* Tue Aug 11 2020 Pierre-Yves Chibon <pingou@pingoured.fr> - 5.11.3-1
- Update to 5.11.3

* Tue Aug 04 2020 Pierre-Yves Chibon <pingou@pingoured.fr> - 5.11.2-1
- Update to 5.11.2

* Mon Aug 03 2020 Pierre-Yves Chibon <pingou@pingoured.fr> - 5.11.1-1
- Update to 5.11.1

* Mon Aug 03 2020 Pierre-Yves Chibon <pingou@pingoured.fr> - 5.11.0-1
- Update to 5.11.0

* Thu May 14 2020 Pierre-Yves Chibon <pingou@pingoured.fr> - 5.10.0-1
- Update to 5.10.0

* Mon Mar 30 2020 Pierre-Yves Chibon <pingou@pingoured.fr> - 5.9.1-1
- Update to 5.9.1

* Tue Mar 24 2020 Pierre-Yves Chibon <pingou@pingoured.fr> - 5.9.0-1
- Update to 5.9.0

* Mon Dec 02 2019 Pierre-Yves Chibon <pingou@pingoured.fr> - 5.8.1-1
- Update to 5.8.1

* Fri Nov 15 2019 Pierre-Yves Chibon <pingou@pingoured.fr> - 5.8-1
- Update to 5.8

* Sat Aug 10 2019 Pierre-Yves Chibon <pingou@pingoured.fr> - 5.7.4-1
- Update to 5.7.4

* Fri Aug 02 2019 Pierre-Yves Chibon <pingou@pingoured.fr> - 5.7.3-1
- Update to pagure 5.7.3

* Tue Jul 30 2019 Pierre-Yves Chibon <pingou@pingoured.fr> - 5.7.2-1
- Update to pagure 5.7.2

* Fri Jul 12 2019 Pierre-Yves Chibon <pingou@pingoured.fr> - 5.7.1-1
- Update to pagure 5.7.1

* Fri Jul 05 2019 Pierre-Yves Chibon <pingou@pingoured.fr> - 5.7-1
- Update to pagure 5.7

* Tue Jun 04 2019 Pierre-Yves Chibon <pingou@pingoured.fr> - 5.6-1
- Update to pagure 5.6

* Mon Apr 08 2019 Pierre-Yves Chibon <pingou@pingoured.fr> - 5.5-1
- Update to pagure 5.5

* Thu Mar 28 2019 Pierre-Yves Chibon <pingou@pingoured.fr> - 5.4-1
- Update to pagure 5.4

* Fri Feb 22 2019 Pierre-Yves Chibon <pingou@pingoured.fr> - 5.3-1
- Update to pagure 5.3

* Mon Jan 07 2019 Pierre-Yves Chibon <pingou@pingoured.fr> - 5.2-1
- Update to pagure 5.2

* Thu Oct 11 2018 Pierre-Yves Chibon <pingou@pingoured.fr> - 5.1.3-1
- Update to pagure 5.1.3

* Thu Oct 11 2018 Pierre-Yves Chibon <pingou@pingoured.fr> - 5.1.2-1
- Update to pagure 5.1.2

* Tue Oct 09 2018 Pierre-Yves Chibon <pingou@pingoured.fr> - 5.1.1-1
- Update to pagure 5.1.1

* Tue Oct 09 2018 Pierre-Yves Chibon <pingou@pingoured.fr> - 5.1-1
- Update to pagure 5.1

* Thu Sep 27 2018 Pierre-Yves Chibon <pingou@pingoured.fr> - 5.0.1-1
- Update to pagure 5.0.1

* Mon Sep 24 2018 Pierre-Yves Chibon <pingou@pingoured.fr> - 5.0-1
- Update to pagure 5.0

* Mon Sep 17 2018 Pierre-Yves Chibon <pingou@pingoured.fr> - 4.93.0-1
- Update to 4.93.0, fourth beta release of pagure 5.0

* Wed Aug 29 2018 Pierre-Yves Chibon <pingou@pingoured.fr> - 4.92.0-1
- Update to 4.92.0, third beta release of pagure 5.0

* Thu Aug 23 2018 Pierre-Yves Chibon <pingou@pingoured.fr> - 4.91.0-1
- Update to 4.91.0, second beta release of pagure 5.0

* Mon Aug 20 2018 Pierre-Yves Chibon <pingou@pingoured.fr> - 4.90.0-1
- Update to 4.90.0, first beta release of pagure 5.0

* Thu Jul 19 2018 Pierre-Yves Chibon <pingou@pingoured.fr> - 4.0.4-1
- Update to 4.0.4

* Mon May 14 2018 Pierre-Yves Chibon <pingou@pingoured.fr> - 4.0.3-1
- Update to 4.0.3

* Mon May 14 2018 Pierre-Yves Chibon <pingou@pingoured.fr> - 4.0.2-1
- Update to 4.0.2

* Thu Apr 26 2018 Pierre-Yves Chibon <pingou@pingoured.fr> - 4.0.1-1
- Update to 4.0.1

* Thu Apr 26 2018 Pierre-Yves Chibon <pingou@pingoured.fr> - 4.0-1
- Update to 4.0
- Changelog is from now on included in the doc/ folder

* Thu Dec 21 2017 Pierre-Yves Chibon <pingou@pingoured.fr> - 3.13.2-1
- Update to 3.13.2
- Fix ordering issues by author using an alias so the User doesn't collide

* Tue Dec 19 2017 Pierre-Yves Chibon <pingou@pingoured.fr> - 3.13.1-1
- Update to 3.13.1
- Add an alembic migration removing a constraint on the DB that not only no
  longer needed but even blocking regular use now

* Mon Dec 18 2017 Pierre-Yves Chibon <pingou@pingoured.fr> - 3.13-1
- Update to 3.13
- Fix the alembic migration adjusting the pull_requests table
- Fix how is created the db in the docker development environment (Clement
  Verna)
- Ensure optional dependencies remain optional
- Ensure groups cannot be created when it is not allowed
- When listing issues, include the project as well in the user's issue API
  endpoint
- Sort forks by date of creation (descending) (Neha Kandpal)
- Ensure the pagination arguments are returned when a page is specified
- Make the milestone clickable on the issue page
- Make the celery tasks update their status so we know when they are running (vs
  pending)

* Fri Dec 08 2017 Pierre-Yves Chibon <pingou@pingoured.fr> - 3.12-1
- Update to 3.12
- Adjust the API endpoint listing project to not return a 404 when not projects
  are found (Vivek Anand)
- Remove --autoreload from the docker dev deployment (Vivek Anand)
- Fix ordering issues (Patrick Uiterwijk)
- Do not log actions pertaining to private issues, PRs or projects
- Fix flagging a PR when no uid is specified
- Fix the doc about custom gitolite config
- Fix displaying the filename on the side and linking to file for remote PRs
- Add irc info in Readme (Vivek Anand)
- Make pagure compatible with newer python chardet
- Check that the identifier isn't the hash of a git tree in view_file
- Fix if the identifier provided is one of a blob instead of a commit in
  view_commit
- Include the status when flagging a PR via jenkins
- Enable OpenID Connect authentication (Slavek Kabrda)
- Use the updated timestamp in the pull-request list
- Add migration to fix the project_from_id foreign key in pull_requests
- Let the SSE server to send the notifications so they can be displayed live
- Improve the createdb script to support stamping the database in the initial
  run
- Specify a different connection and read timeout in pagure-ci
- Small CSS fix making the (un)subscribe show up on the PR page

* Wed Nov 29 2017 Pierre-Yves Chibon <pingou@pingoured.fr> - 3.11.2-1
- Update to 3.11.2
- Fix giving a project if no user is specified
- Don't show issue stats when issues are off

* Tue Nov 28 2017 Pierre-Yves Chibon <pingou@pingoured.fr> - 3.11.1-1
- Update to 3.11.1
- Fix showing the issue list
- Make clear in the project's settings that tags are also for PRs (Clement
  Verna)
- Remove unused jdenticon js library (Shengjing Zhu)

* Mon Nov 27 2017 Pierre-Yves Chibon <pingou@pingoured.fr> - 3.11-1
- Update to 3.11
- Print out the URL to existing PR(s) or to create one on push
- Reword the repository access warning (Matt Prahl)
- Add pagure-admin admin-token update to update the expiration date
- Fix the api_view_user_activity_stats to return the expected data (post flask
  0.11)
- Add small icon showing if issues are blocked or blocking in the issue list
- Replace all print statements with print function calls (Vadim Rutkovski)
- Add a default_priority field to projects
- Bail on merge a PR that is already closed
- Add a graph of the history of the open issues on the project
- Make the pagure hook act as the person doing the push
- Clean spec file to drop deprecated lines and macros (Igor Gnatenko)
- Include selectize in the settings page to fix the autocomplete in the give
  project action
- Do not display the close_status if there isn't one
- Do not show the `Fork and edit` button all the time
- Allow project maintainer to set metadata when creating a new issue (expand the
  API as well)
- Add a timeout when trying to query jenkins
- Show the reply button even if the PR/issue is closed.
- Add a diff view for PR
- Improve the `My star` page
- Introduce repo statistics
- When a project enforce signed-off-by, clearly say so on the new PR page and
  properly block the PR from being created
- Adjust button title on the 'Fork and Edit' action
- Fix typos in the code (chocos10)
- When editing an issue, act as the person who pushed the change
- Commit using the user's fullname if there is one, otherwise its username
- Expand the group info API endpoint
- Sorting on Opened, Modified, Closed, Priority, Reporter, Assignee cols (Mohan
  Boddu and Matt Prahl)
- Fix the Vagrant setup (Ryan Lerch)
- Fix typo in the example pagure.wsgi file (Vivek Anand)
- Add API endpoints for listing pull requests for a user (Ryan Lerch)
- Ask for the post-commit hook to be run when editing files via the UI
- Fix the milter for email gpg signed
- Allow filtering the user's project by access level
- Add a modal at the bottom of the issues list to add milestones
- Add a field to store the order of the milestones
- Hide the ``+`` button on the index page when it is disabled in the UI
- Improve mimetype detection (Shengjing Zhu and Clement Verna)
- Allow assignee to drop their assignment
- Remove duplicate [Pagure] from mail subjects (Stefan Bühler)
- Fix undefined 'path' in blame.html template (Stefan Bühler)
- Warn users when a project does not support direct push
- Update gitolite's config for the project when set to PR only
- Do not report the branch differing master if PRs have been turned off
- Add a button and an API endpoint to subscribe to PR's notifications
- Fix showing the file names in PR (pre)view
- Fix number of typos in the documentation (René Genz)
- Improve the documentation about documentation hosting in pagure (René Genz)
- Allow priorities and milestones to be 0 or -1
- Return the flag UID when adding or updating a flag on a PR not in fedmsg
- Add flags on commits
- Add documentation about flags on commits and PRs
- Add status fields to flags
- Make flag's UID be unique to the commit/PR being flagged
- Add API endpoint to retrieve all issues related to an user across all repos
- Fix the new PR and delete buttons for branch name with + in them
- When merging a PR, call the post-update hook on the target repo
- Add tags to pull-request
- Fix documentation for fork API endpoint (ishcherb)
- Send fedmsg messages when deleting a project (Shaily)

* Fri Oct 13 2017 Pierre-Yves Chibon <pingou@pingoured.fr> - 3.10.1-1
- Update to 3.10.1
- Fix providing access to some of the internal API endpoints by javascript

* Fri Oct 13 2017 Pierre-Yves Chibon <pingou@pingoured.fr> - 3.10-1
- Update to 3.10
- Show the branches' head in the commit list
- Log which IP is being denied access to the internal endpoints (makes debugging
  easier)
- Link to pagure's own markdown documentation and warn that remote images are
  not supported
- Document how to run a single test file or a single test in a file
- Fix trying to decode when the encoding is None
- Include an url_path field in the JSON representation of a project
- Generalize the description of the ACLs (since we know have project-less API
  tokens)
- Drop ``--autoreload`` from the .service files as celery dropped support for it
  and it never really worked (Vivek Anand)

* Wed Oct 11 2017 Pierre-Yves Chibon <pingou@pingoured.fr> - 3.9-1
- Update to 3.9
- Fix the editing issue when the user does not actually edit anything
- Fix the internal API endpoint: get branches of commit to support namespace
- Consolidate the code in our custom markdown processor (fixes linking to a
  commit on a namespaced project)
- Fix deleting a project by also removing it from the gitolite config
- Warn if the user is about to just recompile the gitolite config via
  pagure-admin (Patrick Uiterwijk)
- Update .git/config example in doc/usage/pull_requests.rst (sclark)
- Include the PRs opened by the user on the 'My pull-requests' page
- Add to pagure-admin the actions: get-watch and update-watch
- Add to pagure-admin the action: read-only
- Add the user's fullname (if there is one) as title when they comment
- Fix the title of the percentage when hovering over the red bar in issues
- Make the box to edit comments bigger
- Document in the usage section where to find the API documentation
- Provide the sha256 and sha512 of the releases in a CHECKSUMS file
- Remove clear buttons (Till Maas)

* Fri Sep 29 2017 Pierre-Yves Chibon <pingou@pingoured.fr> - 3.8-1
- Update to 3.8
- Fix API documentation for git/branch (Matt Prahl)
- Fix giving a project to someone who already has access (Matth Prahl)
- Add some border to the tables created in README files
- Ask the user to confirm merging a pull-request
- Fix processing status and close_status updates in the SSE
- Fix the URL to the issue used by the SSE JS on tags
- Increase the logging in the milter to help figuring out issues in the future
- Fix the In-Reply-To header when sending notifications
- Fix showing the delete project button
- Fix search issues with a unicode character
- Catch exception raised when accessing the head of the repo
- Fix deleting a project when some of the folder are not used
- Allow viewing a PR when its origin (fork or branch) is gone
- Fix linking to issue or PR in namespaced projects via #<id>
- Make it more obvious that the namespace and the project are different links
- Tell fedmsg to send things with pagure certificates (Patrick Uiterwijk)
- Fix loading ticket templates on namespaced project and extracting their names
- Add a banner on the overview page when the ACLs are being refreshed on the
  backend (and thus ssh access may not be entirely functional) (Vivek Anand)
- Update the documentation on how to create pull requests (Clement Verna)
- Add button to refresh external pull requests (Patrick Uiterwijk)
- Add the possibility to get the group members when asking the project info
- Make the PROJECT_NAME_REGEX used in form be configurable
- Adjust the milter to support replying with any email addresses associated
- Allow pagure admin to give a project

* Tue Sep 05 2017 Pierre-Yves Chibon <pingou@pingoured.fr> - 3.7.1-1
- Update to 3.7.1
- Fix the UPGRADING documentation
- Add the API endpoint to edit multiple custom fields to the doc (Clement
  Verna)

* Tue Sep 05 2017 Pierre-Yves Chibon <pingou@pingoured.fr> - 3.7-1
- Update to 3.7
- Update link to markdown documentation, fix typo on the way (Till Hofmann)
- Add feature allowing to prevent project creation in the UI only
- Remove the front whitespace from the commit markdown regex (Clement Verna)
- New API endpoint to modify multiple custom fields (Clement Verna)
- Update the example output of the API endpoint giving project information
- Add the ability to order issues by ascending or descending (Matt Prahl)
- Consolidate around pagure.lib.git.generate_gitolite_acls
- Regenerate the gitolite ACL when changing the main admin of a project
- Change the documentation link end point (Clement Verna)
- Fixes the README.rst file (Ompragash)
- Update Docker Environment (Clement Verna)
- Add a configuration key to allow deleting forks but not projects
- Show the entire project name in the UI on the delete button
- Add support for a custom user in the SSH URL
- Do not show the SSH url when the user isn't logged in
- Update the documentation on how to work with pull requests (Clement Verna)
- Support both JSON and Form POST on APIs that accepted only JSON (Matt Prahl)
- Don't expand groups in the watchers API (Ralph Bean)
- Add a new branch API (Matt Prahl)
- Add bash function example to PR documentation (Clement Verna)
- Add the star project feature (Vivek Anand)
- Update the overview diagram
- Fix the rendering of the API version in the html page (Clement Verna)
- Fix message-id not having FQDN (Sachin Kamath)
- Mention on what the rebase was done
- Remove the line numbers coming from pygments on pull-requests
- Include the targeted branch in the list of PRs
- Separately link user/namespace/name
- Fix the pagination when listing projects via the view_projects endpoints
- Retain access when transfering ownership of the project (Matt Prahl)

* Mon Aug 14 2017 Pierre-Yves Chibon <pingou@pingoured.fr> - 3.6-1
- Update to 3.6
- Blacklist creating a group named 'group'
- Allow having a dedicated worker to compile the gitolite configuration file
- Fix removing groups of a project
- Make the API returns only open issues by default (as documented) (Clement
  Verna)
- Improve the README regarding the use of eventlet to run the tests (Vivek
  Anand)
- Give Pagure site admins the ability to modify projects using the API (Matt
  Prahl)
- Add the "git/generateacls" API endpoint for projects (Matt Prahl)

* Tue Aug 08 2017 Pierre-Yves Chibon <pingou@pingoured.fr> - 3.5-1
- Update to 3.5
- Fix login when groups are managed outside
- Fix the ordering of the issues by priority using JS and its documentation
- Indicate the issue/PR status in the title of its link
- Correct typo in waiting page template: 'You task' -> 'Your task' (Hazel Smith)
- Fix redirect in search (Carl George)
- Fix removing users of a project
- Allow customizing the HTML title globally
- Drop the new line character and the '# end of body' message when loading the
  config
- Scroll to the comment section on clicking reply. (shivani)
- only show issues on the My Issue page if the issue tracker is on for the
  project (Vivek Anand)
- Update the refresh-gitolite action of pagure-admin for the new interface
  (turns out this wasn't in fact merged in 3.4)
- Add a configuration key to make pagure case sensitive
- Add an USER_ACLS configuration key
- Document the different API token ACLs configuration keys
- Fix syncing groups from external account sources (Patrick Uiterwijk)

* Mon Jul 31 2017 Pierre-Yves Chibon <pingou@pingoured.fr> - 3.4-1
- Update to 3.4
- Fix layout breakage in the doc
- Stop using readlines() to drop the trailing new line character
- Fix logging by properly formatting the message
- Fix the issue count in the My Issues page (Vivek Anand)
- Add a configuration key to disable deleting branches from the UI
- Add a configuration key to disable managing user's ssh key in pagure
- Fix the vagrant environment (Clement Verna)
- Fix branch support for the git blame view
- Update the PR ref when the PR is updated
- Add a configuration key to disable the deploy keys in a pagure instance
- Fix login when groups are managed outside of pagure
- Fix setting up the git hooks when there is no DOCS_FOLDER set
- Fix installing up the pagure hooks when there is no DOCS_FOLDER set

* Mon Jul 24 2017 Pierre-Yves Chibon <pingou@pingoured.fr> - 3.3.1-1
- Update to 3.3.1
- Fix typo in the alembic migration present in 3.3

* Mon Jul 24 2017 Pierre-Yves Chibon <pingou@pingoured.fr> - 3.3-1
- [SECURITY FIX] block private repo (read) access via ssh due to a bug on how we
  generated the gitolite config - CVE-2017-1002151 (Stefan Bühler)
- Add the date_modified to projects (Clement Verna)

* Fri Jul 14 2017 Pierre-Yves Chibon <pingou@pingoured.fr> - 3.2.1-1
- Fix a syntax error on the JS in the wait page

* Fri Jul 14 2017 Pierre-Yves Chibon <pingou@pingoured.fr> - 3.2-1
- Update to 3.2
- Use a decorator to check if a project has an issue tracker (Clement Verna)
- Optimize generating the gitolite configuration for group change
- Fix the issue_keys table for mysql
- Drop the load_from_disk script
- Fix next_url URL parameter on the login page not being used (Carlos Mogas da
  Silva)
- Support configuration where there are no docs folder and no tickets folder
- Show all the projects a group has access to
- Add pagination to the projects API (Matt Prahl)
- Simplify diff calculation (Carlos Mogas da Silva)
- Show the inline comment in the PR's comments by default (Clement Verna)
- Fix the URL in the API documentation for creating a new project (Matt Prahl)

* Tue Jul 04 2017 Pierre-Yves Chibon <pingou@pingoured.fr> - 3.1-1
- Update to 3.1
- Allow project-less API token to create new tickets
- Tips/tricks: add info on how to validate local user account without email
  verification (Vivek Anand)
- Optimize the generation of the gitolite configuration
- Improve logging and load only the plugin of interest instead of all of them
- Show the task's status on the wait page and avoid reloading the page
- Don't show '+' sign when GROUP_MNGT is off (Vivek Anand)

* Fri Jun 30 2017 Pierre-Yves Chibon <pingou@pingoured.fr> - 3.0-1
- Update to 3.0
- Since 2.90 celery has become a requirement as well as one of the queueing
  system it supports (pagure defaults to using redis)
- Multiple stability and performance improvements (mainly thanks to Patrick
  Uiterwijk)
- Fix the assignee value in fedmsg when assigning a ticket (Ricky Elrod)
- Make pagure support bleach 2.0.0 (Shengjing Zhu)
- Fixes in CI support (Tim Flink)
- Update the documentation
- Fix plain readme html escape (Shengjing Zhu)
- Refactor user existence code in API and UI (Abhijeet Kasurde)
- Add an API to modify a Pagure project's owner (Matt Prahl)
- Support for uploading multiple files to an issue at once
- Introduce the external committer feature
- Add the required groups feature
- Add an API endpoint to get the git urls of a project (Matt Prahl)
- Blacklist 'wait' as project name
- Add a border to the search box on the side bar to the documentation
- Add the list-id, list-archive and X-Auto-Response-Suppress email headers
- Add ways to customize the gitolite configuration file with snippets
- Return a 404 on private ticket if the user is not authenticated
- cleanup: move static js/css to vendor dir
- Limit the requests version as it conflicts with our chardet requirement
- Rename all the services to pagure-*
- Remove 'on <project name' - watch status dropdown (Vivek Anand)
- Create references for pull-request in the git repo for local checkout
- Use the entire list of users for the assignee field completion
- Fix searching for groups
- Make the search work when searching for project with namespaces or forks
- Return a human-friendly error message when upload fails
- Let acting on the status potentially set the close_status and vice versa
- Multiple fixes to the SSE server
- When forking a project, wait until the very end to let the user go through
- Allow customizing the writing of gitolite's configuration file
- Fix diffing the branch of a project against the target branch
- Fix displaying the new PR button on the default branch
- Do not send a notification upon merge conflicts
- Do not let pagure return 500 when hit with bogus URL
- When loading comment from JSON rely on username/comment rather than comment id
- When deleting a comment, refresh the ticket git repo
- Make patch_to_diff use lists instead of string concatenation (Patrick
  Uiterwijk)

* Wed May 24 2017 Pierre-Yves Chibon <pingou@pingoured.fr> - 2.90.1-1
- Update to 2.90.1
- Fix the systemd service file for the worker, needs to have the full path
  (Patrick Uiterwijk and I)
- Fix the logcom server (Patrick Uiterwijk)
- Use python-redis instead of trollius-redis to correctly clean up when client
  leaves on the EV server (Patrick Uiterwijk)

* Tue May 23 2017 Pierre-Yves Chibon <pingou@pingoured.fr> - 2.90.0-1
- Bump to 2.90, pre-release of 3.0
- Re-architecture the interactions with git (especially the writing part) to be
  handled by an async worker (Patrick Uiterwijk)
- Add the ability to filter projects by owner (Matt Prahl)

* Thu May 18 2017 Pierre-Yves Chibon <pingou@pingoured.fr> - 2.15.1-1
- Update to 2.15.1
- Fix the requirements on straight.plugin in the requirements.txt file
  (Shengjing Zhu)
- Fix typo in the fedmsg hook so it finds the function where it actually is
- Fix and increase the logging when merging a PR
- Fix pushing a merge commit to the original repo
- Use psutil's Process() instead of looping through all processes (Patrick
  Uiterwijk)
- Don't email admins for each PR conflicting
- Fix/improve our new locking mechanism (Patrick Uiterwijk)
- Drop making the token required at the database level since pagure-ci doesn't
  use one (but do flag pull-requests)
- Fix the watch feature (Matt Prahl)

* Tue May 16 2017 Pierre-Yves Chibon <pingou@pingoured.fr> - 2.15-1
- Update to 2.15
- Improve logic in api/issue.py to reduce code duplication (Martin Basti)
- Fix the download button for attachment (Mark Reynolds)
- Fix our markdown processor for strikethrough
- Add a spinner indicating when we are retrieving the list of branches differing
- Make add_file_to_git use a lock as we do for our other git repositories
- Add the opportunity to enforce a PR-based workflow
- Store in the DB the API token used to flag a pull-request
- Allow people with ticket access to take and drop issues
- Display the users and groups tied to the repo in the API (Matt Prahl)
- Document our markdown in rest so it shows up in our documentation
- Fix comparing the minimal version of flask-wtf required
- Allow the td and th tags to have an align attribute to allow align in html
  tables via markdown
- Avoid binaryornot 0.4.3 and chardet 3.0.0 for the time being
- Add group information API that shows group members (Matt Prahl)
- Ensure people with ticket metadata can edit the custom fields
- Add support to create private projects (Farhaan Bukhsh) - Off by default
- Link to the doc when the documentation is activated but has no content
- Enforce project wide flake8 compliance in the tests
- Enforce a linear alembic history in the tests
- Increase logging in pagure.lib.git
- Use custom logger on all module so we can configure finely the logging
- Multiple improvements to the documentation (René Genz)
- Add the ability to query projects by a namespace in the API (Matt Prahl)
- Add the /<repo>/git/branches API endpoint (Matt Prahl)
- Lock the git repo when removing elements from it
- Always remove the lockfile after using it, just check if it is still present
- Implement the `Give Repo` feature
- Allow project-less token to change the status of an issue in the API
- Make the watch feature more granular (Matt Prahl): you can now watch tickets,
  commits, both, neither or go back to the default
- Bring the pagure.lib coverage to 100% in the tests (which results to bug fixes
  in the code)
- Add locking at the project level using SQL rather than filelock at the git
  repo level

* Wed Mar 29 2017 Pierre-Yves Chibon <pingou@pingoured.fr> - 2.14.2-1
- Update to 2.14.2
- Fix a bug in the logic around diff branches in repos

* Wed Mar 29 2017 Pierre-Yves Chibon <pingou@pingoured.fr> - 2.14.1-1
- Update to 2.14.1
- Fix typo for walking the repo when creating a diff of a PR
- Have the web-hook use the signed content and have a content-type header
- Fix running the tests on jenkins via a couple of fixes to pagure-admin and
  skipping a couple of tests on jenkins due to the current pygit2/libgit2
  situation in epel7

* Mon Mar 27 2017 Pierre-Yves Chibon <pingou@pingoured.fr> - 2.14-1
- Update to 2.14
- Update the label of the button to comment on a PR (Abhijeet Kasurde)
- Make search case insensitive (Vivek Anand)
- Improve the debugging on pagure_loadjson
- Only link the diff to the file if the PR is local and not remote
- Do not log on fedmsg edition to private comment
- When deleting a project, give the fullname in the confirmation window
- Add link to the FPCA indicating where to sign it when complaining that the
  user did not sign it (Charelle Collett)
- Fix the error: 'Project' object has no attribute 'ci_hook'
- Fix input text height to match to button (Abhijeet Kasurde)
- Fix the data model to make deleting a project straight forward
- Fix searching issues in the right project by including the namespace
- When creating the pull-request, save the commit_start and commit_stop
- Ensure there is a date before trying to humanize it
- Fixing showing tags even when some of them are not formatted as expected
- Allow repo user to Take/Drop assigment of issue (Vivek Anand)
- Add merge status column in pull requests page (Abhijeet Kasurde)
- Allow user with ticket access to edit custom fields, metadata and the privacy
  flag (Vivek Anand)
- Add number of issues in my issues page (Abhijeet Kasurde)
- Allow report to filter for a key multiple times
- Add the support to delete a report in a project
- Fix rendering the roadmap when there are tickets closed without a close date
- Fix to show tabs in pull request page on mobile (Abhijeet Kasurde)
- Document some existing API endpoints that were missing from the doc
- Make issues and pull-requests tables behave in responsive way (Abhijeet Kasurde)
- Add option to custom field for email notification (Mark Reynolds)
- When resetting the value of a custom field, indicate what the old value was
- Add instance wide API token
- Move the admin functions out of the UI and into a CLI tool pagure-admin
- Do not update the hash in the URL for every tabs on the PR page
- Fix heatmap to show current datetime not when when object was created (Smit
  Thakkar and Vivek Anand)
- Do not include watchers in the subscribers of a private issue
- Do not highlight code block unless a language is specified
- Make getting a project be case insensitive
- Do not change the privacy status of an issue unless one is specified
- Fix the logic of the `since` keyword in the API (Vivek Anand)
- Fix the logic around ticket dependencies
- Add reset watch button making it go back to the default (Vivek Anand)
- Do not show dates that are None object, instead make them empty strings
- Allow filtering tickets by milestones in the API
- Allow filtering tickets by priorities in the API
- Expand the API to support filtering issues having or not having a milestone
- Use plural form for SSH key textfield (Martin Basti)
- Support irc:// links in our markdown and adjust the regex
- Remove backticks from email subject (Martin Basti)
- Adjust the logic when filtering issues by priorities in the API
- Remove mentioning if a commit is in master on the front page
- Optimize finding out which branches are in a PR or can be
- Add required asterisk to Description on new issues (Abhijeet Kasurde)
- Fix misc typo in 404 messages (Abhijeet Kasurde)
- Add performance git repo analyzer/framework (Patrick Uiterwijk)
- Added tip_tricks in doc to document how to pre-fill issues using the url
  (Eashan)
- Document how to filter out for issues having a certain tag in the tips and
  tricks section
- Allow to manually triggering a run of pagure-ci via a list of sentences set in
  the configuration
- Add support for admin API token to pagure-admin
- Make clicking on 'Unassigned' filter the unassigned PR as it does for issues
- Add Priority column to My Issues page (Abhijeet Kasurde)
- Optimize diffing pull-requests
- Add a description to the API tokens
- Include the fullname in the API output, in the project representation
- Add the possibility to edit issue milestone in the API (Martin Basti)
- Fix some wording (Till Maas)
- Rename "request pull" to pull request (Stanislav Laznicka)
- Make tags in issue list clickable (Martin Basti)
- Include the priority name in the notification rather than its level
- Update the ticket metadata before adding the new comment (if there is one)

* Fri Feb 24 2017 Pierre-Yves Chibon <pingou@pingoured.fr> - 2.13.2-1
- Update to 2.13.2
- Fix running the test suite due to bugs in the code:
- Fix picking which markdown extensions are available
- Fix rendering empty text files

* Fri Feb 24 2017 Pierre-Yves Chibon <pingou@pingoured.fr> - 2.13.1-1
- Update to 2.13.1
- Add a cancel button on the edit file page (shivani)
- Fix rendering empty file (Farhan Bukhsh)
- Fix retrieving the merge status of a pull-request when there is no master
- On the diff of a pull-request, add link to see that line in the entire file
  (Pradeep CE)
- Make the pagure_hook_tickets git hook file be executable
- Be a little more selective about the markdown extensions always activated
- Do not notify the SSE server on comment added to a ticket via git
- Fix inline comment not showing on first click in PR page (Pradeep CE)

* Tue Feb 21 2017 Pierre-Yves Chibon <pingou@pingoured.fr> - 2.13-1
- Update to 2.13
- Allow filtering issues for certain custom keys using <key>:<value> in the
  search input (Patric Uiterwijk)
- Make loading the JSON blob into the database its own async service
- Add ACLs to pagure (Vivek Anand)
- Fix running the tests against postgresql
- Let the doc server return the content as is when it fails to decode it
- Fix rendering a issue when one of the custom fields has not been properly
  setup (ie a custom field of type list, with no options set-up but still having
  a value for that ticket)
- Fix auto-completion when adding a tag to a ticket
- Add the possibility to filter the issues with no milestone assigned (Mark
  Reynolds)
- Fix the callback URL for jenkins for pagure-ci
- Backport the equalto test to ensure it works on old jinja2 version (fixes
  accessing the user's PR page)

* Mon Feb 13 2017 Pierre-Yves Chibon <pingou@pingoured.fr> - 2.12.1-1
- Update to 2.12.1
- Include the build id in the flag set by pagure-ci on PR (Farhaan Bukhsh)
- Fix using the deploy keys (Patrick Uiterwijk)
- Add the possibility to ignore existing git repo on disk when creating a new
  project
- Fix checking for blacklisted projects if they have no namespace
- Link to the documentation in the footer (Rahul Bajaj)
- Fix retrieving the list of branches available for pull-request
- Order the project of a group alphabetically (case-insensitive)
- Fix listing the priorities always in their right order

* Fri Feb 10 2017 Pierre-Yves Chibon <pingou@pingoured.fr> - 2.12-1
- Update to 2.12
- Fix the place of the search and tags bars in the issues page (Pradeep CE)
- Support removing all content of a custom field (Patrick Uiterwijk)
- Improve the `My Pull Requests` page (Pradeep CE)
- Fix displaying binary files in the documentation
- Add a way to easily select multiple tags in the issues list and roadmap
- Allow selecting multiple milestones easily in the UI of the roadmap
- Fix displaying namespaced docs (Igor Gnatenko)
- Fix the web-hook server
- Add a way to view patch attached to a ticket as raw
- Allow milestone to be set when creating an issue using the API (Mark Reynolds)
- Fix adding and editing tags to/of a project
- Make the usage section of the doc be at the top of it (Jeremy Cline)
- Add notifications to issues for meta-data changes (Mark Reynolds)
- Fix not updating the private status of an issue when loading it from JSON
  (Vivek Anand)
- Fix triggering web-hook notifications via the fedmsg hook
- Add a configuration key allowing to hide some projects that users have access
  to only via these groups
- Fix figuring out which branches are not merged in namespaced project
- Automatically link the commits mentionned in a ticket if their hash is 7 chars
  or more
- Allow dropping all the priorities info of an issue
- Do not edit multiple times the milestone info when updating a ticket
- Only update the custom field if there is a value to give it, otherwise remote
  it
- Make pagure compatible with flask-wtf >= 0.14.0
- Add a button to test web-hook notifications
- Fix the layout on the page listing all the closed issues (Rahul Bajaj)
- Load priorities when refreshing the DB from the ticket git repos (Mark
  Reynolds)
- Ignore `No Content-Type header in response` error raised by libgit2 on pull
  from repo hosted on github (for remote PR)
- Add deployment keys (ssh key specific for a single project can be either read
  and write or read-only) (Patrick Uiterwijk)
- Fix install the logcom service to log commits
- Fix deleting tickets that have a tag attached
- Allow pre-filling title and content of an issue via URL arguments:
  ?title=<title>&content=<issue description>
- Re-initialize the backend git repos if there are no tickets/PRs in the DB
  (Vivek Anand)
- Fix invalid pagination when listing all the tickets (regardless of their
  status) and then applying some filtering (Vibhor Verma)

* Fri Jan 20 2017 Pierre-Yves Chibon <pingou@pingoured.fr> - 2.11-1
- Update to 2.11
- Fix the forked repo text on the user's PR page (Rahul Bajaj)
- Display the number of subscribers subscribed to the ticket
- Add an attachments section to tickets (Mark Reynolds)
- Small fixes around the git blame feature
- Add an `Add group` button on page listing the groups (Rahul Bajaj)
- Move the `My Issues` and `My Pull-requests` links under the user's menu
- Document the FORK_FOLDER configuration key as deprecated
- Display the subscribers to PR in the same way to display them on ticket
- Adjust the wording when showing a merge commit
- Ensure the last_updated field is always properly updated (Mark Reynolds)
- Fix decoding files when we present or blame them
- Disable the markdown extensions nl2br on README files
- Make issue reports public
- Only display modified time as the modifying user can not be determined (Mark
  Reynolds)
- Add a new API endpoint returning information about a specific project
- Add a button allowing dropping of assignments for an issue easily (Paul W.
  Frields)
- Make attachments of ticket downloadable (Mark Reynolds)
- Make patch/diff render nicely when viewed attached to a ticket (Mark Reynolds)
- Filter out the currrent ticket in the drop-down list for the blocker/depending
  fields (Eric Barbour)
- Move the logging of the commit as activity to its own service: pagure_logcom
- Add a new API endpoint to set/reset custom fields on tickets
- Introduce the USER_NAMESPACE configuration key allowing to put the project on
  the user's namespace by default
- Fix sending notifications about pull-requests to people watching a project
- Fix the list of blacklisted projects
- Inform the user when they try to create a new group using a display name
  already used (Rahul Bajaj)
- Fix importing the milestones into the project when loading from the git repo
  (Clement Verna)
- Add a button to create a default set of close status (as we have a default set
  of priorities)
- Have pagure bail with an error message if the OpenID server did not return an
  username
- Let the error email use the FROM_EMAIL address set in the configuration file
- Fix theprogress bar shown when listing issues (Gaurav Kumar)
- Replace our current tags by colored one (Mark Reynolds)
- Make the roadmap page use the colored tag (Mark Reynolds)
- Fix the tag of Open pull-request when listing all the pull-requests (Rahul
  Bajaj)
- Remove the 'pagure.lib.model.drop_tables' from test/__init__.py file (Amol
  Kahat)
- Fix the headers of the table listing all the pull-request
- Raise an exception when a PR was made against a branch that no longer exists
- Document what to do when pull-requests are not available in a troubleshooting
  section of the documentation
- Send notification upon closing tickets
- Fix re-setting the close_status to None it when re-opening a ticket
- Fix linking to the tabs in the pull-request page (cep)
- Adjust the rundocserver utility script to have the same arguments as runserver
- Ensure the filtering by author remains when changing the status filter on PR
  list (Rahul Bajaj)
- Improve the page/process to create a new API token (Pradeep CE)
- Prevent re-uploading a file with the same name
- Improve the roadmap page (Mark Reynolds)
- Improve the `My Issues` page (Mark Reynolds)
- Fix home page 'open issues' links for namespaced projects (Adam Williamson)
- Fix logging who did the action
- Return a nicer error message to the user when an error occurs with a remote
  pull-request
- Make interacting with the different git repos a locked process to avoid
  lost/orphan commits
- Update API doc for api_view_user (Clement Verna)
- Dont return 404 when viewing empty files (Pradeep CE (cep))
- Do not automatically update the last_updated or updated_on fields
- Make alembic use the DB url specified in the configuration file of pagure
- Only connect to the smtp server if we're going to send an email
- Add a type list to the custom fields (allows restricting the options) (Mark
  Reynolds)
- Fix displaying non-ascii milestones
- Add the possibility to view all the milestones vs only the active ones (Mark
  Reynolds)

* Sun Dec 04 2016 Pierre-Yves Chibon <pingou@pingoured.fr> - 2.10.1-1
- Update to 2.10.1
- Clean up the JS code in the settings page (Lubomír Sedlář)
- Fix the URLs in the `My Issues` and `My Pull-request` pages

* Fri Dec 02 2016 Pierre-Yves Chibon <pingou@pingoured.fr> - 2.10-1
- Update to 2.10
- Updating language on not found page (Brian (bex) Exelbierd)
- Add a view for open pull requests and issues (Jeremy Cline)
- Issue 1540 - New meta-data custom field type of "link" (Mark Reynolds)
- Fix overflow issue with comment preview and pre (Ryan Lerch)
- Issue 1549 - Add "updated_on" to Issues and make it queryable (Mark Reynolds)
- Drop UPLOAD_FOLDER in favor of UPLOAD_FOLDER_URL
- Make the group_name be of max 255 characters
- Bug - Update documentation to match the default EMAIL_SEND value (Michael
  Watters)
- Change - Fix grammar in UI messages around enabling/deactivating git hooks
  (Michael Watters)
- Allow resetting the priorities of a project
- Several fixes and enhancements around the activity calendarheatmap
- Add quick_replies field to project (Lubomír Sedlář)
- Fix blaming files containing non-ascii characters (Jeremy Cline and I)
- Include regular contributors when checking if user is watching a project
- List subscribers on the issue pages (Mark Renyolds and I)

* Fri Nov 18 2016 Pierre-Yves Chibon <pingou@pingoured.fr> - 2.9-1
- Update to 2.9
- Fix redirecting after updating an issue on a project with namespace (Vivek
  Anand)
- Remove take button from Closed Issues (Rahul Bajaj)
- Show the open date/time on issues as we do for PR (Rahul Bajaj)
- When rendering markdown file use the same code path as when rendering comments
- Add documentation for using Markdown in Pagure (Justing W. Flory)
- Fix the behavior of the Cancel button on PR page (Rahul Bajaj)
- Be tolerant to markdown processing error
- Let the notifications render correctly when added by the SSE server
- Fix the URL for pull request on the list of branches of a fork (Rahul Bajaj)
- Adjust the markdown processor to have 1 regex for all cross-project links
- Remove unsued variables (Farhaan Bukhsh)
- Hide the title of private tickets when linking to them in markdown
- Show user activity in pagure on the user's page
- Add the possibility to subscribe to issues
- Do not cache the session in pagure-ci (as we did for pagure-webhook)
- Fix rendering raw file when the sha1 provided is one of a blob
- Include project's custom fields in the JSON representation of a project
- Include the issue's custom fields values in the JSON representation of an
  issue
- Include the list of close_status and the milestones in the JSON of a project
- Improve documentation related to unit-tests (Rahul Bajaj)
- Use `project.fullname` in X-Pagure-Project header (Adam Williamson)
- Figure a way to properly support WTF_CSRF_TIME_LIMIT on older version of
  flask-wtf
- When updating an issue, if the form does not validate, say so to the user
- Fix the total number of pages when there are no PR/issues/repo (vibhcool)
- Fix forking a repo with a namespace
- Include the namespace in the message returned in pagure.lib.new_project
- Move the metadata-ery area in PR to under the comments tab (Ryan Lerch)
- Update setup instructions in the README.rst (alunux)
- Support namespaced projects when reading json data (clime)
- When uploading a file in a new issue, propagate the namespace info
- Ensure our avatar works with non-ascii email addresses
- Downgrade to emoji 1.3.1, we loose some of the newer emojis we get back
  preview and reasonable size (Clément Verna)
- Fix sending notifications email containing non-ascii characters
- Fix using the proper URL in email notifications (Adam Williamson)
- Move the Clear and Cancel buttons to the right hand side of the comment box
- Fix spelling in the PR page (Vibhor Verma)
- Support loading custom fields from JSON when loading issues from git (Vivek
  Anand)
- Fix handling namespaced project in the SSE server (Adam Williamson)
- Add a pylintrc configuration file to help with code standards (Adam
  Williamson)
- Add go-import meta tag allowing go projects to be hosted on pagure (Patrick
  Uiterwijk)
- Fix index overflow when opening remote pull-request (Mark Reynolds)
- Add SSE support for custom fields
- Add a git blame view
- Allow emptying a file when doing online editing
- Only let admins edit the dependency tree of issues
- Fix some spelling errors (Adam Williamson)
- Add SHA256 signature to webhooks notifications (Patrick Uiterwijk)
- Multiple fixes in the API documentation and output

* Mon Oct 24 2016 Pierre-Yves Chibon <pingou@pingoured.fr> - 2.8.1-1
- Update to 2.8.1
- Handle empty files in detect_encodings (Jeremy Cline)
- Fix the import of encoding_utils in the issues controller
- Fix the list of commits page
- Update docs to dnf (Rahul Bajaj)
- Add close status in the repo table if not present when updating/creating issue
  via git (Vivek Anand)
- If chardet do not return any result, default to UTF-8

* Fri Oct 21 2016 Pierre-Yves Chibon <pingou@pingoured.fr> - 2.8-1
- Update to 2.8
- Fix the migration adding the close_status field to remove the old status
  only at the end
- Fix the RTD and Force push hooks for the change in location of the plugins
- Fix creating new PR from the page listing the pull-requests
- Add the possibility for the user to edit their settings in their settings page
- Include the close_status in the JSON representation of an issue
- Load the close_status if there is one set in the JSON repsentation given
- Fix running the tests when EVENTSOURCE_SOURCE is defined in the
  configuration.
- Make the search case-insensitive when searching issues
- Fix the "cancel" button when editing a "regular" comment on a pull-request
- Remove the ``Content-Encoding`` headers from responses (Jeremy Cline)
- Fix creating the release folder for project with a namespace
- When sending email, make the user who made the action be in the From field
- When searching groups, search both their name and display name
- Create a Vagrantfile and Ansible role for Pagure development (Jeremy Cline)
- Made searching issue stop clearing status and tags filters (Ryan Lerch)
- Improve documentation (Bill Auger)
- Fix finding out the encoding of a file in git (Jeremy Cline)
- Fix making cross-project references using <project>#<id>
- Allow filter the list of commits for a certain user
- Ensure we disable all the submit button when clicking on one (avoid sending
  two comments)
- Do not always compute the list of diff commits
- Let's not assume PAGURE_CI_SERVICES is always there
- Allow html table to define their CSS class
- Add a link to the user on the commit list (Ryan Lerch)
- Change `Fork` button to `View Fork` on all pages of the project (tenstormavi)
- Enable some of the markdown extensions by default
- Fix mixed content blocked in the doc by not sending our user to google (Rahul
  Bajaj)

* Thu Oct 13 2016 Pierre-Yves Chibon <pingou@pingoured.fr> - 2.7.2-1
- Update to 2.7.2
- Do not show the custom field if the project has none
- Improve the documentation around SEND_EMAIL (Jeremy Cline)

* Wed Oct 12 2016 Pierre-Yves Chibon <pingou@pingoured.fr> - 2.7.1-1
- Update to 2.7.1
- Bug fix to the custom fields feature

* Tue Oct 11 2016 Pierre-Yves Chibon <pingou@pingoured.fr> - 2.7-1
- Update to 2.7
- Clean imports (Vivek Anand)
- Fix NoneType error when pagure-ci form is inactively updated first time
  (Farhaan Bukhsh)
- Fix minor typos in configuration documentation (Jeremy Cline)
- Use context managers to ensure files are closed (Jeremy Cline)
- Adjust update_tickets_from_git to add milestones for issues as well (Vivek
  Anand)
- Update milestone description in Settings (Lubomír Sedlář)
- Add checks for the validity of the ssh keys provided (Patrick Uiterwijk)
- Remove hardcoded hostnames in unit tests (Jeremy Cline)
- Skip clamd-dependent tests when pyclamd isn't installed (Patrick Uiterwijk)
- Fix interacting with branch containing a dot in their name (new PR button,
  delete branch button)
- Ensure only project admins can create reports
- Do not warn admins when a build in jenkins did not correspond to a
  pull-request
- Fix the progress bar on the page listing the issues (d3prof3t)
- Do not call the API when viewing a diff or a PR if issues or PRs are disabled
- Port pagure to flask 0.13+
- Fix displaying the reason when a PR cannot be merged
- Allow projects to turn on/off fedmsg notifications
- Fix the web-hook service so when a project is updated the service is as well
- Add the possibility to specify a status to close ticket (closed as upstream,
  works for me, invalid...)
- Let all the optional SelectFields in forms return None when they should
- Make each tests in the test suite run in its own temporary directory (Jeremy
  Cline)
- Use long dash in footer instead of two short ones (Lubomír Sedlář)
- Add a welcome screen to new comers (does not work with local auth)
- Ensure user are not logged in if we couldn't properly set them up in pagure
- Add the possibility to search through issues (AnjaliPardeshi)
- Add a default hook to all new projects, this hook re-set the merge status of
  all the open PR upon push to the main branch of the repo
- Add support for setting custom fields for issues per projects

* Tue Sep 20 2016 Pierre-Yves Chibon <pingou@pingoured.fr> - 2.6-1
- Update to 2.6
- Fix creating new PR from the page listing all the PRs
- Fix grammar error in the issues and PRs page (Jason Tibbitts)
- Fall back to the user's username if no fullname is provided (Vivek Anand)
- Fix typo in the using_docs documentation page (Aleksandra Fedorova (bookwar))
- Fix viewing plugins when the project has a namespace (and the redirection
  after that)
- Rework the milestone, so that a ticket can only be assigned to one milestone
  and things look better
- Add a project wide setting allowing to make all new tickets private by default
  (with the option to make them public)
- Allow toggling the privacy setting when editing the ticket's metadata
- Rework some of the logic of pagure-ci for when it searches the project related
  to a receive notification
- Fix the label of the button to view all close issues to be consistent with the
  PR page (Jeremy Cline)
- Add the possibility for projects to notify specific email addresses about
  issues/PRs update
- Fix loading tickets from the ticket git repository (fixes importing project to
  pagure)

* Tue Sep 13 2016 Pierre-Yves Chibon <pingou@pingoured.fr> - 2.5-1
- Update to 2.5
- Don't track pagure_env (venv) dir (Paul W. Frields)
- Setting Mail-Followup-To when sending message to users (Sergio Durigan Junior)
  (Fixed by Ryan Lerch and I)
- Fixed the tickets hook so that we dont ignore the files committed in the first
  commit (Clement Verna)
- Fix behavior of view of tree if default branch is not 'master' (Vivek Anand)
- Fix checking the release folder for forks
- Improve the Remote PR page
- Improve the fatal error page to display the error message is there is one
- Avoid issues attachment containing json to be considered as an issue to be
  created/updated (Clement Verna)
- Allow the <del> html tag (Clement Verna)
- Specify rel="noopener noreferrer" to link including target='_blank'
- Show in the overview page when a branch is already concerned by a PR
- Fix viewing a tree when the identifier provided is one of a blob (not a tree)
- Port all the plugins to `uselist=False` in their backref to make the code
  cleaner
- Fix pagure_ci for all sort of small issues but also simply so that it works as
  expected
- Make the private method __get_user public as get_user
- Improve the documentation (fix typos and grammar errors) (Sergio Durigan
  Junior)
- Drop the `fake` namespaces in favor of real ones
- Add the possibility to view all tickets/pull-requests of a project (regardless
  of their status)
- Paginate the pages listing the tickets and the pull-requests
- Add the possibility to save a certain filtering on issues as reports
- Add support to our local markdown processor for ~~striked~~

* Wed Aug 31 2016 Pierre-Yves Chibon <pingou@pingoured.fr> - 2.4-1
- Update to 2.4
- - [Security] Avoid all html related mimetypes and force the download if any
  (CVE-2016-1000037) -- Fixed in 2.3.4 as well
- Redirect the URL to projects <foo>.git to <foo> (Abhishek Goswami)
- Allow creating projects with 40 chars length name on newer pagure instances
- Fix @<user> and #<id> when editing a comment (Eric Barbour)
- Display properly and nicely the ACLs of the API tokens (Lubomír Sedlář)
- Removing html5lib so bleach installation finds what version is best (Tiago M.
  Vieira)
- Remove the branchchooser from the repoheader (again) (Ryan Lerch)
- Fix hard-coded urls in the master template
- Made the interaction with the watch button clearer (Ryan Lerch)
- Introduce pagure-ci, a service allowing to integrate pagure with a jenkins
  instance (Farhaan Bukhsh and I)
- Accept Close{,s,d} in the same way as Merges and Fixes (Patrick Uiterwijk)
- Avoid showing the 'New PR' button on the overview page is a PR already exists
  for this branch, in the main project or a fork (Vivek Anand)
- Fix presenting the readme file and display the readme in the tree page if
  there is one in the folder displayed (Ryan Lerch)
- Move the new issue button to be available on every page (AnjaliPardeshi)
- Fix pagure for when an user enters a comment containing #<id> where the id
  isn't found in the db
- Make the bootstrap URLs configurable (so that they don't necessarily point to
  the Fedora infra) (Farhaan Bukhsh)
- Fix how the web-hook server determine the project and its username
- Replace the login icon with plain text (Ryan Lerch)
- Fix layout in the doc (Farhaan Bukhsh)
- Improve the load_from_disk utility script
- Fix our mardown processor to avoid crashing on #<text> (where we expect #<id>)
- Fix the search for projects with a / in their names
- Fix adding a file to a ticket when running pagure with `local` auth
- Improve the grammar around the allowed prefix in our fake-namespaces (Jason
  Tibbitts)
- Implement scanning of attached files for viruses (Patrick Uiterwijk)
- Document how to set-up multiple ssh keys per user (William Moreno Reyes)
- Add display_name and description to groups, and allow editing them
- Add the ability to run the post-receive hook after merging a PR in the UI
- Fix showing the group page even when user management is turned off (Vivek
  Anand)
- Make explicit what the separators for tags is (Farhaan Bukhsh)
- Include the word setting with icon (tenstormavi)
- Fix the requirements.txt file (Vivek Anand)
- Cleaned up the topbar a bit (Ryan Lerch)
- Fix location of bottom pagination links on user page (Ryan Lerch)
- Add user's project watch list in index page of the user (Vivek Anand)
- Fix showing the reporter when listing the closed issues (Vivek Anand)
- Fix accessing forks once the main repo has been deleted (Farhaan Bukhsh)

* Wed Jul 27 2016 Pierre-Yves Chibon <pingou@pingoured.fr> - 2.3.4-1
- Update to 2.3.4
- Security fix release blocking all html related mimetype when displaying the
  raw files in issues and forces the browser to download them instead (Thanks to
  Patrick Uiterwijk for finding this issue) - CVE: CVE-2016-1000037

* Fri Jul 15 2016 Pierre-Yves Chibon <pingou@pingoured.fr> - 2.3.3-1
- Update to 2.3.3
- Fix redering the release page when the tag message contain only spaces (Vivek
  Anand)
- Fix the search in @<username> (Eric Barbour)
- Displays link and git sub-modules in the tree with a dedicated icon

* Tue Jul 12 2016 Pierre-Yves Chibon <pingou@pingoured.fr> - 2.3.2-1
- Update to 2.3.2
- Do not mark as local only some of the internal API endpoints since they are
  called via ajax and thus with the user's IP

* Mon Jul 11 2016 Pierre-Yves Chibon <pingou@pingoured.fr> - 2.3.1-1
- Update to 2.3.1
- Fix sending notifications to users watching a project
- Fix displaying if you are watching the project or not

* Mon Jul 11 2016 Pierre-Yves Chibon <pingou@pingoured.fr> - 2.3-1
- Update to 2.3
- Fix typos in pr_custom_page.rst (Lubomír Sedlář)
- Improve the unit-test suite (Vivek Anand)
- Remove the branch chooser from the repoheader and rework the fork button (Ryan
  Lerch)
- Add support for non utf-8 file names (Ryan Lerch)
- Add a 'Duplicate' status for issues (Vivek Anand)
- Add title attribute for replying to comment and editing the comment in issues
  and PRs (Vivek Anand)
- Include the user when reporting error by email
- Add an API endpoint to create projects
- Add an API endpoint to assign someone to a ticket
- Add small script to be ran as cron to send reminder of expiring tokens (Vivek
  Anand)
- Do not show the PR button on branches for which a PR is already opened
- Add an API endpoint to fork projects
- Add the possibility to watch/unwatch a project (Gaurav Kumar)
- Add a 'Take' button on the issue page (Ryan Lerch and I)
- Add a dev-data script to input some test data in the DB for testing/dev
  purposes (skrzepto)
- Fix links to ticket/pull-request in the preview of a new ticket
- Add the possibility to diff two or more commits (Oliver Gutierrez)
- Fix viewing a file having a non-ascii name
- Fix viewing the diff between two commits having a file with a non-ascii name
- On the commit detail page, specify on which branch(es) the commit is
- Add the possibility to have instance-wide admins will full access to every
  projects (set in the configuration file)
- Drop the hash to the blob of the file when listing the files in the repo
- Add autocomple/suggestion on typing @<username> on a ticket or a pull-request
  (Eric Barbour)
- Fix the edit link when adding a comment to a ticket via SSE
- Add notifications to issues as we have for pull-requests
- Record in the db the date at which a ticket was closed (Vivek Anand)
- Add the possibility for pagure to rely on external groups provided by the auth
  service
- Add the possibility for pagure to use an SMTP server requiring auth
  (Vyacheslav Anzhiganov)
- Add autocomple/suggestion on typing #<id> for tickets and pull-requests (Eric
  Barbour)
- With creating a README when project's description has non-ascii characters
  (vanzhiganov)
- Add colored label for duplicate status of issues (Vivek Anand)
- Ship working wsgi files so that they can be used directly from the RPM
- Mark the wsgi files provided with the RPM as %%config(noreplace)
- Install the api_key_expire_mail.py script next to the createdb one

* Wed Jun 01 2016 Pierre-Yves Chibon <pingou@pingoured.fr> - 2.2.1-1
- Update to 2.2.1
- Fix showing the inital comment on PR having only one commit (Ryan Lerch)
- Fix diffs not showing for additions/deletions for files under 1000 lines (Ryan
  Lerch)
- Split out the commits page to a template of its own (Ryan Lerch)
- Fix hightlighting the commits tab on commit view
- Fix the fact that the no readme box show on empty repo (Ryan Lerch)

* Tue May 31 2016 Pierre-Yves Chibon <pingou@pingoured.fr> - 2.2-1
- Update to 2.2
- Fix retrieving the log level from the configuration file (Nuno Maltez)
- Rework the labels used when sorting projects (Ankush Behl)
- Fix spelling error in sample config (Bruno)
- Hide the URL to the git repo for issues if these are disabled
- Do not notify about tickets being assigned when loaded from the issue git repo
  (Clément Verna)
- Adjust get_revs_between so that if the push is in the main branch we still get
  the list of changes (Clément Verna)
- Fix display of files moved on both old and new pygit2 (Ryan Lerch)
- Fix changes summary sidebar for older versions of pygit (Ryan Lerch)
- Fix the label on the button to add a new milestone to a project (Lubomír
  Sedlář)
- Allow the roadmap feature to have multiple milestone without dates (Lubomír
  Sedlář)
- Fix the link to switch the roadmap/list views (Lubomír Sedlář)
- Render the emoji when adding a comment to a ticket or PR via SSE (Clément
  Verna)
- Always allow adming to edit/delete comments on issues
- Build Require systemd to get macros defined in the spec file (Bruno)
- Upon creating a ticket if the form already has data, show that data
- Add a readme placeholder for projects without a readme (Ryan Lerch)
- Enable markdown preview on create pull request (Ryan Lerch)
- Make bottom pagination links on project list respect the sorting filter (Ryan
  Lerch)
- Add the ability to create a README when creating a project (Ryan Lerch)
- Try to prevent pushing commits without a parent when there should be one
- Fix the configuration keys to turn off ticket or user/group management for an
  entire instance (Vivek Anand)
- Fix deleting project (propagate the deletion to the plugins tables)
- Do not render the diffs of large added and removed files (more than 1000
  lines) (Ryan Lerch)
- Adjust the UI on the template to add/remove a group or an user to a project in
  the settings page (Ryan Lerch)
- Check if a tag exists on a project before allowing to edit it (skrzepto)

* Fri May 13 2016 Pierre-Yves Chibon <pingou@pingoured.fr> - 2.1.1-1
- Update to 2.1.1
- Do not render the comment as markdown when importing tickets via the ticket
  git repo
- Revert get_revs_between changes made in
  https://pagure.io/pagure/pull-request/941 (Clement Verna)

* Fri May 13 2016 Pierre-Yves Chibon <pingou@pingoured.fr> - 2.1-1
- Update to 2.1
- Fix the milter to get it working (hotfixed in prod)
- Fix the fedmsg hook so that it works fine (hotfixed in prod)
- Fix the path of one of the internal API endpoint
- Pass client_encoding utf8 when connecting to the DB (Richard Marko)
- Do not use client_encoding if using sqlite (Ryan Lerch)
- Allow project names up to 255 characters (Richard Marko)
- Add a spinner showing we're working on retrieve the PR status on the PR page
  (farhaanbukhsh)
- Rework installing and removing git hooks (Clement Verna)
- Rework the summary of the changes on the PR page (Ryan Lerch)
- Improve the description of the priority system (Lubomír Sedlář)
- Fix commit url in the pagure hook (Mike McLean)
- Improve the regex when fixing/relating a commit to a ticket or a PR (Mike
  McLean)
- Improve the description of the pagure hook (Mike McLean)
- Fix the priority system to support tickets without priority
- Fix the ordering of the priority in the drop-down list of priorities
- Ensure the drop-down list of priorities defaults to the current priority
- Adjust the runserver.py script to setup PAGURE_CONFIG before importing pagure
- Remove flashed message when creating a new project
- Add markdown support for making of PR# a link to the corresponding PR
- Include the priority in the JSON representation of a ticket
- Include the priorities in the JSON representation of a project
- Do not update the assignee if the person who commented isn't an admin
- When adding a comment fails, include the comment text in the form if there was
  one
- Add support to remove a group from a project
- Add a roadmap feature with corresponding documentation
- Allow 'kbd' and 'var' html tags to render properly
- Fix deleting a project on disk as well as in the DB
- Allow setting the date_created field when importing ticket from git (Clement
  Verna)
- Strip GPG signature from the release message on the release page (Jan Pokorný)
- Make comment on PR diffs fit the parent, and not overflow horiz (Ryan Lerch)

* Sun Apr 24 2016 Pierre-Yves Chibon <pingou@pingoured.fr> - 2.0.1-1
- Update to 2.0.1
- Fixes to the UPGRADING documentation
- Fix URLs to the git repos shown in the overview page for forks
- Fix the project titles in the html to not start with `forks/`

* Fri Apr 22 2016 Pierre-Yves Chibon <pingou@pingoured.fr> - 2.0-1
- Update to 2.0
- Rework the initial comment of a PR, making it less a comment and more
  something that belong to the PR itself
- Fix showing or not the fork button when editing a comment on an issue or a PR
  and fix the highlighted tab when editing comment of an issue (Oliver
  Gutierrez)
- Fix the count of comments shown on the page listing all the PRs to include
  only the comments and not the notifications (farhaanbukhsh)
- In the settings page explain that API keys are personal (Lubomír Sedlář)
- Rework the fedmsg message sent upon pushing commits, one message per push
  instead of one message per commit
- Mark the page next/previous as disabled when they are (on browse pages)
- Avoid the logout/login loop when logging out
- Support rendering file with a `.markdown` extension
- Fix the layout of the password change branch
- Improve the documentation, add overview graphs, expand the usage section,
  improve the overview description
- Fix checking if the user is an admin of a project or not (which was making the
  user experience confusing as they sometime had the fork button and sometime
  not)
- Fix the pagination on the browse pages when the results are sorted
- Disable the Commit and Files tabs if a repo is new
- Update the pagure logo to look better (Ryan Lerch)
- Allow anyone to fork any project (Ryan Lerch)
- Fix searching on the browse pages by preventing submission of the 'enter' key
  (Ryan Lerch)
- Rework the issue page to be a single, large form allowing to update the
  meta-data and comment in one action and fixing updating the page via SSE
- Turn off the project's documentation by default to empty `Docs` tab leading to
  nothing
- Fill the initial comment with the body of the commit message if the PR only
  has one commit (Ryan Lerch)
- Add a plugin/git hook allowing to disable non fast-forward pushes on a branch
  basis
- Fix asynchronous inline comments in PR by fixing the URL to which the form is
  submitted
- Add a plugin/git hook allowing to trigger build on readthedocs.org upon git
  push, with the possibility to restrict the trigger to only certain branches
- Automatically scroll to the highlighted range when viewing a file with a
  selection (Lubomír Sedlář)
- Indicate the project's creation date in the overview page (Anthony Lackey)
- Clear the `preview` field after adding a comment via SSE
- Adjust the unit-tests for the change in behavior in pygments 2.1.3
- Fix listing all the request when the status is True and do not convert to text
  request.closed_at if it is in fact None
- Improved documentation
- Attempt to fix the error `too many open files` on the EventSource Server
- Add a new param to runserver.py to set the host (Ryan Lerch)
- Fix the of the Docs tab and the Fork button with rounded corners (Pedro Lima)
- Expand the information in the notifications message when a PR is updated (Ryan
  Lerch)
- Fix hidding the reply buttons when users are not authenticated (Paul W. Frields)
- Improve the description of the git hooks (Lubomír Sedlář)
- Allow reply to a notification of pagure and setting the reply email address as
  Cc
- In the fedmsg git hook, publish the username of all the users who authored the
  commits pushed
- Add an activity page/feed for each project using the information retrieved
  from datagrepper (Ryan Lerch)
- Fix showing lightweight tags in the releases page (Ryan Lerch)
- Fix showing the list of branches when viewing a file
- Add priorities to issues, with the possibility to filter or sort them by it in
  the page listing them.
- Add support for pseudo-namespace to pagure (ie: allow one '/' in project name
  with a limited set of prefix allowed)
- Add a new plugin/hook to block push containing commits missing the
  'Signed-off-by' line
- Ensure we always use the default email address when sending notification to
  avoid potentially sending twice a notification
- Add support for using the keyword Merge(s|d) to close a ticket or pull-request
  via a commit message (Patrick Uiterwijk)
- Add an UPGRADING.rst documentation file explaining how to upgrade between
  pagure releases

* Tue Mar 01 2016 Pierre-Yves Chibon <pingou@pingoured.fr> - 1.2-1
- Update to 1.2
- Add the possibility to create a comment when opening a pull-request (Clement
  Verna)
- Fix creating PR from a fork directly from the page listing all the PR on the
  main project (Ryan Lerch)
- Color the label showing the issues' status on the issue page and the page
  listing them (Ryan Lerch)
- Add a small padding at the bottom of the blockquote (Ryan Lerch)
- In the list of closed PR, replace the column of the assignee with the date of
  closing (Ryan Lerch)
- Drop font awesome since we no longer use it and compress the png of the
  current logo (Ryan Lerch)
- Drop the svg of the old logo from the source (Ryan Lerch)
- Add descriptions to the git hooks in the settings page (farhaanbukhsh)
- Fix the pagure git hook

* Wed Feb 24 2016 Pierre-Yves Chibon <pingou@pingoured.fr> - 1.1.1-1
- Update to 1.1.1
- Fix showing some files where decoding to UTF-8 was failing
- Avoid adding a notification to a PR for nothing
- Show notifications correctly on the PR page when received via SSE

* Tue Feb 23 2016 Pierre-Yves Chibon <pingou@pingoured.fr> - 1.1-1
- Update to 1.1
- Sort the release by commit time rather than name (Clerment Verna)
- Add a link to the markdown syntax we support
- Add the possibility to display custom info when creating a new PR
- Improve the title of the issue page
- Make the ssh_info page more flexible so that we can add new info more easily
- Add the possibility to resend a confirmation email when adding a new email
  address
- Encode the email in UTF-8 for domain name supporting it
- Add a button to easily change your avatar in your settings' page (Clement
  Verna)
- Expand our markdown processor to support implicit linking to both PR and
  issues
- Fix running the unit-tests on F23
- Fix deleting in the UI branches containing a slash ('/') in their name
- Add the possibility to always have a merge commit when merging a PR
- Add the project's avatar to the list in front page when authenticated
- Make the dependency on flask-fas-openid (part of python-fedora) optional
- Prevent our customized markdown to create link on foo.com if it doesn't start
  with {f,ht}tp(s) (Clement Verna)
- Bring back the delete ticket button (Ryan Lerch)
- Add the possibility to notify someone when it is mentioned in a comment via
  @username
- Fix setting the default value of the web-hook setting and its display in the
  settings page
- Add the possibility to have templates for the issues
- Add a button on the doc page to open it in a new tab
- Add the concept of notifications on PR allowing to indicate when a PR is
  updated or rebased
- Fix allowing people with non-ascii username to merge PR with a merge commit
- Add the possibility to theme your pagure instance and customized its layout at
  will
- Add the possibility to always see inline-comments even if the file was changed
  since
- Improve the error message given to the user upon error 500 (Patrick Uiterwijk)
- Stop relying on pygit2 to determine if a file is a binary file or not and
  instead use the python library binaryornot
- Store in the DB the identifier of the tree when an inline comment is made to a
  PR, this way it will be simpler to figure out a way to add the context of this
  comment either by email on in the UI
- Add styling to blockquotes so that we see what is the quote and what is the
  answer when replying to someone
- Prevent users from adding again an email pending confirmation
- Fix the preview box for long comment (Ryan Lerch)
- Add the possibility to sort the projects when browsing them (Ryan Lerch)

* Thu Feb 04 2016 Pierre-Yves Chibon <pingou@pingoured.fr> - 1.0.2-1
- Update to 1.0.2
- Rework the PR page (Ryan Lerch)
- Add ssh_info to blacklist in default config (Ryan Lerch)
- Restyle the ssh_info page (Ryan Lerch)
- Fix hiding the preview pane when creating an issue (Ryan Lerch)
- Indicate the number of comments on the PR when listing them (Ryan Lerch)
- Fix showing the links to issues when previewing a comment
- Ensure some more that the page number isn't below 1
- Do not show the edit and delete buttons to everyone when adding a comment via
  SSE
- Update the requirements.txt for a missing dependency on Ubuntu (vanzhiganov)
- Improving sorting the release tags in the release page (Clement Verna)

* Mon Feb 01 2016 Pierre-Yves Chibon <pingou@pingoured.fr> - 1.0.1-1
- Update to 1.0.1
- Improve the fork list (Ryan Lerch)
- Make sure the images on comments do not exceed the size of the comment
  box/area (Ryan Lerch)
- Improve the page listing all issues (Ryan Lerch)
- Include the project information when sending a fedmsg message about editing a
  comment
- Allow <span> tags in rst files so that the README shows fine
- Fix linking directly to a specific comment in a PR
- Fix adding comment in a PR via SSE
- Fix updating issue information via SSE
- Fix the reply buttons on the issue page
- Remove the choice for a status when creating a new ticket (Farhaandukhsh)
- Fix deleting a branch from the UI
- Make the cards have rounded corners (Sayan Chowdhury)
- Fix showing the description of form field (Vivek Anand)
- Fix checking if the passwords added are the same (for local accounts)
  (Vivek Anand)
- Fix displaying emojis when previewing a comment on a ticket (Clement Verna)
- Add support for emojis when creating a new ticket (Clement Verna)

* Wed Jan 27 2016 Pierre-Yves Chibon <pingou@pingoured.fr> - 1.0-1
- Update to 1.0
- Entirely new UI thanks to the hard work on Ryan Lerch
- Add the possibility to edit comments on PR/Tickets (and the option to disable
  this) (farhaanbukhsh)
- Add the number of open Tickets/PR on the project's menu
- Also allow PRs to be closed via a git commit message (Patrick Uiterwijk)
- Disable issues and PR on forks by default (Vivek Anand)
- Fix deleting the temporary folders we create
- Un-bundle flask_fas_openid (requires python-fedora 0.7.0 or higher
- Add support for an openid backend (ie same thing as FAS but w/o the FPCA
  enforcing)
- Add support to view rst/markdown files as html directly inline (default) or as
  text (Yves Martin)
- Change the encryption system when using pagure with local auth to not be
  time-sensitive and be stronger in general (farhaanbukhsh)
- Change the size of the varchar from 256 to 255 for a better MySQL support
- Add support for pagure to work behind a reverse proxy
- Rename the cla_required decorator to a more appropriate login_required
- Show the in the front page and the page listing all the pull-requests the
  branch for which a PR can be opened
- Rework the avatar to not rely on the ones associated with id.fedoraproject.org
- Add support to high-light a section of code in a PR and show the diff
  automatically if there is such selection

* Mon Dec 14 2015 Pierre-Yves Chibon <pingou@pingoured.fr> - 0.1.36-1
- Update to 0.1.36
- Add the ssh info on the front page if the repo is empty
- Make the code handling exception be python3 compatible
- Make pagure compatible with F23 (ie: pygit2 0.23.0)
- Fix pagination when rendering the repo blocks (Gaurav Kumar)
- Make the SHOW_PROJECTS_INDEX list what should be showing in the index page
- Adjust pagure to work on recent version of psutils as well as the old one
- Added 'projects' to the blacklisted list of projects (Gaurav Kumar)
- Removed delete icons for non group members on the group info page (Gaurav
  Kumar)
- Fixed forbidden error for PR title editing (Gaurav Kumar)

* Mon Nov 30 2015 Pierre-Yves Chibon <pingou@pingoured.fr> - 0.1.35-1
- Update to 0.1.35
- Fix the web-hook server by preventing it to raise any exception (rather log
  the errors)

* Mon Nov 30 2015 Pierre-Yves Chibon <pingou@pingoured.fr> - 0.1.34-1
- Update to 0.1.34
- Fix the encoding of the files we're displaying on the UI
- Fix commenting on the last line of a diff
- Fix returning error message from the internal API (shows the PR as conflicting
  then)
- Fix stacktrace encountered in some repo if the content of a folder is empty
  (or is a git submodule)
- Split the web-hooks into their own server
- If you try to fork a forked project, redirect the user to the fork
- Show the repo from and repo to when opening a new PR
- Add the pagination links at the bottom of the repo list as well
- Add the groups to the pool of users to notify upon changes to a project
- Hide private repo from user who do not have commit access

* Fri Nov 20 2015 Pierre-Yves Chibon <pingou@pingoured.fr> - 0.1.33-1
- Update to 0.1.33
- Prevent project with a name starting with a non-alphanumerical character
  (Farhaanbukhsh)
- Ensure we appropriately set the private flag when creating an issue
- Add an activity graph on the user profile using datagrepper
- Sometime the identified we get is a Tag, not a commit (fixes traceback
  received by email)
- Order the PR from the most recent to the oldest
- Fix the patch view of a PR when we cannot find one of the commit (fixes
  traceback received by email)
- Allow user that are not admin to create a remote pull-request
- Fix closing the EV server by calling the appropriate variable
- Fix generating the diff of remote pull-request

* Fri Nov 13 2015 Pierre-Yves Chibon <pingou@pingoured.fr> - 0.1.32-1
- Update to 0.1.32
- Fix the example configuration file
- Make pagure work on MySQL
- Hide sections on the front page only if the user is logged out
- Fix the release page where sometime tags are commits
- Escape the raw html in markdown
- Decode the bytes returned by pygit2 to try to guess if the content is a text
  or not
- Fix the 'Clear' button on the pull-request page (farhaanbukhsh)
- Fix installing pagure in a venv
- Fix uploading images when editing the first comment of a ticket
- Let the author of the merge commit be the user doing the merge
- Suggest the title of the PR only if it has one and only one commit in
- Do not hide sections on the user page if we set some to be hidden on the front
  page
- Forward the head to the commits page to fix the pull-request button
- Ensure we create the git-daemon-export-ok when forking a repo (fixes cloning
  over https)
- Add instructions on how to get pagure working in a venv (Daniel Mach)
- Improve the way we retrieve and check pygit2's version (Daniel Mach)

* Tue Oct 13 2015 Pierre-Yves Chibon <pingou@pingoured.fr> - 0.1.31-1
- Forward the bail_on_tree boolean when iterating so that we know how to behave
  when we run into a git tree (where we expected a git blob)
  -> fixes error received by email

* Tue Oct 13 2015 Pierre-Yves Chibon <pingou@pingoured.fr> - 0.1.30-1
- Fix error received by email by checking the right variable if it is a git tree
  or a git blob
- Unless we explicitly accept all images tag, always filter them (fixes
  attaching images to a ticket)

* Tue Oct 13 2015 Pierre-Yves Chibon <pingou@pingoured.fr> - 0.1.29-1
- Use monospace fonts for online editing as well as comment on tickets and
  pull-requests
- Fix online editing of symlinked files (such as the README)
- Handle potential error when converting from rst to html

* Mon Oct 12 2015 Pierre-Yves Chibon <pingou@pingoured.fr> - 0.1.28-1
- Update to 0.1.28
- Fix the call to noJS() in the pull-request template to avoid crashing
- Improve the runserver script in the sources
- Fix the projects pagination on the index page
- Create the git-daemon-export-ok file upon creating a new project/git
- Use first line of commit message for PR title when only one commit (Maciej
  Lasyk)
- Show the tag message near the tag in the release page
- Set the default_email when creating a local user account

* Mon Oct 05 2015 Pierre-Yves Chibon <pingou@pingoured.fr> - 0.1.27-1
- Update to 0.1.27
- Skip writing empty ssh keys on disc
- Regenerate authorized_keys file on ssh key change (Patrick Uiterwijk)

* Mon Oct 05 2015 Pierre-Yves Chibon <pingou@pingoured.fr> - 0.1.26-1
- Update to 0.1.26
- Let admins close PRs as well

* Mon Oct 05 2015 Pierre-Yves Chibon <pingou@pingoured.fr> - 0.1.25-1
- Update to 0.1.25
- Improve the documentation (especially the part about configuring pagure and
  all the options the configuration file supports)
- Remove the two trailing empty lines when showing a file online
- Add a link on the issue list to be able to filter all the unassigned issues
- Rework the layout of the pull-request page
- Rework the commit list in the PR page to allow showing the entire commit
  message
- Let any user create remote pull-request otherwise what's the point?
- Add the possibility to edit the title of a pull-request
- Add a page listing all the pull-requests of an user (opened by or against)
- Add support for multiple ssh-keys (Patrick Uiterwijk)
- Ensure the authorized_keys file is generated by gitolite (Patrick Uiterwijk)
- Fix the regex for @<username>
- Improve the display of renamed files in PR
- Add option to disable entirely the user/group management from the UI
- Add an updated_on field to Pull-Request
- Add an closed_at field to Pull-Request
- Allow the submitter of a PR to close it (w/o merging it)
- Disable editing a pull-request when that one is closed/merged
- Add option to hide by default a part of the index page (ie: all the repos, the
  user's repos or the user's forks)
- Drop the csrf_token from the error emails sent to the admins

* Tue Sep 08 2015 Pierre-Yves Chibon <pingou@pingoured.fr> - 0.1.24-1
- Update to 0.1.24
- Fix changelog to add the -release
- Block the <img> tag on titles
- Better fedmsg notifications (for example for new branches or rebase)
- Support uploading multiple files at once
- Add a load_from_disk utility script to the sources
- Fix indentation to the right on very long pull-request

* Sun Aug 30 2015 Pierre-Yves Chibon <pingou@pingoured.fr> - 0.1.23-1
- Update to 0.1.23
- Return a 404 error if we can't find the doc repo asked
- Fix for #106 Allow setting the default branch of the git repo and in the UI
  (Ghost-script)
- Improve unit-tests suite
- Add a global boolean to disable entirely tickets on all projects of a pagure
  instance (with no way to re-set them per project)
- Do display uploading a tarball if it is not entirely configured
- Ensure we do not offer to reply by email if the milter is not set up
- Ensure there is no new line character on the msg-id and improve logging in the
  milter
- Add a configuration key to globally disable creating projects
- Add a configuration key to globally disable deleting projects
- Add the possibility to search projects/users
- Drop links to the individual commits in a remote pull-request
- Input that are cleaned via the noJS filter are safe to be displayed (avoid
  double HTML escaping)
- When writing the authorized_key file, encode the data in UTF-8
- Makes page title easier to find in multi-tab cases (dhrish20)
- Fix authorized_keys file creation (Patrick Uiterwijk)
- Honor also symlinked README's in repo overview (Jan Pakorný)
- Fix the patch generation for remote PR
- Fix showing the comment's preview on the pull-request page
- Fix bug in checking if a PR can be merged

* Fri Aug 07 2015 Pierre-Yves Chibon <pingou@pingoured.fr> - 0.1.22-1
- Update to 0.1.22
- Adjust the README to the current state of pagure
- Rework how we integrate our custom tags into markdown to avoid the infinite
  loop we run into once in a while

* Wed Aug 05 2015 Pierre-Yves Chibon <pingou@pingoured.fr> - 0.1.21-1
- Update to 0.1.21
- Make SSH protocol explicit for SSH URLs (Till Maas)
- Adjust the documentation (layout and content)
- Rework the doc server to allow showing html files directly
- Fix installing the pagure hook correctly (tickets and requests)
- Give proper attribution to the pagure logo to Micah Deen in the documentation
- Increase pull request text field lengths to 80 (Till Maas)
- Fix who can open a remote PR and the check that the repo allows PR
- If there is no commit and no content, it means we didn't find the file: 404

* Wed Jul 29 2015 Pierre-Yves Chibon <pingou@pingoured.fr> - 0.1.20-1
- Update to 0.1.20
- Include the tags in the JSON representation of a project
- Add the ability to open a pull-request from a git repo not hosted on pagure
- Fix pagination when browsing the list of commits
- Fix the fork button when viewing the Settings of a project
- Adjust the example apache configuration file
- Add a favicon with pagure's logo
- Fix asynchronous commentting on pull-requests
- Start working on some documentation on how to install pagure
- Do no flash messages when a comment is submitted via javascript (ie: async)
- Do not blink the tittle of the page if the page is already on focus
- Retrieve ssh key from FAS and set it up in pagure if none is currently set-up
- Fix anchors for comments on the pull-request pages
- Fix checking the merge status of a PR when user is not logged in

* Mon Jul 20 2015 Pierre-Yves Chibon <pingou@pingoured.fr> - 0.1.19-1
- Update to 0.1.19
- Prettify the JSON stored in the git for tickets/requests... (Simo Sorce)
- Use the project name as subject tag in the notifications sent (Simo Sorce)
- Add an X-pagure header with either the pagure instance or the project name
- Reset the merge status of all the open PR when one is merged
- Add a second server listing the number of connections opened on the first
  eventsource server
- Log the info instead of printing them in the eventsource server
- Split the documentation to a different wsgi application to avoid any risk of
  cross-site forgery
- Fix the JS logic when adding a tag or a dependency to avoid having duplicates
  in the input field
- Allow deleting a git branch of a project via the UI
- Include the font-awesome in the source rather than relying on an external cdn
- Do not try to connect to the eventsource server if we're not viewing a
  pull-request
- Fix showing the first comment made on a PR via the eventsource server
- Fix showing the git URLs in the doc server
- Much better API documentation (Lei Yang)
- Handle showing closed PR that were not merged
- Fix refreshing the UI of private tickets via the eventsource (making calls to
  the API to get the info while only getting what changed via the SSE)
- Fix the anchor links in the API documentation
- Blink the tab upon changes in the page
- Ensure we close both SSE server when stopping pagure_ev
- Let the HTML form trigger if we did not connect to the EV server successfully
- The admins of a repo are anyone with commit access to the repo, directly or
  via a group
- Order the project by names in the front page (instead of creation date)
- Add the ability to tag a project
- Fix the fedmsg_hook when there are only deletions or only additions
- Add a new API endpoint allowing to search projects (by name, author, tag ...)
- Make pagure compatible with pygit 0.22.0
- Adjust unit-tests for all these changes

* Mon Jun 22 2015 Pierre-Yves Chibon <pingou@pingoured.fr> - 0.1.18-1
- Update to 0.1.18
- Fix the eventsource server for CORS
- Fix showing/checking the merge status of a PR

* Mon Jun 22 2015 Pierre-Yves Chibon <pingou@pingoured.fr> - 0.1.17-1
- Update to 0.1.17
- Fix for missing docs of API issue add comment (Kunaal Jain)
- Fix the systemd init file
- Be more careful about the URL specified, it may be of the wrong format in the
  eventsource server
- Allow configuring the port where the event source server runs in the
  configuration
- Fix bug in filter_img_src introduced with its moved to the backend library

* Thu Jun 18 2015 Pierre-Yves Chibon <pingou@pingoured.fr> - 0.1.16-1
- Update to 0.1.16
- Clone all the remote branches when cloning a project
- Allow online editing to a new branch or any of the existing ones
- Allow the <hr /> html tags in markdown
- Add eventsource support in the ticket and pull-request pages

* Tue Jun 16 2015 Pierre-Yves Chibon <pingou@pingoured.fr> - 0.1.15-1
- Update 0.1.15
- Use a monospace font for the commit hash
- Remove duplicated "commit" id in the HTML (causing a graphical bug in the
  commit page)
- Secure the input using the no_js filter instead of relying on a restrictive
  regex for PR and issue titles
- Support ',' in the tags field since it's required to specify multiple tags

* Fri Jun 12 2015 Pierre-Yves Chibon <pingou@pingoured.fr> - 0.1.14-1
- Update to 0.1.14
- Remove all new lines characters from the ssh key uploaded
- Adjust the URL in the footer to point to https://pagure.io/pagure
- Fix displaying the time of a comment
- Forbid the use of spaces in group name
- Do not get the list of not-merged commits if there is only 1 branch in the
  repo
- Display the error message if pagure.lib.add_group raises an exception
- Add a new setting enforcing that all commits in a PR are signed-off by their
  author
- Enforce that all commits are signed-off by the author if the repo is
  configured for this
- Also check for the signed-off status before merging a pull-request
- Adjust online-editing to allow specifying which email address to use in the
  commit
- Add an avatar_email field to projects
- Change the PullRequest's status from a Boolean to a Text restricted at the DB
  level (Allows to distinguish Open/Merged/Closed)
- Show in the pull-request view who merged the pull-request
- Specify who closed the pull-request in the API output
- Catch GitError when merging and checking merge status of a PR
- Hide the form to create pull-requests if the user is not an admin of the repo
- Replace the Pull-Request button by a Compare button if the user it not a repo
  admin
- Set the title of the tab as URL hash to allow directly linking to it
- Adjust the API to be able to distinguish API authentication and UI
  authentication
- Fix API documentation to create new issues
- Drop the status from the requirements to open a new issue via the API
- Expand the list of blacklisted project names
- Have the code tags behave like pre tags (html tags)
- Allow project to specify an URL and display it on their page
- Strip the ssh keys when writing them to the authorized_keys file
- Disable javascript in all the markdown fields
- Validate early the input submitted in the forms (using more or less strict
  regex)
- If the session timed-out, redirect to the setting page after authentication
  and inform the user that the action was canceled
- Catch PagureException when adjusting the project's settings
- Redirect the /api endpoint to the api documentation place
- Fix how is retrieved the list of emails to send the notification to
- Sanitize the html using bleach to avoid potential XSS exploit
- Do not give READ access to everyone on the tickets and pull-requests repos to
  avoid leaking private tickets
- Adjust the unit-tests for all these changes

* Fri Jun 05 2015 Pierre-Yves Chibon <pingou@pingoured.fr> - 0.1.13-1
- Update to 0.1.13
- Do not show the edit button if the user cannot edit the file
- Fix who is allowed to drop comments
- Fix showing the drop comment button on issue comments
- Fix creating the pull-request for fast people like @lmacken
- Display the target of the PR as well as the origin in the PR page
- Limit the size of the lists on the front page

* Fri Jun 05 2015 Pierre-Yves Chibon <pingou@pingoured.fr> - 0.1.12-1
- Update to 0.1.12
- Fix the URL where the sources upload are done
- Upload the new sources under the project's name (be it project or
  user/project)

* Fri Jun 05 2015 Pierre-Yves Chibon <pingou@pingoured.fr> - 0.1.11-1
- Update to 0.1.11
- Another fix for the fedmsg_hook git hook
- Adjust how we display the README page to avoid XSS there as well
- Add the possibility to disable plugins via the configuration file
- Present the git tags in the UI
- As soon as the API user present a token, validate it or not, even if the
  endpoint would work without token
- Integrate alembic for DB scheme migration
- Cache the PR's merge status into the DB
- Only people with access to the project can add/remove API token
- Make the unit-tests run on bare repos as in prod
- First stab at online editing
- Simplify the API output to drop the project's settings where it doesn't
  make sense
- First stag at allowing upstream to upload their release to pagure
- Fix merging a PR into another branch than master
- Reduce code duplication when checking if a PR can be merged or merging it
- Code style clean-up

* Tue Jun 02 2015 Pierre-Yves Chibon <pingou@pingoured.fr> - 0.1.10-1
- Update to 0.1.10
- Add support for URL ending with a trailing slash where it makes sense (so
  we support both with and without trailing slash)
- Fix XSS issue by disabling <script> tags in the documentation pages
- Expend the unit-test suite for the api.project controller
- Add the possibility for 3rd party apps to 'flag' a pull-request with for
  example the result of a build
- Handle the situation where there are multiple branch of the same name in
  the same repo
- Fix the color of the link on hover when displayed within a tab view
  (for example in the PR pages)
- Redirect the user to the pull-request created after its the creation
- Do not leak emails over fedmsg
- Fix the fedmsg_hook plugin

* Fri May 29 2015 Pierre-Yves Chibon <pingou@pingoured.fr> - 0.1.9-1
- Update to 0.1.9
- Initial API work
- Document the initial API
- Fix the CSS to present the links correctly
- Add new API endpoint to list the git tags of a project
- Ensure the DB is updated regarding the start and stop commits before merging

* Wed May 27 2015 Pierre-Yves Chibon <pingou@pingoured.fr> - 0.1.8-1
- Update 0.1.8
- Add the possibility to do Asynchronous in-line comment posting
  (Patrick Uiterwijk)
- Handle the situation where the branch asked is not found in the git repo
- Handle the situation where we cannot find a desired commit
- Do not display a value in the settings page if there are none
- Rework the pull-request view to move the list of commits into a tab
- Make email sending optional (Patrick Uiterwijk)

* Fri May 22 2015 Pierre-Yves Chibon <pingou@pingoured.fr> - 0.1.7-1
- Update to 0.1.7
- Drop debugging code on the milter and the hooks
- Adjust the search_issues method to support filter for some tags, excluding
  some others (for example ?tags=easfix&tags=!0.2)
- Support groups when searching an user's projects (ie: finding the projects an
  user has access to via the group their are in)
- Do not load the git repo from the FS when loading an user's page
- Present and document the SSH keys in a dedicated documentation page

* Wed May 20 2015 Pierre-Yves Chibon <pingou@pingoured.fr> - 0.1.6-1
- Update to 0.1.6
- Fix sending notification emails to multiple users, avoid sending private into
  to all of them

* Tue May 19 2015 Pierre-Yves Chibon <pingou@pingoured.fr> - 0.1.5-1
- Update to 0.1.5
- Bug fix on the milter and the internal API endpoint

* Tue May 19 2015 Pierre-Yves Chibon <pingou@pingoured.fr> - 0.1.4-1
- Update to 0.1.4
- Fix loading requests and tickets from git (allows syncing projects between
  pagure instances)
- Add to the template .wsgi file a way to re-locate the tmp folder to work
  around a bug in libgit2
- Fix unit-tests suite
- Adjust the spec file to install all the files required for the milters
- Fix the `View` button on the pull-request pages

* Wed May 13 2015 Pierre-Yves Chibon <pingou@pingoured.fr> - 0.1.3-1
- Update to 0.1.3
- Add support for gitolite3
- Fix unit-tests suite to work on jenkins

* Sat May 09 2015 Pierre-Yves Chibon <pingou@pingoured.fr> - 0.1.2-2
- Fix the Requires on the milter subpackage (adding: post, preun and postun)
- Add systemd scriptlet to restart the service gracefully
- Use versioned python macro (py2)
- Ship the license in the milter subpackage as well
- Use the %%license macro

* Thu May 07 2015 Pierre-Yves Chibon <pingou@pingoured.fr> - 0.1.2-1
- Update to 0.1.2
- Fix bug in the fedmsg hook file (Thanks Zbigniew Jędrzejewski-Szmek)

* Wed May 06 2015 Pierre-Yves Chibon <pingou@pingoured.fr> - 0.1.1-1
- Update to 0.1.1
- Port to python-munch and list it in the dependencies
- Fix exporting patch when they contain unicode characters or accent
- After creating an issue, user is brought back to the new issue page
- Fix unit-tests
- Stop the pagure hook if the user is deleting a branch (no need to run through
  all the commits of that branch)
- Fix the requirements.txt file (Sayan Chowdhury)
- Fix the tree page to show the commit sha on its proper line (Sayan Chowdhury)
- Fix typo in the form of some of the plugin (Sayan Chowdhury)
- Improve the README (Sayan Chowdhury)
- Fix highlighting the commits tab when accessing it (Sayan Chowdhury)

* Mon May 04 2015 Pierre-Yves Chibon <pingou@pingoured.fr> - 0.1-1
- First official release: 0.1

* Thu Apr 02 2015 Pierre-Yves Chibon <pingou@pingoured.fr> - 0.0-1.20150402
- Cut a RPM for testing on Thu Apr 2nd 2015

* Wed Oct 08 2014 Pierre-Yves Chibon <pingou@pingoured.fr> - 0.0-1.20141008
- Initial packaging work for Fedora
