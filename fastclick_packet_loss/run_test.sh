#!/bin/bash
export PYTHONPATH=$PYTHONPATH:/homes/ofekg/trex-core/scripts/automation/trex_control_plane/interactive
loader1="132.68.206.105"
# === CONFIGURATION ===
GENERATOR_HOST=ofek.givony@132.68.206.105       # change to your TRex machine's user@IP
GENERATOR_DIR=/homes/ofekg/trex-core     # change to the directory where trex is
FASTCLICK_DIR=/homes/ofekg/fastclick
# Default NUM_CORES if not set
[ -z "$NUM_CORES" ] && NUM_CORES=2
# Packets per second to generate and transmit
#[ -z "$PPS" ] && PPS=12000000
[ -z "$PPS" ] && PPS=10000000
# Number of packets to generate
[ -z "$PACKETS_NUM" ] && PACKETS_NUM=$((PPS * 10))
[ -z "$FLOW_DST1" ] && FLOW_DST1=192.168.0.1
[ -z "$FLOW_DST2" ] && FLOW_DST2=192.168.1.6

LAST_CORE=$((NUM_CORES - 1))
LCORES="-l 0-$LAST_CORE"

echo "sudo $FASTCLICK_DIR/bin/click --dpdk $LCORES -- fastclick/packet_counter.click &"
timeout -k 1s 22s sudo $FASTCLICK_DIR/bin/click --dpdk $LCORES -- fastclick/packet_counter.click &

sleep 5

printf "WRITE in.reset_counts 1\n" | nc -N 127.0.0.1 1234
printf "WRITE in.reset_load 1\n"   | nc -N 127.0.0.1 1234
printf "WRITE c_match.reset\n" | nc -N 127.0.0.1 1234
printf "READ c_match.count\n" | nc -N 127.0.0.1 1234 \
  | tail -n1 \
  | awk '{ printf("c_match.count = %s\n", $1) }'

# run for 17 seconds, sample every 0.5s, write to cpu_load_wide.csv
#python3 cpu_logger.py --duration 17 --interval 0.5 --out cpu_load.csv &


python3 trex/two_flow_remote.py -s 132.68.206.105 -p 0 --pkts $PACKETS_NUM --pps $PPS --dst1 $FLOW_DST1 --dst2 $FLOW_DST2 > /dev/null 2>&1 &

sleep 5
printf "READ load\n" | nc -N 127.0.0.1 1234 \
  | tail -n1 \
  | awk '{ for (i=1; i<=NF; i++) printf("CPU%d: %.1f%%\n", i-1, $i*100) }'

sleep 10
printf "READ c_match.count\n" | nc -N 127.0.0.1 1234 \
  | tail -n1 \
  | awk '{ printf("c_match.count = %s\n", $1) }'
# Read SW vs HW tallies
printf "READ in.xstats\n"     | nc -N 127.0.0.1 1234   # full driver counters (rx_missed, rx_errors, etc.)

#printf "READ load\n" | nc -N 127.0.0.1 1234 | tail -n1
#echo
#printf "READ load\n" | nc -N 127.0.0.1 1234
#echo ''

sleep 2
echo "Finished"
#printf "READ fd0.queue_packets\n" | nc -N 127.0.0.1 1234 | tail -n1 | awk '{print "fd0.queue_packets:", $0}'
#printf "READ fd1.queue_packets\n" | nc -N 127.0.0.1 1234 | tail -n1 | awk '{print "fd1.queue_packets:", $0}'

#printf "READ fd0.queue_packets\r\n" | nc -N 127.0.0.1 1234
#echo ''
#printf "READ fd1.queue_packets\r\n" | nc -N 127.0.0.1 1234
#echo ''

#for q in 0 1; do
#  printf "Queue %d: %s packets\n" \
#    "$q" \
#    "$(printf "READ fd${q}.queue_packets\n" | nc -N 127.0.0.1 1234 | awk '/^DATA/{print $2}')"
#done
