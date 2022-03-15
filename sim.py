from asyncio import base_tasks
from concurrent.futures import thread
import time
import queue
import random
from typing import Type
import numpy as np
from packet import Packet
import threading
from host import Host
import math
from constants import *
from concurrent.futures import ThreadPoolExecutor
import sys

# Switch queues, and a place to store the successfully delivered packets
switches = [queue.Queue()] * 4
delivered_packs = queue.Queue()


'''
Generates a packet object. In the paper, the authors note that
30-50% of DC packets are less than 256 bytes. Thus, I choose 
packet sizes from a normal distribution centered around 256
'''
def pack_gen(priority, epoch, src=-1, dst=-1):
    pack_size = math.floor(np.random.normal(loc=256.0, scale=75.0, size=1))
    
    if pack_size > 1000:
            pack_size = 1000
            
    if pack_size <= 0:
        pack_size = 1
    
    pkt = Packet(priority, pack_size, epoch, src, dst)
    return pkt

'''
Worker function for hosts. Iterates through the host's queues,
round robin sends packets from non empty buckets.
'''
def host_egress_controller(host: Host, end_time):
    while time.time() < end_time:
        for i in range(4):
            if host.queue.empty():
                continue
            
            pkt = host.queue.get()
            
            if pkt:
                switches[host.group].put(pkt)
    return

'''
Worker function for ToR switches. Identifies whether to route the packet
through the aggregation switch or to a directly connected host
'''
def switch_egress_controller(switch: queue.Queue, end_time, group):
    while time.time() < end_time:
        if switch.empty():
            continue
        
        pkt = switch.get()
        
        if pkt:
            # variable group is used to determine if the packet is going to a host connected
            # to this ToR. If not, we route to the aggregation switch
            if math.floor(pkt.dst/4) == group:
                pkt.set_t_delivered(time.time())
                delivered_packs.put(pkt)
            else:
                switches[3].put(pkt)
    return

'''
Worker function for the aggregation switch. Determines which ToR to route to
'''
def agg_egress_controller(switch:queue.Queue, end_time):
    while time.time() < end_time:
        if switch.empty():
            continue
        
        pkt:Packet = switch.get()
        
        if pkt:
            # Determines the destination's ToR by calculating its group
            group = math.floor((pkt.dst+1)/4)
            switches[group].put(pkt)

    return

'''
Worker function for packet generation thread pool. Essentially just creates packets
and attempts to send them to the host egress queues.
'''
def pack_gen_worker(h, traffic_dist, curr_time, end_time, host_number, curr_epoch):
    # Determine priority based on traffic distribution
    qjump_level = random.random()
    for prio in range(4):
        if qjump_level < traffic_dist[prio]:
            break
        
    # Destination host number
    dst = random.randint(0, 11)
    
    while dst == 0:
        dst = random.randint(0, 11)
        
    pkt = pack_gen(prio, curr_time, host_number, dst)
    
    # Try to send packet to rate limiter. If the host's bucket[packet.priority] is full,
    # sleep for a network epoch and try sending the packet again.
    while(h.rate_limiter(pkt, curr_epoch) == 0 and time.time() < end_time):
        time.sleep(NETWORK_EPOCH)
        
    return
                


# A simulation of a network employing Qjump
def run(epochs, traffic_dist, p_tx):
    # End of sim
    end_time = time.time() + (epochs * NETWORK_EPOCH)
    
    # Host thread generation
    host_workers = []
    hosts = []
    for i in range(12):
        h = Host(math.floor((i+1)/4))
        hosts.append(h)
        host_workers.append(threading.Thread(target=host_egress_controller, args=(h, end_time)))
    
    # Switch thread generation
    switch_workers = []
    switch_workers.append(threading.Thread(target=switch_egress_controller, args=(switches[0], end_time, 0)))
    switch_workers.append(threading.Thread(target=switch_egress_controller, args=(switches[1], end_time, 1)))
    switch_workers.append(threading.Thread(target=switch_egress_controller, args=(switches[2], end_time, 2)))
    switch_workers.append(threading.Thread(target=agg_egress_controller, args=(switches[3], end_time)))
    
    # Starting helper threads
    for switch in switch_workers:
        switch.start()
    
    for host in host_workers:
        host.start()

    start_time = time.time()
    last_epoch = -1
    pool = ThreadPoolExecutor()
    pgen = 0
    
    # Main simulation loop. on each new epoch, there is a p_tx chance a host 'generates' a packet
    while time.time() < end_time:
        curr_epoch = math.floor((time.time() - start_time) / NETWORK_EPOCH)
        if curr_epoch > last_epoch:
            for i in range(12):
                if random.random() < p_tx:
                    pool.submit(pack_gen_worker, hosts[i], traffic_dist, time.time(), end_time, i, curr_epoch)
                    pgen += 1

    # Thread cleanup
    for switch in switch_workers:
        switch.join()
        
    for host in host_workers:
        host.join()
        
    pool.shutdown()
    
    print('Packets generated: ' + str(pgen))
    print('Packets successfully delivered: ' + str(delivered_packs.qsize()))
    print('NOTE: This discrepancy is not due to QJump, it is due to my implementation using threadsafe queues \n')
    
    packs_of_each_prio = [0] * 4
    while not delivered_packs.empty():
        packs_of_each_prio[delivered_packs.get().get_priority()] += 1
    
    print('Priority 0 packets delivered: ' + str(packs_of_each_prio[0]))
    print('Priority 1 packets delivered: ' + str(packs_of_each_prio[1]))
    print('Priority 2 packets delivered: ' + str(packs_of_each_prio[2]))
    print('Priority 3 packets delivered: ' + str(packs_of_each_prio[3]))

    
                                    
                    

# A simulation of the rate limiter, the main contribution of Qjump, in a single host
def rate_limit_sim(epochs, traffic_dist, avg_pkt_per_epoch):
    tokens = [
        QJUMP_0,
        QJUMP_1,
        QJUMP_2,
        QJUMP_3
    ]
    retrans = []
    sent = []
    
    pkt_list = []
    
    # Packet generation loop. This simulation uses packets per epoch and not p(transmission)
    # so that we can see what happens when a host is trying to transmit a lot of packets
    for epoch in range(epochs):
        packs = math.floor(np.random.normal(avg_pkt_per_epoch))
        if packs == 0:
            packs = 1
        for pkts in range(packs):
            qjump_level = random.random()
            for prio in range(4):
                if qjump_level < traffic_dist[prio]:
                    break
            pkt_list.append(pack_gen(prio, epoch))
            
    # Main simulation loop. Iterations serve as network epochs. We are using packet.time_entered to serve as the
    # epoch it was sent at, and packet.time_delivered to serve as the epoch it left the queue. Retransmitted packets
    # just means that the host's queues[priority] was full and packet generation returned a ENOBUFS
    index_of_last_pkt_sent = 0
    for epoch in range(epochs):
        # Reallocate tokens
        tokens[0] = QJUMP_0
        tokens[1] = QJUMP_1
        tokens[2] = QJUMP_2
        tokens[3] = QJUMP_3
        
        # Iterating over all not-already-sent-packets until we reach one that's epoch
        # it is supposed to be sent at exceeds current epoch
        for i in range(index_of_last_pkt_sent, len(pkt_list)):
            pkt = pkt_list[i]
            if pkt.get_t_entered() > epoch:
                index_of_last_pkt_sent = i
                break
            
            # If this packets length exceeds the room left in its queue[priority]
            elif pkt.get_length() > tokens[pkt.get_priority()]:
                pkt.set_t_delivered(epoch)
                retrans.append(pkt)
            
            # Packet successfully is added to queue[priority]
            else:
                tokens[pkt.get_priority()] -= pkt.get_length()
                pkt.set_t_delivered(epoch)
                
                sent.append(pkt)
    
    print("Results from rate limit simulation:")
    print("Packets successfully sent: " + str(len(sent)))
    print("Packets that cuased ENOBUFS (retransmissions): " + str(len(retrans)))
    print("Ratio of retransmission/total packets: " + str(len(retrans) / len(pkt_list)))
    
    low_latency_total = 0
    for pkt in retrans:
        if pkt.get_priority() == 3:
            low_latency_total += 1

    print("Number of retransmitted packets from Qjump level 3 (lowest latency): " + str(low_latency_total))
    print("**********************************************\n\n")



def value_parser(string, type: Type):
    try:
        val = type(string)
    except ValueError:
        print("ERROR: {} is not a {}".format(string, type))
        return False
    return val
    


if __name__ == "__main__":
    args = sys.argv
    
    base_tdist = [6/12, 9/12, 11/12, 1.0]
    
    if len(args) == 1:
        # In a situation where we know the traffic distribution, we can get minimal interference
        rate_limit_sim(100000, base_tdist, 5)
        
        # In a situation where we do not know the traffic distribution, interference can be brutal
        rate_limit_sim(100000, [0.25, 0.5, 0.75, 1.0], 5)
        
        run(10000000, base_tdist, 0.00001)
    
    else:
        if args[1] == 'net_sim':
            if len(args) == 2:
                run(10000000, base_tdist, 0.00001)
            
            else:
                if args[2] == '-d':
                    epochs = value_parser(args[3], int)
                    p_tx = value_parser(args[4], float)
                    if epochs and p_tx:
                        run(epochs, base_tdist, p_tx)
                        
                else:
                    epochs = value_parser(args[2], int)
                    d1 = value_parser(args[3], float)
                    d2 = value_parser(args[4], float)
                    d3 = value_parser(args[5], float)
                    p_tx = value_parser(args[6], float)
                    
                    if epochs and p_tx and d1 and d2 and d3 and p_tx:
                        run(epochs, [d1,d2,d3,1.0], p_tx)
                        
        elif args[1] == 'rate_sim':
            if len(args) == 2:
                rate_limit_sim(100000, base_tdist, 5)
            
            else:
                if args[2] == '-d':
                    epochs = value_parser(args[3], int)
                    n_tx = value_parser(args[4], float)
                    if epochs and n_tx:
                        rate_limit_sim(epochs, base_tdist, n_tx)
                        
                else:
                    epochs = value_parser(args[2], int)
                    d1 = value_parser(args[3], float)
                    d2 = value_parser(args[4], float)
                    d3 = value_parser(args[5], float)
                    n_tx = value_parser(args[6], float)
                    
                    if epochs and d1 and d2 and d3 and n_tx:
                        rate_limit_sim(epochs, [d1,d2,d3,1.0], n_tx)
        else:
            print("ERROR: {} is an invalid simulation type. Please pass in either \'rate_sim\', \'net_sim\', or nothing as the second argument.".format(args[1]))