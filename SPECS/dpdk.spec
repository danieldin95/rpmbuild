# Add option to build with examples
%bcond_with examples
# Add option to build without tools
%bcond_without tools

# Dont edit Version: and Release: directly, only these:
#% define commit0 0da7f445df445630c794897347ee360d6fe6348b
#% define date 20181127
#% define shortcommit0 %(c=%{commit0}; echo ${c:0:7})

%define ver 18.11
%define rel 4

%define srcname dpdk

Name: dpdk
Version: %{ver}
Release: %{rel}%{?commit0:.%{date}git%{shortcommit0}}%{?dist}
URL: http://dpdk.org
%if 0%{?commit0:1}
Source: http://dpdk.org/browse/dpdk/snapshot/dpdk-%{commit0}.tar.xz
%else
Source: http://fast.dpdk.org/rel/dpdk-%{ver}.tar.xz
%endif

# Only needed for creating snapshot tarballs, not used in build itself
Source100: dpdk-snapshot.sh

Source500: configlib.sh
Source501: gen_config_group.sh
Source502: set_config.sh

# Important: source503 is used as the actual copy file
# @TODO: this causes a warning - fix it?
Source504: arm64-armv8a-linuxapp-gcc-config
Source505: ppc_64-power8-linuxapp-gcc-config
Source506: x86_64-native-linuxapp-gcc-config

# Patches only in dpdk package
Patch0: 0001-bus-vmbus-fix-race-in-subchannel-creation.patch
Patch1: 0002-net-netvsc-enable-SR-IOV.patch
Patch2: 0003-net-netvsc-disable-multi-queue-on-older-servers.patch
Patch3: 0004-net-virtio-set-offload-flag-for-jumbo-frames.patch

Summary: Set of libraries and drivers for fast packet processing

#
# Note that, while this is dual licensed, all code that is included with this
# Pakcage are BSD licensed. The only files that aren't licensed via BSD is the
# kni kernel module which is dual LGPLv2/BSD, and thats not built for fedora.
#
License: BSD and LGPLv2 and GPLv2

#
# The DPDK is designed to optimize througput of network traffic using, among
# other techniques, carefully crafted assembly instructions.  As such it
# needs extensive work to port it to other architectures.
ExclusiveArch: x86_64 aarch64 ppc64le

# machine_arch maps between rpm and dpdk arch name, often same as _target_cpu
# machine_tmpl is the config template machine name, often "native"
# machine is the actual machine name used in the dpdk make system
%ifarch x86_64
%define machine_arch x86_64
%define machine_tmpl native
%define machine default
%endif
%ifarch aarch64
%define machine_arch arm64
%define machine_tmpl armv8a
%define machine armv8a
%endif
%ifarch ppc64le
%define machine_arch ppc_64
%define machine_tmpl power8
%define machine power8
%endif

%define target %{machine_arch}-%{machine_tmpl}-linuxapp-gcc

%define sdkdir  %{_datadir}/%{name}
%define docdir  %{_docdir}/%{name}
%define incdir  %{_includedir}/%{name}
%define pmddir %{_libdir}/%{name}-pmds

%if 0%{?rhel} > 7 || 0%{?fedora}
%define _py python3
%define _py_exec %{?__python3}
%else
%define _py python
%define _py_exec %{?__python2}
%endif

BuildRequires: gcc, kernel-headers, zlib-devel, numactl-devel
BuildRequires: doxygen, %{_py}-devel, %{_py}-sphinx
%ifarch x86_64
BuildRequires: rdma-core-devel >= 15 libmnl-devel
%global __requires_exclude_from ^%{_libdir}/librte_pmd_mlx[45]_glue\.so.*$
%endif

%description
The Data Plane Development Kit is a set of libraries and drivers for
fast packet processing in the user space.

%package devel
Summary: Data Plane Development Kit development files
Requires: %{name}%{?_isa} = %{version}-%{release}

%description devel
This package contains the headers and other files needed for developing
applications with the Data Plane Development Kit.

%package doc
Summary: Data Plane Development Kit API documentation
BuildArch: noarch

%description doc
API programming documentation for the Data Plane Development Kit.

%if %{with tools}
%package tools
Summary: Tools for setting up Data Plane Development Kit environment
Requires: %{name} = %{version}-%{release}
Requires: kmod pciutils findutils iproute %{_py_exec}

%description tools
%{summary}
%endif

%if %{with examples}
%package examples
Summary: Data Plane Development Kit example applications
BuildRequires: libvirt-devel

%description examples
Example applications utilizing the Data Plane Development Kit, such
as L2 and L3 forwarding.
%endif

%prep
%autosetup -n %{srcname}-%{?commit0:%{commit0}}%{!?commit0:%{ver}} -p1

%build
# In case dpdk-devel is installed
unset RTE_SDK RTE_INCLUDE RTE_TARGET

# Avoid appending second -Wall to everything, it breaks upstream warning
# disablers in makefiles. Strip expclit -march= from optflags since they
# will only guarantee build failures, DPDK is picky with that.
export EXTRA_CFLAGS="$(echo %{optflags} | sed -e 's:-Wall::g' -e 's:-march=[[:alnum:]]* ::g') -Wformat -fPIC"

# DPDK defaults to using builder-specific compiler flags.  However,
# the config has been changed by specifying CONFIG_RTE_MACHINE=default
# in order to build for a more generic host.  NOTE: It is possible that
# the compiler flags used still won't work for all Fedora-supported
# machines, but runtime checks in DPDK will catch those situations.

make V=1 O=%{target} T=%{target} %{?_smp_mflags} config

cp -f %{SOURCE500} %{SOURCE502} "%{_sourcedir}/%{target}-config" .
%{SOURCE502} %{target}-config "%{target}/.config"

make V=1 O=%{target} %{?_smp_mflags} 

# Creating PDF's has excessive build-requirements, html docs suffice fine
make V=1 O=%{target} %{?_smp_mflags} doc-api-html doc-guides-html

%if %{with examples}
make V=1 O=%{target}/examples T=%{target} %{?_smp_mflags} examples
%endif

%install
# In case dpdk-devel is installed
unset RTE_SDK RTE_INCLUDE RTE_TARGET

%make_install O=%{target} prefix=%{_usr} libdir=%{_libdir}

# Replace /usr/bin/env python with the correct python binary
find %{buildroot}%{sdkdir}/ -name "*.py" -exec \
  sed -i -e 's|#!\s*/usr/bin/env python|#!%{_py_exec}|' {} +

# Create a driver directory with symlinks to all pmds
mkdir -p %{buildroot}/%{pmddir}
for f in %{buildroot}/%{_libdir}/*_pmd_*.so.*; do
    bn=$(basename ${f})
%ifarch x86_64
    case $bn in
    librte_pmd_mlx[45]_glue.so.*)
        mkdir -p %{buildroot}/%{pmddir}-glue
        ln -s ../${bn} %{buildroot}%{pmddir}-glue/${bn}
        continue
        ;;
    esac
%endif
    ln -s ../${bn} %{buildroot}%{pmddir}/${bn}
done

%if ! %{with tools}
rm -rf %{buildroot}%{sdkdir}/usertools
rm -rf %{buildroot}%{_sbindir}/dpdk-devbind
%endif
rm -f %{buildroot}%{sdkdir}/usertools/dpdk-setup.sh
rm -f %{buildroot}%{sdkdir}/usertools/meson.build
rm -f %{buildroot}%{_bindir}/dpdk-pmdinfo
rm -f %{buildroot}%{_bindir}/dpdk-test-crypto-perf
rm -f %{buildroot}%{_bindir}/dpdk-test-eventdev

%if %{with examples}
find %{target}/examples/ -name "*.map" | xargs rm -f
for f in %{target}/examples/*/%{target}/app/*; do
    bn=`basename ${f}`
    cp -p ${f} %{buildroot}%{_bindir}/dpdk-${bn}
done
%else
rm -rf %{buildroot}%{sdkdir}/examples
%endif

# Setup RTE_SDK environment as expected by apps etc
mkdir -p %{buildroot}/%{_sysconfdir}/profile.d
cat << EOF > %{buildroot}/%{_sysconfdir}/profile.d/dpdk-sdk-%{_arch}.sh
if [ -z "\${RTE_SDK}" ]; then
    export RTE_SDK="%{sdkdir}"
    export RTE_TARGET="%{target}"
    export RTE_INCLUDE="%{incdir}"
fi
EOF

cat << EOF > %{buildroot}/%{_sysconfdir}/profile.d/dpdk-sdk-%{_arch}.csh
if ( ! \$RTE_SDK ) then
    setenv RTE_SDK "%{sdkdir}"
    setenv RTE_TARGET "%{target}"
    setenv RTE_INCLUDE "%{incdir}"
endif
EOF

# Fixup target machine mismatch
sed -i -e 's:-%{machine_tmpl}-:-%{machine}-:g' %{buildroot}/%{_sysconfdir}/profile.d/dpdk-sdk*

%files
# BSD
%doc README MAINTAINERS
%{_bindir}/testpmd
%{_bindir}/dpdk-procinfo
%{_bindir}/dpdk-pdump
%dir %{pmddir}
%{_libdir}/*.so.*
%{pmddir}/*.so.*
%ifarch x86_64
%dir %{pmddir}-glue
%{pmddir}-glue/*.so.*
%endif

%files doc
#BSD
%{docdir}

%files devel
#BSD
%{incdir}/
%{sdkdir}/
%if %{with tools}
%exclude %{sdkdir}/usertools/
%endif
%if %{with examples}
%exclude %{sdkdir}/examples/
%endif
%{_sysconfdir}/profile.d/dpdk-sdk-*.*
%{_libdir}/*.so
%if %{with examples}
%files examples
%exclude %{_bindir}/dpdk-procinfo
%exclude %{_bindir}/dpdk-pdump
%{_bindir}/dpdk-*
%doc %{sdkdir}/examples/
%endif

%if %{with tools}
%files tools
%{sdkdir}/usertools/
%{_sbindir}/dpdk-devbind
%endif

%changelog
* Mon Feb 18 2019 Jens Freimann <jfreiman@redhat.com> - 18.11-4
- Set correct offload flags for virtio and allow jumbo frames (#1669355)

* Wed Feb 06 2019 Maxime Coquelin <maxime.coquelin@redhat.com> - 18.11.3
- Backport NETVSC pmd fixes (#1662292)

* Tue Nov 27 2018 Timothy Redaelli <tredaelli@redhat.com> - 18.11-2
- Fix python scripts hashbang
- Remove meson.build from dpdk-tools

* Tue Nov 27 2018 Timothy Redaelli <tredaelli@redhat.com> - 18.11-1
- Add conditionals to build on RHEL8 and Fedora
- Updated to DPDK 18.11 (#1651337):
  - Updated configs
  - Added libmnl-devel BuildRequires for Mellanox

* Mon Nov 05 2018 Timothy Redaelli <tredaelli@redhat.com> - 17.11-15
- Re-align with DPDK patches inside OVS FDP 18.11 (#1646598)

* Fri Sep 14 2018 Timothy Redaelli <tredaelli@redhat.com> - 17.11-14
- Backport "net/mlx{4,5}: avoid stripping the glue library" (#1627285)

* Tue Jul 31 2018 Timothy Redaelli <tredaelli@redhat.com> - 17.11-13
- Re-align with DPDK patches inside OVS FDP 18.08 (#1610407)
- Backport "net/i40e: fix port segmentation fault when restart" (#1610481)

* Mon Jul 23 2018 Timothy Redaelli <tredaelli@redhat.com> - 17.11-12
- Remove dpdk-pmdinfo (#1494462)

* Thu Jun 14 2018 Timothy Redaelli <tredaelli@redhat.com> - 17.11-11
- Re-align with DPDK patches inside OVS FDP 18.06 (#1591198)

* Mon Jun 11 2018 Aaron Conole <aconole@redhat.com> - 17.11-10
- Fix mlx5 memory region boundary checks (#1581230)

* Thu Jun 07 2018 Timothy Redaelli <tredaelli@redhat.com> - 17.11-9
- Add 2 missing QEDE patches
- Fix previous changelog date

* Thu Jun 07 2018 Timothy Redaelli <tredaelli@redhat.com> - 17.11-8
- Align with DPDK patches inside OVS FDP 18.06
- Enable BNXT, MLX4, MLX5, NFP and QEDE PMDs
- Backport "net/mlx: fix rdma-core glue path with EAL plugins" (only needed on
  DPDK package)

* Wed Jan 31 2018 Kevin Traynor <ktraynor@redhat.com> - 17.11-7
- Backport to forbid IOVA mode if IOMMU address width too small (#1530957)

* Wed Jan 31 2018 Aaron Conole <aconole@redhat.com> - 17.11-6
- Backport to protect active vhost_user rings (#1525446)

* Tue Jan 09 2018 Timothy Redaelli <tredaelli@redhat.com> - 17.11-5
- Real backport of "net/virtio: fix vector Rx break caused by rxq flushing"

* Thu Dec 14 2017 Timothy Redaelli <tredaelli@redhat.com> - 17.11-4
- Backport "net/virtio: fix vector Rx break caused by rxq flushing"

* Wed Dec 06 2017 Timothy Redaelli <tredaelli@redhat.com> - 17.11-3
- Enable ENIC only for x86_64

* Wed Dec 06 2017 Timothy Redaelli <tredaelli@redhat.com> - 17.11-2
- Re-add main package dependency from dpdk-tools
- Add explicit python dependency to dpdk-tools

* Tue Nov 28 2017 Timothy Redaelli <tredaelli@redhat.com> - 17.11-1
- Update to DPDK 17.11 (#1522700)
- Use a static configuration file
- Remove i686 from ExclusiveArch since it's not supported on RHEL7
- Remove "--without shared" support

* Fri Oct 13 2017 Josh Boyer <jwboyer@redhat.com> - 16.11.2-6
- Rebuild to pick up all arches

* Fri Oct 13 2017 Timothy Redaelli <tredaelli@redhat.com> - 16.11.2-5
- Enable only supported PMDs (#1497384)

* Fri Jun 23 2017 John W. Linville <linville@redhat.com> - 16.11.2-4
- Backport "eal/ppc: fix mmap for memory initialization"

* Fri Jun 09 2017 John W. Linville <linville@redhat.com> - 16.11.2-3
- Enable i40e driver in PowerPC along with its altivec intrinsic support
- Add PCI probing support for vfio-pci devices in Power8

* Thu Jun 08 2017 John W. Linville <linville@redhat.com> - 16.11.2-2
- Enable aarch64, ppc64le (#1428587)

* Thu Jun 08 2017 Timothy Redaelli <tredaelli@redhat.com> - 16.11.2-1
- Import from fdProd
- Update to 16.11.2 (#1459333)

* Wed Mar 22 2017 Timothy Redaelli <tredaelli@redhat.com> - 16.11-4
- Avoid infinite loop while linking with libdpdk.so (#1434907)

* Thu Feb 02 2017 Timothy Redaelli <tredaelli@redhat.com> - 16.11-3
- Make driverctl a different package

* Thu Dec 08 2016 Kevin Traynor <ktraynor@redhat.com> - 16.11-2
- Update to DPDK 16.11 (#1335865)

* Wed Oct 05 2016 Panu Matilainen <pmatilai@redhat.com> - 16.07-1
- Update to DPDK 16.07 (#1383195)
- Disable unstable bnx2x driver (#1330589)
- Enable librte_vhost NUMA support again (#1279525)
- Enable librte_cryptodev, its no longer considered experimental
- Change example prefix to dpdk- for consistency with other utilities
- Update driverctl to 0.89

* Thu Jul 21 2016 Flavio Leitner <fbl@redhat.com> - 16.04-4
- Updated to DPDK 16.04

* Wed Mar 16 2016 Panu Matilainen <pmatilai@redhat.com> - 2.2.0-3
- Disable librte_vhost NUMA support for now, it causes segfaults

* Wed Jan 27 2016 Panu Matilainen <pmatilai@redhat.com> - 2.2.0-2
- Use a different quoting method to avoid messing up vim syntax highlighting
- A string is expected as CONFIG_RTE_MACHINE value, quote it too
- Enable librte_vhost NUMA-awareness

* Tue Jan 12 2016 Panu Matilainen <pmatilai@redhat.com> - 2.2.0-1
- Update DPDK to 2.2.0 final
- Add README and MAINTAINERS docs
- Adopt new upstream standard installation layout, including
  dpdk_nic_bind.py renamed to dpdk_nic_bind
- Move the unversioned pmd symlinks from libdir -devel
- Establish a driver directory for automatic driver loading
- Disable CONFIG_RTE_SCHED_VECTOR, it conflicts with CONFIG_RTE_MACHINE default
- Disable experimental cryptodev library
- More complete dtneeded patch
- Make option matching stricter in spec setconf
- Update driverctl to 0.59

* Wed Dec 09 2015 Panu Matilainen <pmatilai@redhat.com> - 2.1.0-5
- Fix artifacts from driverctl having different version
- Update driverctl to 0.58

* Fri Nov 13 2015 Panu Matilainen <pmatilai@redhat.com> - 2.1.0-4
- Add driverctl sub-package

* Fri Oct 23 2015 Panu Matilainen <pmatilai@redhat.com> - 2.1.0-3
- Enable bnx2x pmd, which buildrequires zlib-devel

* Mon Sep 28 2015 Panu Matilainen <pmatilai@redhat.com> - 2.1.0-2
- Make lib and include available both ways in the SDK paths

* Thu Sep 24 2015 Panu Matilainen <pmatilai@redhat.com> - 2.1.0-1
- Update to dpdk 2.1.0 final
  - Disable ABI_NEXT
  - Rebase patches as necessary
  - Fix build of ip_pipeline example
  - Drop no longer needed -Wno-error=array-bounds
  - Rename libintel_dpdk to libdpdk

* Tue Aug 11 2015 Panu Matilainen <pmatilai@redhat.com> - 2.0.0-9
- Drop main package dependency from dpdk-tools

* Wed May 20 2015 Panu Matilainen <pmatilai@redhat.com> - 2.0.0-8
- Drop eventfd-link patch, its only needed for vhost-cuse

* Tue May 19 2015 Panu Matilainen <pmatilai@redhat.com> - 2.0.0-7
- Drop pointless build conditional, the linker script is here to stay
- Drop vhost-cuse build conditional, vhost-user is here to stay
- Cleanup comments a bit
- Enable parallel build again
- Dont build examples by default

* Thu Apr 30 2015 Panu Matilainen <pmatilai@redhat.com> - 2.0.0-6
- Fix potential hang and thread issues with VFIO eventfd

* Fri Apr 24 2015 Panu Matilainen <pmatilai@redhat.com> - 2.0.0-5
- Fix a potential hang due to missed interrupt in vhost library

* Tue Apr 21 2015 Panu Matilainen <pmatilai@redhat.com> - 2.0.0-4
- Drop unused pre-2.0 era patches
- Handle vhost-user/cuse selection automatically based on the copr repo name

* Fri Apr 17 2015 Panu Matilainen <pmatilai@redhat.com> - 2.0.0-3
- Dont depend on fuse when built for vhost-user support
- Drop version from testpmd binary, we wont be parallel-installing that

* Thu Apr 09 2015 Panu Matilainen <pmatilai@redhat.com> - 2.0.0-2
- Remove the broken kmod stuff
- Add a new dkms-based eventfd_link subpackage if vhost-cuse is enabled

* Tue Apr 07 2015 Panu Matilainen <pmatilai@redhat.com> - 2.0.0-1
- Update to 2.0 final (http://dpdk.org/doc/guides-2.0/rel_notes/index.html)

* Thu Apr 02 2015 Panu Matilainen <pmatilai@redhat.com> - 2.0.0-0.2086.git263333bb.2
- Switch (back) to vhost-user, thus disabling vhost-cuse support
- Build requires fuse-devel for now even when fuse is unused

* Mon Mar 30 2015 Panu Matilainen <pmatilai@redhat.com> - 2.0.0-0.2049.git2f95a470.1
- New snapshot
- Add spec option for enabling vhost-user instead of vhost-cuse
- Build requires fuse-devel only with vhost-cuse
- Add virtual provide for vhost user/cuse tracking 

* Fri Mar 27 2015 Panu Matilainen <pmatilai@redhat.com> - 2.0.0-0.2038.git91a8743e.3
- Disable vhost-user for now to get vhost-cuse support, argh.

* Fri Mar 27 2015 Panu Matilainen <pmatilai@redhat.com> - 2.0.0-0.2038.git91a8743e.2
- Add a bunch of missing dependencies to -tools

* Thu Mar 26 2015 Panu Matilainen <pmatilai@redhat.com> - 2.0.0-0.2038.git91a8743e.1
- Another day, another snapshot
- Disable IVSHMEM support for now

* Fri Mar 20 2015 Panu Matilainen <pmatilai@redhat.com> - 2.0.0-0.2022.gitfe4810a0.2
- Dont fail build for array bounds warnings for now, gcc 5 is emitting a bunch

* Fri Mar 20 2015 Panu Matilainen <pmatilai@redhat.com> - 2.0.0-0.2022.gitfe4810a0.1
- Another day, another snapshot
- Avoid building pdf docs

* Tue Mar 03 2015 Panu Matilainen <pmatilai@redhat.com> - 2.0.0-0.1916.gita001589e.2
- Add missing dependency to tools -subpackage

* Tue Mar 03 2015 Panu Matilainen <pmatilai@redhat.com> - 2.0.0-0.1916.gita001589e.1
- New snapshot
- Work around #1198009

* Mon Mar 02 2015 Panu Matilainen <pmatilai@redhat.com> - 2.0.0-0.1911.gitffc468ff.2
- Optionally package tools too, some binding script is needed for many setups

* Mon Mar 02 2015 Panu Matilainen <pmatilai@redhat.com> - 2.0.0-0.1911.gitffc468ff.1
- New snapshot
- Disable kernel module build by default
- Add patch to fix missing defines/includes for external applications

* Fri Feb 27 2015 Panu Matilainen <pmatilai@redhat.com> - 2.0.0-0.1906.git00c68563.1
- New snapshot
- Remove bogus devname module alias from eventfd-link module
- Whack evenfd-link to honor RTE_KERNELDIR too

* Thu Feb 26 2015 Panu Matilainen <pmatilai@redhat.com> - 2.0.0-0.1903.gitb67578cc.3
- Add spec option to build kernel modules too
- Build eventfd-link module too if kernel modules enabled

* Thu Feb 26 2015 Panu Matilainen <pmatilai@redhat.com> - 2.0.0-0.1903.gitb67578cc.2
- Move config changes from spec after "make config" to simplify things
- Move config changes from dpdk-config patch to the spec

* Thu Feb 19 2015 Panu Matilainen <pmatilai@redhat.com> - 2.0.0-0.1717.gitd3aa5274.2
- Fix warnings tripping up build with gcc 5, remove -Wno-error

* Wed Feb 18 2015 Panu Matilainen <pmatilai@redhat.com> - 2.0.0-0.1698.gitc07691ae.1
- Move the unversioned .so links for plugins into main package
- New snapshot

* Wed Feb 18 2015 Panu Matilainen <pmatilai@redhat.com> - 2.0.0-0.1695.gitc2ce3924.3
- Fix missing symbol export for rte_eal_iopl_init()
- Only mention libs once in the linker script

* Wed Feb 18 2015 Panu Matilainen <pmatilai@redhat.com> - 2.0.0-0.1695.gitc2ce3924.2
- Fix gcc version logic to work with 5.0 too

* Wed Feb 18 2015 Panu Matilainen <pmatilai@redhat.com> - 2.0.0-0.1695.gitc2ce3924.1
- Add spec magic to easily switch between stable and snapshot versions
- Add tarball snapshot script for reference
- Update to pre-2.0 git snapshot

* Thu Feb 12 2015 Panu Matilainen <pmatilai@redhat.com> - 1.8.0-15
- Disable -Werror, this is not useful behavior for released versions

* Wed Feb 11 2015 Panu Matilainen <pmatilai@redhat.com> - 1.8.0-14
- Fix typo causing librte_vhost missing DT_NEEDED on fuse

* Wed Feb 11 2015 Panu Matilainen <pmatilai@redhat.com> - 1.8.0-13
- Fix vhost library linkage
- Add spec option to build example applications, enable by default

* Fri Feb 06 2015 Panu Matilainen <pmatilai@redhat.com> - 1.8.0-12
- Enable librte_acl build
- Enable librte_ivshmem build

* Thu Feb 05 2015 Panu Matilainen <pmatilai@redhat.com> - 1.8.0-11
- Drop the private libdir, not needed with versioned libs

* Thu Feb 05 2015 Panu Matilainen <pmatilai@redhat.com> - 1.8.0-10
- Drop symbol versioning patches, always do library version for shared
- Add comment on the combined library thing

* Wed Feb 04 2015 Panu Matilainen <pmatilai@redhat.com> - 1.8.0-9
- Add missing symbol version to librte_cmdline

* Tue Feb 03 2015 Panu Matilainen <pmatilai@redhat.com> - 1.8.0-8
- Set soname of the shared libraries
- Fixup typo in ld path config file name

* Tue Feb 03 2015 Panu Matilainen <pmatilai@redhat.com> - 1.8.0-7
- Add library versioning patches as another build option, enable by default

* Tue Feb 03 2015 Panu Matilainen <pmatilai@redhat.com> - 1.8.0-6
- Add our libraries to ld path & run ldconfig when using shared libs

* Fri Jan 30 2015 Panu Matilainen <pmatilai@redhat.com> - 1.8.0-5
- Add DT_NEEDED for external dependencies (pcap, fuse, dl, pthread)
- Enable combined library creation, needed for OVS
- Enable shared library creation, needed for sanity

* Thu Jan 29 2015 Panu Matilainen <pmatilai@redhat.com> - 1.8.0-4
- Include scripts directory in the "sdk" too

* Thu Jan 29 2015 Panu Matilainen <pmatilai@redhat.com> - 1.8.0-3
- Fix -Wformat clash preventing i40e driver build, enable it
- Fix -Wall clash preventing enic driver build, enable it

* Thu Jan 29 2015 Panu Matilainen <pmatilai@redhat.com> - 1.8.0-2
- Enable librte_vhost, which buildrequires fuse-devel
- Enable physical NIC drivers that build (e1000, ixgbe) for VFIO use

* Thu Jan 29 2015 Panu Matilainen <pmatilai@redhat.com> - 1.8.0-1
- Update to 1.8.0

* Wed Jan 28 2015 Panu Matilainen <pmatilai@redhat.com> - 1.7.0-8
- Always build with -fPIC

* Wed Jan 28 2015 Panu Matilainen <pmatilai@redhat.com> - 1.7.0-7
- Policy compliance: move static libraries to -devel, provide dpdk-static
- Add a spec option to build as shared libraries

* Wed Jan 28 2015 Panu Matilainen <pmatilai@redhat.com> - 1.7.0-6
- Avoid variable expansion in the spec here-documents during build
- Drop now unnecessary debug flags patch
- Add a spec option to build a combined library

* Tue Jan 27 2015 Panu Matilainen <pmatilai@redhat.com> - 1.7.0-5
- Avoid unnecessary use of %%global, lazy expansion is normally better
- Drop unused destdir macro while at it
- Arrange for RTE_SDK environment + directory layout expected by DPDK apps
- Drop config from main package, it shouldn't be needed at runtime

* Tue Jan 27 2015 Panu Matilainen <pmatilai@redhat.com> - 1.7.0-4
- Copy the headers instead of broken symlinks into -devel package
- Force sane mode on the headers
- Avoid unnecessary %%exclude by not copying unpackaged content to buildroot
- Clean up summaries and descriptions
- Drop unnecessary kernel-devel BR, we are not building kernel modules

* Sat Aug 16 2014 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1.7.0-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_21_22_Mass_Rebuild

* Thu Jul 17 2014 - John W. Linville <linville@redhat.com> - 1.7.0-2
- Use EXTRA_CFLAGS to include standard Fedora compiler flags in build
- Set CONFIG_RTE_MACHINE=default to build for least-common-denominator machines
- Turn-off build of librte_acl, since it does not build on default machines
- Turn-off build of physical device PMDs that require kernel support
- Clean-up the install rules to match current packaging
- Correct changelog versions 1.0.7 -> 1.7.0
- Remove ix86 from ExclusiveArch -- it does not build with above changes

* Thu Jul 10 2014 - Neil Horman <nhorman@tuxdriver.com> - 1.7.0-1.0
- Update source to official 1.7.0 release 

* Thu Jul 03 2014 - Neil Horman <nhorman@tuxdriver.com>
- Fixing up release numbering

* Tue Jul 01 2014 - Neil Horman <nhorman@tuxdriver.com> - 1.7.0-0.9.1.20140603git5ebbb1728
- Fixed some build errors (empty debuginfo, bad 32 bit build)

* Wed Jun 11 2014 - Neil Horman <nhorman@tuxdriver.com> - 1.7.0-0.9.20140603git5ebbb1728
- Fix another build dependency

* Mon Jun 09 2014 - Neil Horman <nhorman@tuxdriver.com> - 1.7.0-0.8.20140603git5ebbb1728
- Fixed doc arch versioning issue

* Mon Jun 09 2014 - Neil Horman <nhorman@tuxdriver.com> - 1.7.0-0.7.20140603git5ebbb1728
- Added verbose output to build

* Tue May 13 2014 - Neil Horman <nhorman@tuxdriver.com> - 1.7.0-0.6.20140603git5ebbb1728
- Initial Build

