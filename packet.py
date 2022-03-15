

class Packet():
    
    def __init__(self, priority, length, time_curr, src=-1, dst=-1):
        self.priority = priority
        self.length = length
        self.timeEnteredQueue = time_curr
        self.timeDelivered = -1.0
        self.src = src
        self.dst = dst
    
    # I realized way after I wrote these getters/setters that python just makes object data public
        
    def get_priority(self):
        return self.priority
    
    def get_length(self):
        return self.length
    
    def get_t_entered(self):
        return self.timeEnteredQueue
    
    def get_t_left(self):
        return self.timeLeftQueue
    
    def get_src(self):
        return self.src
    
    def get_dst(self):
        return self.dst
    
    def set_t_delivered(self, time: float):
        self.timeDelivered = time
    
    def toString(self):
        return 'Priority: ' + str(self.priority) +  ' Time Sent: ' + str(self.timeEnteredQueue) + ' Time Delivered: ' + str(self.timeDelivered) + ' Travel Time: ' + str(self.timeDelivered - self.timeEnteredQueue)
