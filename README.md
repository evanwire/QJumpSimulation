#  A simulation of QJump

### How to run
Clone the repo and enter the project's directory. For sake of dependency organizaiton, create a virtual environment
```
$ python -m venv env
$ source env/bin/activate
```

Install the requirements
```
$ pip install -r requirements.txt
```

Run the project
```
$ python sim.py sim_type flag epoch d1 d2 d3 tx
```

Examples:
```
$ python sim.py
$ python sim.py rate_sim 100000 0.25 0.5 0.75 5
$ python sim.py net_sim -d 10000000 0.0001
```

**Command line args:**
* sim_type: Specifies which simulation to run
    * 'rate_sim' runs the rate simulator
    * 'net_sim' runs the full network simulator
* flag: Specifies whether you intend to use the provided traffic distribution
    * '-d' implies you want the provided traffic distribution. If this option is chosen, you do not need to pass in d1 d2 or d3
* epoch: number of network epochs to run
* d1, d2, d3: the distribution of traffic for different traffic priorities. Values are floats that can range from 0-1, not inclusive. Will create a distribution [d1, d2, d3, 1.0]
* tx: if running network simulator, a float ranging from 0-1 that implies the percentage chance a host will generate packets in any given epoch. If running rate simulator, an integer greater than 0 that determines the average number of packets generated each epoch


### About this project
This was done as an assignment for CS740. I attempted to mirror the rate limiter
found in the QJump paper (https://www.usenix.org/system/files/conference/nsdi15/nsdi15-paper-grosvenor.pdf)
and study mainly the throughput of varrying packet priorities and the amount of ENOBUFS for differing
traffic patterns.

QJump is a paper that proposed a QoS style packet prioritization system that allows packets of high priority
to "jump the queue." This is done by having each host maintain a subqueue for each priority level. When a packet
enters the host egress queue, it is sent through the rate limiter, which determines which queue to add it to. The catch
is that there is a throughput-latency tradeoff: high priority traffic will send faster, but it sends less packets per unit time. This
allows developers to, based on their priorities and their application's traffic distribution, select a priority level
that optimizes their workflow. For instance, latency sensitive operations like memcache will transmit less packets but at a higher rate,
while Hadoop MapReduce packets can be sent in bulk, but at a slower rate. 

This implementation has two simulations, the network simulation (net sim) and rate limiter simulation (rate sim). Net sim uses threads to
control the hosts' and switches' egress queues, while a thread pool is utilized to generate packets and send them to the hosts' rate limiters.
This implementation is not optimal because the queues used are threadsafe, which is achieved by blocking put() and get() calls while
another thread is accessing the data structure. This causes drastically inaccurate measurements of packet delivery times, however it still
allows us to see the relative throughput for different packet priorities. We can see that, generally, the low priority applications
are able to send way more packets per unit time than the latency sensitive ones. Adjusting the traffic distribution provides insight as to what the
optimal QJump parameter values might be for a given distribution.

Upon completing this simulation, I became curious on how the rate limiter would work if we provided parameters that are not representative
of the expected traffic patterns. Rate sim allows us to narrow in on the operation of the rate simulator at one host. We can see that,
if the QJump parameters are set inaccurately, we experience a lot of interference for high priority workloads. Data center interference primarily
stems from shared switch queues, where a switch's queue is full and thus a host is unable to route packets through that switch. In this simulation, we
can pass in the average number of packets per epoch, and any value greater than 1 will mirror the effects of severe network oversubscription. This is because the rate limiter in an actual QJump deployment allows hosts to only send one packet per network epoch.

One thing I would like to do in the future is implement QJump using a network simulator, such as mininet. This would reduce the impact that the threadsafe queues have on packet travel times. The only reason I did not do that originally is because, to do so, I would have had to rewrite QJump as a linux traffic control module. Having no prior experience with TC, I assumed I would not be able to complete that by the assignment deadline. Regardless, I feel that this implementation provides a glimpse into how the rate limiter works, and how important parameter tuning is for QJump. It also indicates that, if a data center's traffic is very unpredictable, perhaps QJump isn't the best way to limit interference.
