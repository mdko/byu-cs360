import numpy as np
import math
import requests
import time
import optparse
import sys
import os
import matplotlib
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

    mu_l = 1.0/avg_time_lighttpd    # Avg service rate
    mu_m = 1.0/avg_time_mine        # Avg service rate

    print 'Mu lighttpd server: %f' % (mu_l)
    print 'Mu my server: %f' % (mu_m) 

    # Notes from Dr. Zappala
    # 1) Measure how long it takes to serve a file. Do this 100 times. Take the average. This is 1/mu.
    # 2) rho = lambda/mu
    # 3) average time = 1/(mu - lambda)
    # 4) For part two, plot the theoretical curve by varying lambda from 0 to mu. Since you know mu, you can 
    #    obtain a series of values for X and Y and plot these using the example code I've give you.
    # 5) For part three, likewise vary lambda from 0 to mu. For each lambda, run an experiment with generator.py 
    #    that will give you a bunch of data for your server. Plot a box plot at each value of lambda you tested, 
    #    using the data for that experiment.
    # """ Create a line graph of an equation. """
    #
    #

    clf()
    lambdaa = np.arange(0,mu_l,1.0)
    plot(lambdaa/mu_l,1/(mu_l - lambdaa))
    title('Theoretical Average Response Time vs Utilization for the Lighttpd Server\n')
    xlabel('Utilization')
    ylabel('Average Response Time')
    savefig('Theoretical_avg_resp_vs_utilization_lighttpd.png')

    clf()
    lambdaa = np.arange(0,mu_m,1.0)
    plot(lambdaa/mu_m,1/(mu_m - lambdaa))
    title('Theoretical Average Response Time vs Utilization for the Our Server\n')
    xlabel('Utilization')
    ylabel('Average Response Time')
    savefig('Theoretical_avg_resp_vs_utilization_ourserver.png')

    return mu_l, mu_m

def performance_evaluation(mu_l, mu_m):
    # Use the web-[server]-[load].txt files to create a box plot of the response time as a function of utilization
    # On the same graph, plot the theoretical line from Part 2
    # You convert your mu into a certain number of clients per second. Then you vary from 10% to 95% or 98%.

    utilization = [0.01, 0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.98, 0.99]
    loadsm = [] # could also do loadsm = map(lambda x: x * mu_m, lambdasperc)
    loadsl = [] # could also do loadsl = map(lambda x: x * mu_l, lambdasperc)

    for percent in utilization:
        load = percent * mu_m # lambda
        loadsm.append(load)
        os.system('python ../lab4-webserver/tests/generator.py --port 8080 -l %d -d 30 >> ./part3/ours/web-ours-%d.txt' % (load, load))
    for percent in utilization:
        load = percent * mu_l
        loadsl.append(load)
        os.system('python ../lab4-webserver/tests/generator.py --port 3000 -l %d -d 30 >> ./part3/lighttpd/web-lighttpd-%d.txt' % (load, load)) 

    #	loadsm = [3, 16, 32, 80, 161, 241, 290, 306, 315, 319] # For debugging, not having to run many files again
    # Our Web Server
    avg_ours_times = {}
    all_our_times = {}  # map from load number to a list of times
    for l in loadsm:
        f = open('./part3/ours/web-ours-%d.txt' % (l))
        total_time = 0
        total_lines = 0
        all_times = []
        for line in f:
            total_lines += 1
            time = float(line.split()[5])
            all_times.append(time)
            total_time += time
        all_our_times[l] = all_times
    
        avg_ours_times[l] = total_time/total_lines
        print 'Average for ours load %d: %f' % (l, avg_ours_times[l])	# unneeded, but for my information

    """ Create a box plot of the download time"""
    clf()
    boxplot(all_our_times.values(),positions=utilization,widths=0.01)
    xlim(0,1)
    # TODO graph theoretical line with this plot of boxplots
    # ylim(0,1)
    # plot(np.arange(0,mu_m,1.0)/mu_m,1/(mu_m-np.arange(0,mu_m,1.0)))
    # xlabel('Utilization')
    # ylabel('Average Response Time')
    savefig('download-boxplot%d.png' % (l))

    # TODO Lighttpd Web Server
    # avg_lighttpd_times = {}
    # for l in loadsl:
    #     f = open('./part3/lighttpd/web-lighttpd-%d.txt' % (l))
    #     total_time = 0
    #     total_lines = 0
    #     for line in f:
    #         total_lines += 1
    #         total_time += float(line.split()[5])
    #     avg_lighttpd_times[l] = total_time/total_lines
    #     print 'Average for lighttpd load %d: %f' % (l, avg_lighttpd_times[l])
    

def main():
    #queuing_theory()
    mu_l, mu_m = queuing_analysis()
    performance_evaluation(mu_l, mu_m)

if __name__ == "__main__":
    main()