import numpy as np
import math
import requests
import time
import optparse
import sys

import matplotlib
matplotlib.use('Agg')
from pylab import *

def queuing_theory():
    # 2. M/M/N queuing
    N = 3

    arrival_rate = 40
    service_rate = 20
    ro = np.double(arrival_rate)/service_rate
    print ro

    summation = 0
    for nc in range(N):
        summation += np.double(np.power(ro, nc))/np.double(math.factorial(nc)) + np.power(ro, N)/(math.factorial(N) * (1-(ro/N))) # TA said the summation goes around everything in the denomiator
        print 'nc %f, ro^nc %f, ro^N %f, summation %f' % (nc, np.power(ro, nc), np.power(ro, N), summation)
    P0 = 1.0/summation
    print 'Summation %f' % (summation)
    print 'P0 %f' % P0

    Qbarleft = (P0 * np.power(ro, N+1))/(math.factorial(N) * N)
    Qbarright = 1/np.power(1-(ro/N), 2)
    Qbar = Qbarleft * Qbarright

    print 'Average queue length: %f' % (Qbar)

    w = (ro+Qbar)/arrival_rate - 1.0/service_rate
    print 'Average wait time in queue: %f' % (w)    

    n = 5
    P5 = ((ro**n) * P0)/((N**(n-N))*math.factorial(N))
    print 'P5: %f' % (P5)

# Do this once for the lighttpd server, once for my server
def queuing_analysis():
    
    # The lighttpd server
    tests = 0
    elapsed = 0
    while tests < 100:
        start = time.time()
        r = requests.get('http://localhost:3000/file000.txt')
        end = time.time()
        if  r.status_code == 200:
            tests += 1
            elapsed += (end - start)
    avg_time_lighttpd = elapsed / tests # This is 1/mu
    print 'Average Lighttpd Time: %f' % (avg_time_lighttpd)

    # My server
    tests = 0
    elapsed = 0
    while tests < 100:
        start = time.time()
        r = requests.get('http://localhost:8080/file000.txt')
        end = time.time()
        if  r.status_code == 200:
            tests += 1
            elapsed += (end - start)
    avg_time_mine = elapsed / tests     # This is 1/mu
    print 'Average Time for my Server: %f' % (avg_time_mine)

    mu_l = 1.0/avg_time_lighttpd
    mu_m = 1.0/avg_time_mine

    # 1) Measure how long it takes to serve a file. Do this 100 times. Take the average. This is 1/mu.
    # 2) rho = lambda/mu
    # 3) average time = 1/(mu - lambda)
    # 4) For part two, plot the theoretical curve by varying lambda from 0 to mu. Since you know mu, you can obtain a series of values for X and Y and plot these using the example code I've give you.
    # 5) For part three, likewise vary lambda from 0 to mu. For each lambda, run an experiment with generator.py that will give you a bunch of data for your server. Plot a box plot at each value of lambda you tested, using the data for that experiment.
    

def main():
    #queuing_theory()
    queuing_analysis()

if __name__ == "__main__":
    main()