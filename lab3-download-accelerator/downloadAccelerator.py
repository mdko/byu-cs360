import requests
import argparse
import os
import threading
import time

''' Threaded downloader for a file '''
class DownloadAccelerator:
    def __init__(self):
        self.url = None
        self.n_threads = 1
        self.parse_arguments()

    def parse_arguments(self):
        ''' parse arguments, which include '-n' for number of threads and the url to download'''
        parser = argparse.ArgumentParser(prog='Threaded downloader', description='A script that downloads a file specified by a url in a threaded fashion', add_help=True)
        parser.add_argument('-n', '--threads', type=int, action='store', help='Specify the number of threads to use to download the file',default=1)
        parser.add_argument('url', type=str, action='store', help='Specify the url to download')
        args = parser.parse_args()
        self.url = args.url
        if not self.url.startswith('http://') or not args.url.startswith('https://'):
            self.url = 'http://' + self.url
        if self.url.endswith('/'):
            self.file_name = 'index.html'
        else:
            self.file_name = self.url.split('/')[-1]
        self.n_threads = args.threads

    def download(self):
        ''' download the files listed specified by the url '''
        # send a HEAD request to the web server specified in the URL
        # to determine the size of the object
        h = requests.head(self.url) 
        file_size = int(h.headers['content-length'])
        if file_size <= 0 :
            return

        section_size = file_size / self.n_threads 

        # download the object in parallel, using the specified number
        # of threads
        threads = []
        for i in range(0, self.n_threads):
            start_byte, end_byte = i * section_size, (i + 1) * section_size
            if i + 1 == self.n_threads:
                end_byte = file_size
            d = DownThread(self.url, start_byte, end_byte)
            threads.append(d)
        t1 = time.time()
        for t in threads:
            t.start()

        # store the individual parts and join them in one file after all
        # have been downloaded
        whole_file = []
        for t in threads:
            t.join()
            whole_file.append(t.content)
        t2 = time.time()
        seconds = t2 - t1

        f = open(self.file_name,'wb')
        f.write(''.join(whole_file))
        f.close()

        print self.url + ' ' + str(self.n_threads) + ' ' + str(file_size) + ' ' + str(seconds)

''' Use a thread to download the specific part of the file'''
class DownThread(threading.Thread):
    def __init__(self,url,start_byte,end_byte):
        self.url = url
        bytes_s = 'bytes=%s-%s' % (start_byte, end_byte)
        self.header = {'range':bytes_s}
        threading.Thread.__init__(self)

    def run(self):
        file_section = requests.get(self.url, headers=self.header, stream=True)
        if file_section.headers['content-range'] == None:
            raise Exception('No content-range header value found. Exiting...')
        self.content = file_section.content


if __name__ == "__main__":
    d = DownloadAccelerator()
    d.download()
