
'''
Another quick script for Dynamo-style staggered requests
Context: http://www.bailis.org/blog/doing-redundant-work-to-speed-up-distributed-queries/

For more info on distributions,
see http://www.bailis.org/papers/pbs-vldb2012.pdf

pbailis@cs.berkeley.edu
'''

from random import random, expovariate

TRIALS = 10000000
PCTILE = .999

'''
#LNKD-DISK model for reads
pareto_min = .235
pareto_shape = 10
exponential_lmbda = 1.66
pareto_to_exponential = .9122
'''

'''
#LNKD-DISK model for writes
pareto_min = 1.05
pareto_shape = 1.51
exponential_lmbda = .183
pareto_to_exponential = .38
'''

#YMMR model for reads
pareto_min = 1.5
pareto_shape = 3.8
exponential_lmbda = .0217
pareto_to_exponential = .018

def get_percentile(samples, pctile):
    samples.sort()
    return samples[int(len(samples)*pctile)]

def gen_pareto(min_value, shape):
    return min_value/pow(random(), 1/shape)

# one-way message delay; two of these make up a read
def get_latency_sample():
    if random() < pareto_to_exponential:
        return expovariate(exponential_lmbda)
    else:
        return gen_pareto(pareto_min, pareto_shape)

def simulate_read():
    return get_latency_sample()+get_latency_sample()

# this one is really simplistic due to the tails in the yammer
# latency distribution

for thresh in range(0, 30):
    extra = 0
    samples = []

    for trial in range(0, TRIALS):
        first = simulate_read()
        if first > thresh:
            extra += 1
            samples.append(min(first, simulate_read()))
        else:
            samples.append(first)

    print thresh, float(extra)/TRIALS, get_percentile(samples, PCTILE)
