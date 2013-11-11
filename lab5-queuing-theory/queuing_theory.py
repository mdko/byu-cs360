import numpy as np
import math

def queuing_theory():
    # 2. M/M/N queuing
    N = 3

    arrival_rate = 40
    service_rate = 60
    ro = #2.0#np.double(arrival_rate)/service_rate #TODO check this
    print ro
    summation = 0
    for nc in range(N):
        summation += np.double(np.power(ro, nc))/np.double(math.factorial(nc))
        print 'nc %f, ro^nc %f, nc! %f, sum %f' % (nc, np.power(ro, nc), np.double(math.factorial(nc)), summation)
    summation += np.power(ro, N)/(math.factorial(N) * (1-(ro/N)))
    P0 = 1.0/summation
    print 'P0: %f' % (P0)

    roNplus1 = np.power(ro, N+1)
    Qbarleft = (P0 * roNplus1)/(math.factorial(N) * N)
    Qbarright = 1/np.power(1-(ro/N), 2)
    Qbar = Qbarleft * Qbarright

    print 'Average queue length: %f' % (Qbar)

def main():
    queuing_theory()


if __name__ == "__main__":
    main()