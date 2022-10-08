#!/bin/bash

source configlib.sh

# Generates arch configurations in the current directory based on
# 1. an dpdk.spec file
# 2. an expanded dpdk tree

if (( $# != 2 )); then
    echo "$0: dpdk.spec dpdk_tree" >&2
    exit 1
fi

DPDKSPEC="$1"
DPDKDIR="$2"

# accumulate all arch + name triples
DPDK_CONF_MACH_ARCH=()
for arch in $(grep %define\ machine_arch "$DPDKSPEC" | sed 's@%define machine_arch @@')
do
    DPDK_CONF_MACH_ARCH+=($arch)
done

DPDK_CONF_MACH_TMPL=()
for tmpl in $(grep %define\ machine_tmpl "$DPDKSPEC" | sed 's@%define machine_tmpl @@')
do
    DPDK_CONF_MACH_TMPL+=($tmpl)
done

DPDK_CONF_MACH=()
for mach in $(grep %define\ machine\  "$DPDKSPEC" | sed 's@%define machine @@')
do
    DPDK_CONF_MACH+=($mach)
done

DPDK_TARGETS=()
for ((i=0; i < ${#DPDK_CONF_MACH[@]}; i++));
do
    DPDK_TARGETS+=("${DPDK_CONF_MACH_ARCH[$i]}-${DPDK_CONF_MACH_TMPL[$i]}-linuxapp-gcc")
    echo "DPDK-target: ${DPDK_TARGETS[$i]}"
done

OUTPUT_DIR=$(pwd)
pushd "$DPDKDIR"
for ((i=0; i < ${#DPDK_TARGETS[@]}; i++));
do
    echo "For ${DPDK_TARGETS[$i]}:"

    echo "     a. Generating initial config"
    echo "        make V=1 T=${DPDK_TARGETS[$i]} O=${DPDK_TARGETS[$i]}"
    make V=1 T=${DPDK_TARGETS[$i]} O=${DPDK_TARGETS[$i]} -j8 config
    ORIG_SHA=""
    OUTDIR="${DPDK_TARGETS[$i]}"

    echo "     b. calculating and applying sha"
    calc_sha ORIG_SHA "${OUTDIR}/.config"
    if [ "$ORIG_SHA" == "" ]; then
        echo "ERROR: Unable to get sha for arch ${DPDK_TARGETS[$i]}"
        exit 1
    fi
    echo "# -*- cfg-sha: ${ORIG_SHA}" > ${OUTDIR}/.config.new
    cat "${OUTDIR}/.config" >> "${OUTDIR}/.config.new"
    cp "${OUTDIR}/.config" "${OUTDIR}/.config.orig"
    mv -f "${OUTDIR}/.config.new" "${OUTDIR}/.config"

    echo "     c. setting initial configurations"
    # these are the original setconf values from dpdk.spec
    set_conf "${OUTDIR}" CONFIG_RTE_MACHINE "\\\"${DPDK_CONF_MACH[$i]}\\\""

    # Enable automatic driver loading from this path
    set_conf "${OUTDIR}" CONFIG_RTE_EAL_PMD_PATH '"/usr/lib64/dpdk-pmds"'

    # Disable DPDK libraries not needed
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_TIMER n
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_CFGFILE n
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_JOBSTATS n
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_LPM n
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_ACL n
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_POWER n
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_SCHED n
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_DISTRIBUTOR n
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_REORDER n
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_PORT n
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_TABLE n
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_PIPELINE n
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_KNI n
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_CRYPTODEV n
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_SECURITY n
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_FLOW_CLASSIFY n
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_BBDEV n
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_COMPRESSDEV n
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_BPF n
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_OCTEONTX_MEMPOOL n
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_DPAA_MEMPOOL n
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_DPAA2_MEMPOOL n
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_CFGFILE n
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_EFD n
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_FLOW_CLASSIFY n

    # Disable all eventdevs
    for eventdev in $(grep _EVENTDEV= "${OUTDIR}/.config" | sed 's@=\(y\|n\)@@g')
    do
        set_conf "${OUTDIR}" $eventdev n
    done

    # Disable all rawdevs
    for rawdev in $(grep _RAWDEV= "${OUTDIR}/.config" | sed 's@=\(y\|n\)@@g')
    do
        set_conf "${OUTDIR}" $rawdev n
    done

    # Disable virtio user
    set_conf "${OUTDIR}" CONFIG_RTE_VIRTIO_USER n

    # Enable vhost numa as libnuma dep is ok
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_VHOST_NUMA y

    # start by disabling ALL PMDs
    for pmd in $(grep _PMD= "${OUTDIR}/.config" | sed 's@=\(y\|n\)@@g')
    do
        set_conf "${OUTDIR}" $pmd n
    done

    # PMDs which have their own naming scheme
    # the default for this was 'n' at one point.  Make sure we keep it
    # as such
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_PMD_QAT n
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_PMD_OCTEONTX_SSOVF n
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_PMD_OCTEONTX_ZIPVF n
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_PMD_VHOST n
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_PMD_KNI n
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_PMD_XENVIRT n
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_PMD_NULL_CRYPTO n
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_PMD_NULL n
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_PMD_CRYPTO_SCHEDULER n
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_PMD_SKELETON_EVENTDEV n
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_PMD_SW_EVENTDEV n
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_PMD_PCAP n
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_PMD_BOND n
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_PMD_AF_PACKET n
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_PMD_SOFTNIC n
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_PMD_DPAA2_SEC n
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_PMD_DPAA_SEC n
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_PMD_VIRTIO_CRYPTO n
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_COMMON_DPAAX n
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_PMD_CAAM_JR n
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_PMD_CAAM_JR_BE n
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_PMD_BBDEV_NULL n
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_PMD_OCTEONTX_CRYPTO n

    # whitelist of enabled PMDs
    # Soft PMDs to enable
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_PMD_RING y
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_PMD_VHOST y
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_VIRTIO_PMD y
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_PMD_TAP y
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_PMD_FAILSAFE y


    # start by disabling all buses
    for bus in $(grep _BUS= "${OUTDIR}/.config" | sed 's@=\(y\|n\)@@g')
    do
        set_conf "${OUTDIR}" $bus n
    done

    # blacklist buses that don't conform to std naming
    # May override VMBUS later in arch specific section
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_VMBUS n

    # whitelist buses
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_PCI_BUS y
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_VDEV_BUS y


    # Disable some other miscellanous items related to test apps
    set_conf "${OUTDIR}" CONFIG_RTE_TEST_BBDEV n
    set_conf "${OUTDIR}" CONFIG_RTE_APP_CRYPTO_PERF n

    # Disable kernel modules
    set_conf "${OUTDIR}" CONFIG_RTE_EAL_IGB_UIO n
    set_conf "${OUTDIR}" CONFIG_RTE_KNI_KMOD n

    # Disable experimental stuff
    set_conf "${OUTDIR}" CONFIG_RTE_NEXT_ABI n

    # Build DPDK as shared library
    set_conf "${OUTDIR}" CONFIG_RTE_BUILD_SHARED_LIB y

    # Compile the PMD test application
    set_conf "${OUTDIR}" CONFIG_RTE_TEST_PMD y

    # Arch specific
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_I40E_PMD y
    case "${DPDK_CONF_MACH_ARCH[i]}" in
    x86_64)
        # Hw PMD
        set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_BNXT_PMD y
        set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_ENIC_PMD y
        set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_MLX4_PMD y
        set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_MLX4_DLOPEN_DEPS y
        set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_MLX5_PMD y
        set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_MLX5_DLOPEN_DEPS y
        set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_NFP_PMD y
        set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_QEDE_PMD y
        # Sw PMD
        set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_NETVSC_PMD y
        set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_VDEV_NETVSC_PMD y
        # Bus
        set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_VMBUS y
        ;&
    arm64)
        set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_IXGBE_PMD y
        set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_IGB_PMD y
        ;;
    esac

    cp "${OUTDIR}/.config" "${OUTPUT_DIR}/${DPDK_TARGETS[$i]}-config"
done
popd >/dev/null

echo -n "For each arch ( "
for ((i=0; i < ${#DPDK_CONF_MACH_ARCH[@]}; i++));
do
    echo -n "${DPDK_CONF_MACH_ARCH[i]} "
done
echo "):"
echo "1. ensure you enable the requisite hw"
