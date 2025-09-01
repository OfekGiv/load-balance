#~/bin/bash

basedir=`dirname \`realpath $0\``
DPDK_BASE=/homes/ofekg/dpdk/build
FCLICK_BASE=/homes/ofekg/fastclick/
TREX_BASE=/homes/ofekg/trex-core/scripts
DEF_TRACE_FILE=/homes/ofekg/trex-core/scripts/equinix-nyc.dirA.20190117-125910/test.fixed.pcap

loader1="132.68.206.105"
export PYTHONPATH=/homes/ofekg/trex-core/scripts/automation/trex_control_plane/interactive:$PYTHONPATH
# output directory
[ -z "$OUT_FILE" ] && OUT_FILE=/tmp

# click params
[ -z "$IF1PCI" ] && IF1PCI=0000:3b:00.0 # PCIe BDF for $if1 on dante732

# kernel pktgen params
#[ -z "$IF" ] && IF=enp94s0f1 # $if1 on dante732
#[ -z "$DMAC" ] && DMAC=0c:42:a1:1d:3a:fb # dmac for $if1 on dante732
#[ -z "$DIP" ] && DIP=101.0.0.0/12 # dmac for $if1 on dante732
#[ -z "$FLOWS" ] && FLOWS=1000000
#[ -z "$FLOWLEN" ] && FLOWLEN=2
#[ -z "$COUNT" ] && COUNT=1000000000
#[ -z "$THREADS" ] && THREADS=20
#[ -z "$DPORT" ] && DPORT=1234

# click params
[ -z "$MEMTYPE" ] && MEMTYPE="base"
#[ -z "$MEMTYPE" ] && MEMTYPE="host"
#[ -z "$MEMTYPE" ] && MEMTYPE="nic"

[ -z "$TIME" ] && TIME=20
[ -z "$WARMUP" ] && WARMUP=0
[ -z "$PKT_SIZE" ] && PKT_SIZE=1500
[ -z "$CORES" ] && CORES=1

# trex params
[ -z "$LOAD" ] && LOAD=100
[ -z "$TMPL" ] && TMPL=cap2/imix_1518.yaml
[ -z "$TRACE" ] && TRACE=1 # use packet trace file 
[ -z "$TRACE_FILE" ] && TRACE_FILE=$DEF_TRACE_FILE

## generic fastclick script parameters (see fastclick.x.$PORTS.npf)
[ -z $CAPACITY ] && echo Missing CAPACITY setting to 20000000 && export CAPACITY=10000000 
[ -z $CPUS1 ] && echo Missing CPUS1 setting to CORES=$CORES &&   export CPUS1=$CORES
[ -z $CPUS2 ] && echo Missing CPUS2 setting to CORES=$CORES &&   export CPUS2=$CORES
[ -z $RXDESC ] && echo Missing RXDESC setting to 1024 &&         export RXDESC=1024
[ -z $DDIO_WAYS ] && echo Missing DDIO_WAYS setting to 2 &&      export DDIO_WAYS=2

[ -z "$MLXINLINE" ] && MLXINLINE="0"
[ -z "$MLXCOMPRESS" ] && MLXCOMPRESS="0"
[ -z "$MLXMPRQ" ] && MLXMPRQ="0"

if [ $MEMTYPE == "host" ]; then
	echo "[+] host split memory"
	_MEMTYPE="--dpdk-split"
elif [ $MEMTYPE == "base" ]; then
	echo "[+] host baseline memory"
	_MEMTYPE=""
elif [ $MEMTYPE == "nic" ]; then
	echo "[+] nic memory"
	_MEMTYPE="--dpdk-nicmem --dpdk-split"
elif [ $MEMTYPE == "nic-inline" ]; then
	echo "[+] nic memory"
	_MEMTYPE="--dpdk-nicmem --dpdk-split"
        MLXINLINE="1"
else
	echo "[-] unknown memtype $MEMTYPE"
	exit -1
fi

if [ $MLXINLINE == "0" ]; then
  echo '[-] not using inline'
  MLXFLAGS="" # MLXFLAGS="txq_inline_min=64"
else
  echo '[+] inlining 64 bytes'
  MLXFLAGS="txq_inline_min=64"
fi

# try to use many cores
CORE_MASK="0xfffffffc"

(( "$TIME" <= "10" )) && echo "TIME ($TIME) must be greater than 10" && exit -1

IF1PCI_FLAGS=,$MLXFLAGS,rxq_cqe_comp_en=0,mprq_en=0
# single/dual port
if [ -z "${IF2PCI+x}" ]; then
	echo "[+] single port" $IF1PCI
	PORTS_MASK=1
	PORTS=1
	IF2PCI_PREFIX=""
        IF2PCI_FLAGS=""
else
	echo "[+] dual port" $IF1PCI " " $IF2PCI
	PORTS_MASK=3 # PORTS_MASK is a mask 3=0x11 (two ports)
	PORTS=2
	IF2PCI_PREFIX="-w "
        IF2PCI_FLAGS=,$MLXFLAGS,rxq_cqe_comp_en=0,mprq_en=0
fi

#-------------------------------------------------
# kill previous instances
sudo pkill -f $FCLICK_BASE/bin/click
sleep 3

# avoid killing trex as it has a server
# # kill the load generator
# echo ssh $loader1 sudo pkill --signal SIGINT pktgen
# ssh $loader1 sudo pkill --signal SIGINT pktgen
#-------------------------------------------------

# run new click instance using GENERIC values
export STARTUP=$[$WARMUP+10]
export FCLICK_TIME=$[$TIME-$WARMUP-10]
envsubst '${FCLICK_TIME} ${STARTUP} ${CAPACITY} ${CPUS1} ${CPUS2} ${RXDESC} ${DDIO_WAYS}' < fastclick.x.$PORTS.npf > fastclick.envsubst.$PORTS.npf 
echo sudo -E $FCLICK_BASE/bin/click $_MEMTYPE --dpdk -c $CORE_MASK -- fastclick.envsubst.$PORTS.npf
sudo -E $FCLICK_BASE/bin/click $_MEMTYPE --dpdk -c $CORE_MASK -- fastclick.envsubst.$PORTS.npf |& tee -a $OUT_FILE/fclick_lb.txt &

sleep 10

# run kernel pktgen load-generator
# echo "ssh $loader1 FLOWS=$FLOWS FLOWLEN=$FLOWLEN $basedir/pktgen/pktgen_sample04_many_flows.sh -i $IF -m $DMAC -d $DIP -n $COUNT -t $THREADS -p $DPORT -s $PKT_SIZE > /dev/null"
# ssh $loader1 FLOWS=$FLOWS FLOWLEN=$FLOWLEN $basedir/pktgen/pktgen_sample04_many_flows.sh -i $IF -m $DMAC -d $DIP -n $COUNT -t $THREADS -p $DPORT -s $PKT_SIZE > /dev/null &
# echo sleeping $TIME ...
# sleep $TIME

# trex warmup
if [ $WARMUP == "0" ]; then
	echo "Skipping warmup"
e
	echo python3 trex/stl_imix.py -s $loader1 -p trex/imix_lat.py -d $WARMUP -m $LOAD% -l $PKT_SIZE --ports $PORS
	#python3 trex/stl_imix.py -s $loader1 -p trex/imix_lat.py -d $WARMUP -m $LOAD% -l $PKT_SIZE --ports $PORTS_MASK
fi

# run trex load-generator
#echo "ssh $loader1 \"cd $TREX_BASE; sudo -E ./_t-rex-64-o --cfg $TREX_BASE/trex_cfg.yaml -f $TMPL -c 4 -m $LOAD% -d $TIME --no-ofed-check --mlx5-so -l 10 --hdrh\""
#ssh $loader1 "cd $TREX_BASE; sudo -E ./_t-rex-64-o --cfg $TREX_BASE/trex_cfg.yaml -f $TMPL -c 4 -m $LOAD% -d $TIME --no-ofed-check --mlx5-so -l 10 --hdrh" | tee -a $OUT_FILE/trex.txt
if [ -z "$TRACE" ]; then
  echo python3 trex/stl_imix.py -s $loader1 -p trex/imix_lat.py -d $FCLICK_TIME -m $LOAD% -l $PKT_SIZE --ports $PORS
  #python3 trex/stl_imix.py -s $loader1 -p trex/imix_lat.py -d $FCLICK_TIME -m $LOAD% -l $PKT_SIZE --ports $PORTS_MASK |& tee -a $OUT_FILE/trex.txt
else
  echo python3 trex/stl_remote.py -s $loader1 -d $FCLICK_TIME -m $LOAD% -f $TRACE_FILE --ports $PORTS_MASK
  #python3 trex/stl_remote.py -s $loader1 -d $FCLICK_TIME -m $LOAD% -f $TRACE_FILE --ports $PORTS_MASK & # never terminates
  sleep $FCLICK_TIME; pkill -f trex/stl_remote.py
fi

#-------------------------------------------------
# kill the load generator
#echo ssh $loader1 sudo pkill --signal SIGINT pktgen
#ssh $loader1 sudo pkill --signal SIGINT pktgen

# kill this instances
sudo pkill -f $FCLICK_BASE/bin/click
#-------------------------------------------------

env > $OUT_FILE/env.txt
