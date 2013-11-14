import httplib
import optparse
import sys
import time

# Run an experiment to download a URL
class Experiment:
    def __init__(self,host,url,repeat):
        """ Set host, url, and number of repetitions. """
        self.host = host
        self.url = url
        self.headers = {"User-Agent":"Daniel Zappala"}
        self.repeat = repeat

    def download(self):
        """ Download the URL a certain number of times. """
        print "# Time (seconds) Download Time (seconds) Size (bytes)"
        for i in range(0,self.repeat):
            # start the clock
            t1 = time.time()

            # send HTTP request
            conn = httplib.HTTPConnection(self.host)
            conn.request("GET",self.url,"",self.headers)
        
            # get HTTP response
            r = conn.getresponse()

            # read the data
            data = r.read()

            # end the clock
            t2 = time.time()
            diff = t2 - t1

            # parse response
            if r.status == 200:
                size = len(data)
                print "%f %f %d" % (t1,diff,size)
            else:
                print "# ",r.status, r.reason

        # close connection
        conn.close()


def parse_options():
        # parse options
        parser = optparse.OptionParser(usage = "%prog [options]",
                                       version = "%prog 0.1")

        parser.add_option("-s","--server",type="string",dest="server",
                          default=None,
                          help="server")
        parser.add_option("-u","--url",type="string",dest="url",
                          default="/",
                          help="url")
        parser.add_option("-r","--repetitions",type="int",dest="repetitions",
                          default=10,
                          help="repetitions")

        (options,args) = parser.parse_args()
        return (options,args)


if __name__ == '__main__':
    (options,args) = parse_options()
    if options.server == None:
        print "experiment.py -s [server] [-u url] [-r repetitions]"
        sys.exit()
    e = Experiment(options.server,options.url,options.repetitions)
    e.download()
