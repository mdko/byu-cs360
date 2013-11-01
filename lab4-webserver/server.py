import select
import socket
import sys
import time
import os
filename = '/etc/motd'

class Server:
    """ Web Server """
    def __init__(self,port):
        self.host = ""
        self.port = port
        self.open_socket()
        self.hosts = {}
        self.media = {}
        self.configure()
        self.clients = {}
        self.cache = {}
        self.size = 1024

    def configure(self):
        configfile = open('web.conf')
        for line in configfile:
            parts = line.split(' ')
            if parts[0] == 'host':
                name = parts[1]
                path = parts[2]
                self.hosts[name] = path
            elif parts[0] == 'media':
                ext = parts[1]
                mtype = parts[2]
                self.media[ext] = mtype
            elif parts[0] == 'parameter':
                timeout = parts[1]
                if timeout != 'timeout'
                    print 'Unknown parameter in web.conf file'
                    sys.exit(1)
                self.timeout = parts[2]
            else:
                print 'Could not parse web.conf file'
                sys.exit(1)

    def open_socket(self):
        """ Setup the socket for incoming clients """
        try:
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR,1)
            self.server.bind((self.host,self.port))
            self.server.listen(5)
        except socket.error, (value,message):
            if self.server:
                self.server.close()
            print "Could not open socket: " + message
            sys.exit(1)

    def run(self):
        """ Use poll() to handle each incoming client."""
        self.poller = select.epoll()
        self.pollmask = select.EPOLLIN | select.EPOLLHUP | select.EPOLLERR
        self.poller.register(self.server,self.pollmask)
        print self.server.fileno()
        while True:
            # poll sockets
            try:
                fds = self.poller.poll(timeout=1)
            except:
                return
            for (fd,event) in fds:
                # handle errors
                if event & (select.POLLHUP | select.POLLERR):
                    self.handleError(fd)
                    continue
                # handle the server socket
                if fd == self.server.fileno():
                    self.handleServer()
                    continue
                # handle client socket
                result = self.handleClient(fd)

    def handleError(self,fd):
        self.poller.unregister(fd)
        if fd == self.server.fileno():
            # recreate server socket
            self.server.close()
            self.open_socket()
            self.poller.register(self.server,self.pollmask)
        else:
            # close the socket
            self.clients[fd].close()
            del self.clients[fd]

    def handleServer(self):
        (client,address) = self.server.accept()
        self.clients[client.fileno()] = client
        self.cache[client.fileno()] = ""
        self.poller.register(client.fileno(),self.pollmask)

    def handleClient(self,fd):
        while True:
            data = self.clients[fd].recv(self.size)
            if data == socket.errno.EAGAIN or data == socket.errno.EWOULDBLOCK:
                break
            if data:
                self.cache[fd] += data
                blankline = data.find('\r\n\r\n')
                if blankline >= 0:  # end of message
                    message = self.cache[fd]
                    message = message[:blankline]
                    # remove request (up to and including blankline), 
                    # leave anything after request in cache still
                    self.cache[fd] = message[blankline:]
                    processed = self.process_http(message, fd)
                    if processed: # no entity body present, done
                        break
            else:
                self.poller.unregister(fd)
                self.clients[fd].close()
                del self.clients[fd]

    def process_http(self, message, fd):
        processed, response_code = True, ('200', 'OK')

        # read and parse the http request message
        lines = message.split('\r\n')
        request_line = lines[0]
        header_lines = lines[1:]
        headers = {}
        method, uri, version = request_line.split(' ')
        for header in header_lines:
            # implement General Headers (Date), Request Headers (Host),
            # Response Headers (Server), and Entity Headers(Content-Type, Content-Length, and Last-Modified)
            # however, it doesn't really matter if I split them up into their categories right now
            field_name, value = header.split(':')
            if field_name not in ('Host', 'Date', 'Server', 'Content-Type', 'Content-Length', 'Last-Modified'):
                # ignore the others, according the lab spec
                pass
            headers[field_name] = value.strip()
        
        # translate the uri to a file name
        #   need web server configuration to determine the document root
        filename = ''
        if url == '/':
            filename = '/index.html'
        else:
            host_value = headers['Host']
            path = self.hosts[host_value]
            filename = path + '/' + uri
        
        # determine whether the request is authorized
        #   check file permissions or other authorization procedure
        outfile = None
        try:
            outfile = open(filename)
        except IOError as (errno,strerror):
            if errno == 13:
                # 403 Forbidden
                response_code = ('403','Forbidden')
            elif errno == 2:
                # 404 Not Found
                response_code = ('404','Not Found')
            else:
                # 500 Internal Server Error
                response_code = ('500','Internal Server Error')

        # generate and transmit the response
        #   error code or file or results of script
        #   must be a valid HTTP message with appropriate headers
        status_line = 'HTTP/1.1' + ' ' + response_code[0] + ' ' + response_code[1]
        t = time.time()
        current_time = get_time(t)
        general_headers = ['Date:' + current_time]
        response_headers = ['Server:cs360-mchristensen/1.1.11 (Ubuntu)']
        
        filetype = 'text/plain' #default for files with no extension
        if outFile:
            if outfile.name.find('.'): #if it has an extension, supposedly
                filesplit = outfile.split('.')
                fileext = filesplit[-1]
                if (self.media.has_key(fileext)): #if it's a recognized extension
                    filetype = self.media[fileext] 
        content_size = os.stat(outFile).st_size
        last_mod = os.stat(outFile).st_mtime
        last_mod_time = get_time(last_mod)
        entity_headers = ['Content-Type:' + filetype, \
                            'Content-Length:' + content_size, \
                            'Last-Modified:' + last_mod_time]
        
        # log request and any errors

        if headers.has_key('Content-Length'):
            content_length = headers['Content-Length']
            #processed = False
            processed = True
            # an entity body comes after the blank line that ended this request
            # however, the spec doesn't have us doing anything with the entity body of a request.
            # we would continue with the calling function to keep reading until we've reached this length
            # of bytes read

        if data:
            self.clients[fd].send(data)

def get_time(t):
    gmt = time.gmttime(t)
    format = '%a, %d %b %Y %H:%M:%S GMT'
    time_string = time.strftime(format,gmt)
    return time_string
        