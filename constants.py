# 10Gb links were used in the Qjump experiment
BANDWIDTH = 10000000000
# timeout = 0
# network_epoch = (2 * 10) * (256/BANDWIDTH) #10 is n hosts

# Qjump configurations, naming conventions left unchanged
P = 256
N = 12
R = BANDWIDTH
EPSILON = 0.000001

NETWORK_EPOCH = (2 * N * (P / R)) + EPSILON

# Using only 4 Qjump levels, can add more if results aren't clear
QJUMP_0 = 12 * P
QJUMP_1 = 6 * P
QJUMP_2 = 3 * P
QJUMP_3 = 1 * P

