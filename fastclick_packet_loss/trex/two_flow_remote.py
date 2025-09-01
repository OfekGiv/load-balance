#!/usr/bin/env python3

from trex.stl.api import STLClient, STLStream, STLPktBuilder, STLTXSingleBurst
from scapy.all import Ether, IP, UDP, Raw
import argparse


def build_stream(pkt, total_pkts=100, pps=100,delay_ns=0):
    return STLStream(
        packet=STLPktBuilder(pkt=pkt),
        mode=STLTXSingleBurst(total_pkts=total_pkts, pps=pps),
        isg=delay_ns
    )


def run_two_flows(server, port, pkts, pps, dst1, dst2):
    client = STLClient(server=server)
    client.connect()
    client.reset(ports=[port])

    # Flow 1
    pkt1 = Ether()/IP(src="10.0.0.1", dst=dst1)/UDP(sport=1111, dport=2222)/Raw(load="flow1")
    stream1 = build_stream(pkt1, pkts, pps)

    # Flow 2
    pkt2 = Ether()/IP(src="10.0.0.1", dst=dst2)/UDP(sport=1111, dport=2222)/Raw(load="flow2")
    stream2 = build_stream(pkt2, pkts, pps, 2_000_000)


    client.add_streams(stream1, ports=[port])
    #client.add_streams([stream1, stream2], ports=[port])
    client.start(ports=[port])
    client.wait_on_traffic(ports=[port])

    stats = client.get_stats()
    print(f"\n[+] Stats for port {port}:")
    print(stats[port])

    client.disconnect()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--server", default="127.0.0.1", help="TRex server IP")
    parser.add_argument("-p", "--port", default=0, type=int, help="Port to send traffic on")
    parser.add_argument("--pkts", type=int, default=100, help="Total packets per flow")
    parser.add_argument("--pps", type=int, default=100, help="Packets per second per flow")
    parser.add_argument("--dst1", required=True, help="Destination IP for flow 1")
    parser.add_argument("--dst2", required=True, help="Destination IP for flow 2")
    args = parser.parse_args()

    run_two_flows(args.server, args.port, args.pkts, args.pps, args.dst1, args.dst2)
