from trex.stl.api import STLClient, STLStream, STLPktBuilder, STLTXSingleBurst
from scapy.all import Ether, IP, UDP, Raw

# Connect to TRex
client = STLClient()
client.connect()
client.reset()

# Flow 1: 5-tuple #1
pkt1 = Ether()/IP(src="10.0.0.1", dst="192.168.0.1")/UDP(sport=1111, dport=2222)/Raw(load="flow1")
stream1 = STLStream(
    packet=STLPktBuilder(pkt=pkt1),
    mode=STLTXSingleBurst(total_pkts=100, pps=100)
)

# Flow 2: 5-tuple #2
pkt2 = Ether()/IP(src="10.0.0.2", dst="192.168.0.2")/UDP(sport=3333, dport=4444)/Raw(load="flow2")
stream2 = STLStream(
    packet=STLPktBuilder(pkt=pkt2),
    mode=STLTXSingleBurst(total_pkts=100, pps=100)
)

# Add both streams to port 0
client.add_streams([stream1, stream2], ports=[0])

# Start traffic
client.start(ports=[0])
client.wait_on_traffic(ports=[0])

# Show statistics
print(client.get_stats())

client.disconnect()
