Name:           openrc-manager
Version:        1.0.6
Release:        1%{?dist}
Summary:        GTK4 graphical interface for managing OpenRC services

License:        GPL-3.0
URL:            https://github.com/sarahmeow86/openrc-manager
Source0:        %{name}-%{version}.tar.gz

BuildArch:      noarch
BuildRequires:  python3-devel
BuildRequires:  python3-setuptools

Requires:       python3
Requires:       python3-gobject
Requires:       gtk4
Requires:       libadwaita
Requires:       openrc
Requires:       polkit

%description
A user-friendly GTK4 GUI application for managing OpenRC init scripts.
Works on any OpenRC-based distribution including Gentoo, Alpine, Artix,
Devuan, and StrataOS.

%prep
%autosetup

%build
%py3_build

%install
%py3_install

install -Dm644 openrc_manager/data/openrc-manager.desktop \
    %{buildroot}%{_datadir}/applications/openrc-manager.desktop

install -Dm644 openrc_manager/data/openrc-manager.svg \
    %{buildroot}%{_datadir}/icons/hicolor/scalable/apps/openrc-manager.svg

install -Dm644 openrc_manager/data/org.openrc.manager.policy \
    %{buildroot}%{_datadir}/polkit-1/actions/org.openrc.manager.policy

%files
%license LICENSE
%doc README.md
%{python3_sitelib}/openrc_manager/
%{python3_sitelib}/openrc_manager-*.egg-info/
%{_bindir}/openrc-manager
%{_datadir}/applications/openrc-manager.desktop
%{_datadir}/icons/hicolor/scalable/apps/openrc-manager.svg
%{_datadir}/polkit-1/actions/org.openrc.manager.policy

%changelog
* Mon Jan 15 2024 sarahmeow86 <saretta1986@proton.me> - 1.0.6-1
- Initial release
