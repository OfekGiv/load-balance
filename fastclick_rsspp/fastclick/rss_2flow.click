// **FastClick Static RSS Example** 
// This configuration uses NIC hardware RSS to spread incoming traffic across multiple RX queues.
// No RSS++ or dynamic load balancing is used – all distribution is done by the NIC hardware.

ControlSocket(TCP, 1234);

// Define configuration parameters for clarity and easy adjustment:
define($DPDK_PORT 0);        // DPDK port index (e.g., 0 for first port)
define($RX_QUEUES 8);        // Number of RX queues to use for RSS (e.g., 8 queues)
define($BURST_SIZE 32);      // Burst size for packet retrieval (max packets per poll)
define($PROMISC_MODE true);  // Promiscuous mode (true to receive all packets)

// Initialize a DPDK input device with hardware RSS enabled.
// - N_QUEUES $RX_QUEUES: use the specified number of hardware RX queues on the port.
// - RSS_AGGREGATE true: NIC's RSS hash is enabled and copied to packet annotation:contentReference[oaicite:3]{index=3}.
// - PROMISC $PROMISC_MODE: set the NIC to promiscuous mode to capture all traffic.
// - BURST $BURST_SIZE: number of packets to retrieve from the NIC in one batch (poll).
fd0 :: FromDPDKDevice($DPDK_PORT,
                      N_QUEUES $RX_QUEUES,
                      RSS_AGGREGATE true,
                      PROMISC $PROMISC_MODE,
                      BURST $BURST_SIZE);

// The FromDPDKDevice element (fd0) will output packets from each RX queue separately.
// Here we connect each queue output directly to a Discard element.
// This means all received packets are dropped, but it demonstrates that packets 
// from different RSS queues can be handled independently (static spread across queues).
fd0 -> Discard();  // Packets from RX queue 0 -> drop
// (Adjust the number of outputs above to match $RX_QUEUES if changed.)

