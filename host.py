import numpy as np
from packet import Packet
from constants import *
import time
import random
import queue

class Host():    
    def __init__(self, group):
        self.timeout = 0
        self.tokens = [
            QJUMP_0,
            QJUMP_1,
            QJUMP_2,
            QJUMP_3
        ]
        self.queue = queue.Queue()
        self.group = group
                            
                
        
    def rate_limiter(self, pkt: Packet, epoch: int):
        # If we are in a new epoch, reallocate room in the buffers
        if epoch > self.timeout:
            self.timeout += 1
            self.tokens[0] = QJUMP_0
            self.tokens[1] = QJUMP_1
            self.tokens[2] = QJUMP_2
            self.tokens[3] = QJUMP_3
        
        # If not enough room left, return ENOBUFS
        if pkt.get_length() > self.tokens[pkt.get_priority()]:
            return 0
        
        # Add packet to queues[priority], return SENT
        self.tokens[pkt.get_priority()] -= pkt.get_length()
        self.queue.put(pkt)
        return 1
        
            