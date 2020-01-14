Summary: XCache Consistency Check 
Name: xcache_consistency_check
Version: 5.0.0
Release: 1%{?dist}
Source: xcache_consistency_check-%{version}.tar.gz
License: Apache 2.0
BuildArch: noarch
Url: https://github.com/ddavila0/xcache_consistecy_check
BuildRequires: python2-setuptools
Requires: xz
Requires: python-pip

%description
Tool to chech consistency on XCache files

%prep
%setup

%build
%py2_build

%install
%py2_install

%files
%{python_sitelib}/*
%{_bindir}/%{name}

%post
pip install --upgrade pip
pip install -r  /lib/python2.7/site-packages/%{name}-%{version}-py2.7.egg-info/requires.txt

%changelog
* Tue Nov 19 2019 Diego Davila <didavila@ucsd.edu> 1.0.0-1
- Initial
