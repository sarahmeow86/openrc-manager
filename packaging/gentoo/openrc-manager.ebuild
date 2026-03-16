# Copyright 2024 Gentoo Authors
# Distributed under the terms of the GNU General Public License v2

EAPI=8

PYTHON_COMPAT=( python3_{10..12} )
inherit python-single-r1 desktop xdg

DESCRIPTION="GTK4 graphical interface for managing OpenRC services"
HOMEPAGE="https://github.com/youruser/openrc-manager"
SRC_URI="https://github.com/youruser/${PN}/archive/v${PV}.tar.gz -> ${P}.tar.gz"

LICENSE="GPL-3"
SLOT="0"
KEYWORDS="~amd64 ~x86"
IUSE=""

REQUIRED_USE="${PYTHON_REQUIRED_USE}"

RDEPEND="
    ${PYTHON_DEPS}
    gui-libs/gtk:4
    gui-libs/libadwaita
    dev-python/pygobject:3
    sys-apps/openrc
"

DEPEND="${RDEPEND}"

src_install() {
    python_domodule openrc_manager
    python_newscript openrc_manager/__main__.py openrc-manager

    doicon -s scalable openrc_manager/data/openrc-manager.svg
    domenu openrc_manager/data/openrc-manager.desktop

    insinto /usr/share/polkit-1/actions
    doins openrc_manager/data/org.openrc.manager.policy
}
