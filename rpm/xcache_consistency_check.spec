Summary: XCache Consistency Check 
Name: xcache_consistency_check
Version: 1.0.0
Release: 1%{?dist}
Source: xcache_consistency_check-%{version}.tar.gz
License: Apache 2.0
BuildArch: noarch
Url: https://github.com/ddavila0/xcache_consistecy_check
Requires: uproot

%description
Tool to chech consistency on XCache files

%prep
%setup -q

%install
install -D -m 0755 bin/xcache_consistency_check %{buildroot}/%{_bindir}/xcache_consistency_check
#install -D -m 0644 src/net_name_addr_utils.py  %{buildroot}/%{python_sitelib}/net_name_addr_utils.py

%files
%{_bindir}/xcache_consistency_check
#%{python_sitelib}/topology_utils.py*


%changelog
* Tue Nov 19 2019 Diego Davila <didavila@ucsd.edu> 1.0.0-1
- Initial
