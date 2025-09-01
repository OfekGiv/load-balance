#import stl_path
from trex.stl.api import *

import time
import json
from pprint import pprint
import argparse
import sys
import os

def mask_list(l, mask):
    res = []
    for i in l:
        if mask & 1:
            res.append(i)
        mask >>= 1
    return res

# IMIX test
# it maps the ports to sides
# then it load a predefind profile 'IMIX'
# and attach it to both sides and inject
# at a certain rate for some time
# finally it checks that all packets arrived
def imix_test (server, mult, profile_name, duration, length, ports):

    # create client
    c = STLClient(server = server)

    passed = True

    try:

        # connect to server
        c.connect()

        # take all the ports
        c.reset()

        # map ports - identify the routes
        #table = stl_map_ports(c)
        #print table
        #dir_0 = [x for x in table['map'].keys()]
        #dir_1 = [x for x in table['map'].values()]
        dir_0 = [0] 
        dir_1 = []
        dir_0 = mask_list(dir_0, ports)
        dir_1 = mask_list(dir_1, ports)
        print ("ports:", ports, dir_0, dir_1)

        #print("Mapped ports to sides {0} <--> {1}".format(dir_0, dir_1))

        # load IMIX profile
        for port_id in dir_0:
            profile = STLProfile.load_py(profile_name, port_id = port_id, size = length)
            streams = profile.get_streams()
            #print [(s.get_pg_id()) for s in streams]
            c.add_streams(streams, ports = port_id)

        # clear the stats before injecting
        c.clear_stats()

        # choose rate and start traffic for 10 seconds
        #print("Injecting {0} <--> {1} on total rate of '{2}' for {3} seconds".format(dir_0, dir_1, mult, duration))

        c.start(ports = (dir_0 + dir_1), mult = mult, duration = duration, total = True)

        # block until done
        c.wait_on_traffic(ports = (dir_0 + dir_1))

        # read the stats after the test
        stats = c.get_stats()

        #for pg_id, s in stats['latency'].items():
        #    if pg_id == 'global':
        #        continue
        #    pprint(s['latency'])

        # use this for debug info on all the stats
        s = {'latency' : stats['latency'], 'global' : stats['global']}
        pprint(s)

        # sum dir 0
        dir_0_opackets = sum([stats[i]["opackets"] for i in dir_0])
        dir_0_ipackets = sum([stats[i]["ipackets"] for i in dir_0])

        # sum dir 1
        dir_1_opackets = sum([stats[i]["opackets"] for i in dir_1])
        dir_1_ipackets = sum([stats[i]["ipackets"] for i in dir_1])


        lost_0 = dir_0_opackets - dir_1_ipackets
        lost_1 = dir_1_opackets - dir_0_ipackets

        #print("\nPackets injected from {0}: {1:,}".format(dir_0, dir_0_opackets))
        #print("Packets injected from {0}: {1:,}".format(dir_1, dir_1_opackets))

        #print("\npackets lost from {0} --> {1}:   {2:,} pkts".format(dir_0, dir_0, lost_0))
        #print("packets lost from {0} --> {1}:   {2:,} pkts".format(dir_1, dir_1, lost_1))

        if c.get_warnings():
            print("\n\n*** test had warnings ****\n\n")
            for w in c.get_warnings():
                print(w)

        #if (lost_0 <= 0) and (lost_1 <= 0) and not c.get_warnings(): # less or equal because we might have incoming arps etc.
        #    passed = True
        #else:
        #    passed = False


    except STLError as e:
        passed = False
        print(e)
        sys.exit(1)

    finally:
        c.disconnect()

    #if passed:
    #    print("\nTest has passed :-)\n")
    #else:
    #    print("\nTest has failed :-(\n")

parser = argparse.ArgumentParser(description="Example for TRex Stateless, sending IMIX traffic")
parser.add_argument('-s', '--server',
                    dest='server',
                    help='Remote trex address',
                    default='127.0.0.1',
                    type = str)
parser.add_argument('-m', '--mult',
                    dest='mult',
                    help='Multiplier of traffic, see Stateless help for more info',
                    default='30%',
                    type = str)
parser.add_argument('-p', '--profile',
                    dest='profile',
                    help='Profile to load',
                    default='imix.py',
                    type = str)
parser.add_argument('-d', '--duration',
                    dest='duration',
                    help='Duration of test',
                    default=10,
                    type = int)
parser.add_argument('-l', '--length',
                    dest='length',
                    help='Packet legnth',
                    default=1514,
                    type = int)
parser.add_argument('-n', '--ports',
                    dest='ports',
                    help='Active ports mask',
                    default=0x3,
                    type = int)
args = parser.parse_args()

# run the tests
imix_test(args.server, args.mult, args.profile, args.duration, args.length, args.ports)

