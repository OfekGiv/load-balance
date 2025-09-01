// Define parameters for the test configuration
define($PORT 0);              // DPDK port index to use (e.g., 0 for first port)
define($N_QUEUES 8);          // Number of RX queues (and threads/cores) to use
define($RETA_SIZE 512);       // NIC RSS indirection table size (e.g., 128 entries typical)
define($BURST 32);            // I/O burst size for DPDK (packets per poll)
define($PROMISC true);        // Enable promiscuous mode (capture all traffic)

// ----- Control -----

ControlSocket(TCP, 1234);
// DPDK input: Open port $PORT with $N_QUEUES RX queues, enabling RSS hashing.
// RSS_AGGREGATE true => annotate packets with NIC's RSS hash for aggregation.
fd0 :: FromDPDKDevice($PORT, N_QUEUES $N_QUEUES, BURST $BURST, PROMISC $PROMISC, RSS_AGGREGATE true);

// Counter element to count packets per RSS bucket (using lower bits of hash).
// MASK 127 gives 128 bins (0–127) corresponding to possible bucket indices if RETA_SIZE=128.
agg :: AggregateCounterVector(MASK 511);

// Connect input to counter and then to output (here we simply drop the packets after counting).
fd0 -> agg -> Discard;  

// DeviceBalancer element from RSS++: configures NIC’s RSS indirection table and (if dynamic) rebalances.
// Here we set METHOD to "rss" for static distribution (classical RSS).
balancer :: DeviceBalancer( 
    DEV fd0,               // target device element (FromDPDKDevice) to control NIC
    METHOD rsspp,            // static RSS method (no dynamic rebalancing):contentReference[oaicite:0]{index=0}
    CPUS $N_QUEUES,        // number of CPU cores/RX queues to use for load-spreading
    RSSCOUNTER agg,        // use our AggregateCounterVector for packet counts (optional for static)
    RETA_SIZE $RETA_SIZE,  // size of the NIC's indirection table (buckets count)
    VERBOSE 2              // verbosity level (prints mapping info at startup)
);
