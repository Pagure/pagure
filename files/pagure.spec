%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from
%distutils.sysconfig import get_python_lib; print (get_python_lib())")}

Name:           pagure
Version:        0.1
Release:        1%{?dist}
Summary:        A git-centered forge

License:        GPLv2+
URL:            http://fedorahosted.org/pagure/
Source0:        https://fedorahosted.org/releases/p/a/pagure/%{name}-%{version}.tar.gz

BuildArch:      noarch

BuildRequires:  python2-devel
BuildRequires:  python-setuptools
BuildRequires:  python-nose

BuildRequires:  python-alembic
BuildRequires:  python-arrow
BuildRequires:  python-blinker
BuildRequires:  python-chardet
BuildRequires:  python-docutils
BuildRequires:  python-flask
BuildRequires:  python-flask-wtf
BuildRequires:  python-markdown
BuildRequires:  python-psutil
BuildRequires:  python-pygit2 >= 0.20.1
BuildRequires:  python-pygments
BuildRequires:  python-fedora
BuildRequires:  python-openid
BuildRequires:  python-openid-cla
BuildRequires:  python-openid-teams
BuildRequires:  python-straight-plugin
BuildRequires:  python-wtforms
BuildRequires:  python-munch

# EPEL6
%if ( 0%{?rhel} && 0%{?rhel} == 6 )
BuildRequires:  python-sqlalchemy0.8
Requires:  python-sqlalchemy0.8
%else
BuildRequires:  python-sqlalchemy > 0.8
Requires:  python-sqlalchemy > 0.8
%endif

Requires:  python-alembic
Requires:  python-arrow
Requires:  python-blinker
Requires:  python-chardet
Requires:  python-docutils
Requires:  python-flask
Requires:  python-flask-wtf
Requires:  python-markdown
Requires:  python-psutil
Requires:  python-pygit2 >= 0.20.1
Requires:  python-pygments
Requires:  python-fedora
Requires:  python-openid
Requires:  python-openid-cla
Requires:  python-openid-teams
Requires:  python-straight-plugin
Requires:  python-wtforms
Requires:  python-munch
Requires:  mod_wsgi

# No dependency of the app per say, but required to make it working.
Requires:  gitolite


%description
Pagure is a light-weight git-centered forge based on pygit2.

Currently, Pagure offers a web-interface for git repositories, a ticket
system and possibilities to create new projects, fork existing ones and
create/merge pull-requests across or within projects.

%package milters
Summary: Milter to integrate pagure with emails
BuildArch: noarch
BuildRequires: python-pymilter
BuildRequires: systemd-devel
Requires: python-pymilter
Requires: systemd
# It would work with sendmail but we configure things (like the tempfile)
# to work with postfix
Requires:  postfix


%description milters
Milters (Mail filters) allowing the integration of pagure and emails.
This is useful for example to allow commenting on a ticket by email.


%prep
%setup -q


%build
%{__python} setup.py build


%install
rm -rf $RPM_BUILD_ROOT
%{__python} setup.py install -O1 --skip-build --root $RPM_BUILD_ROOT

# Install apache configuration file
mkdir -p $RPM_BUILD_ROOT/%{_sysconfdir}/httpd/conf.d/
install -m 644 files/pagure.conf $RPM_BUILD_ROOT/%{_sysconfdir}/httpd/conf.d/pagure.conf

# Install configuration file
mkdir -p $RPM_BUILD_ROOT/%{_sysconfdir}/pagure
install -m 644 files/pagure.cfg.sample $RPM_BUILD_ROOT/%{_sysconfdir}/pagure/pagure.cfg

# Install WSGI file
mkdir -p $RPM_BUILD_ROOT/%{_datadir}/pagure
install -m 644 files/pagure.wsgi $RPM_BUILD_ROOT/%{_datadir}/pagure/pagure.wsgi

# Install the createdb script
install -m 644 createdb.py $RPM_BUILD_ROOT/%{_datadir}/pagure/pagure_createdb.py


# Install the milter files
mkdir -p $RPM_BUILD_ROOT/%{_localstatedir}/run/pagure
mkdir -p $RPM_BUILD_ROOT/%{_tmpfilesdir}
mkdir -p $RPM_BUILD_ROOT/%{_unitdir}
install -m 0644 milters/milter_tempfile.conf \
    $RPM_BUILD_ROOT/%{_tmpfilesdir}/%{name}-milter.conf
install -m 644 milters/pagure_milter.service \
    $RPM_BUILD_ROOT/%{_unitdir}/pagure_milter.service


%files
%doc README.rst LICENSE
%config(noreplace) %{_sysconfdir}/httpd/conf.d/pagure.conf
%config(noreplace) %{_sysconfdir}/pagure/pagure.cfg
%dir %{_sysconfdir}/pagure/
%{_datadir}/pagure/
%{python_sitelib}/pagure/
%{python_sitelib}/pagure*.egg-info


%files milters
%attr(755,postfix,postfix) %dir %{_localstatedir}/run/pagure
%{_tmpfilesdir}/%{name}-milter.conf
%{_unitdir}/pagure_milter.service


%changelog
* Mon May 04 2015 Pierre-Yves Chibon <pingou@pingoured.fr> - 0.1-1
- First official release: 0.1

* Thu Apr 02 2015 Pierre-Yves Chibon <pingou@pingoured.fr> - 0.0-1.20150402
- Cut a RPM for testing on Thu Apr 2nd 2015

* Wed Oct 08 2014 Pierre-Yves Chibon <pingou@pingoured.fr> - 0.0-1.20141008
- Initial packaging work for Fedora
