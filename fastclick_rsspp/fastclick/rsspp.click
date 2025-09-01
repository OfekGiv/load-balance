// Use NIC port 0 in RSS mode with 4 cores
fd0 :: FromDPDKDevice(0, PROMISC true, RSS_AGGREGATE 1, N_QUEUES 4, SCALE parallel);

// Count packets per queue
agg :: AggregateCounterVector(MASK 511);

// Simple fake per-packet work
work :: Idle;

// Send out the packet
out :: ToDPDKDevice(0);

// Main pipeline
fd0 -> agg -> work -> out;
StaticThreadSched(bal 4);

// RSS++ load balancer (for RSS++ config only):
bal :: DeviceBalancer(DEV fd0, METHOD rsspp, RSSCOUNTER agg,
                      CPUS 4, TARGET_LOAD 0.75, AUTOSCALE true, 
                      CYCLES cycles, RETA_SIZE 128, IMBALANCE_THRESHOLD 0.02);
StaticThreadSched(bal 4);  // pin balancer to core 4 (workers on cores 0-3)
