import select
import socket
import sys
import time
import os

class Server:
    """ Web Server """
    def __init__(self,port,dbg):
        self.debug = dbg
        self.host = ""
        self.port = port
        self.open_socket()
        self.hosts = {}
        self.media = {}
        self.configure()
        self.clients = {}
        self.last_event = {}
        self.begin = time.time()
        self.cache = {}
        self.size = 1024

    def debugPrint(self, msg):
        if self.debug == True:
            print msg

    def configure(self):
        configfile = open('web.conf')
        for line in configfile:
            parts = line.split(' ')
            if parts[0] == '\n':
                continue
            elif parts[0] == 'host':
                name = parts[1]
                path = parts[2]
                self.hosts[name] = path.strip()
            elif parts[0] == 'media':
                ext = parts[1]
                mtype = parts[2]
                self.media[ext] = mtype.strip()
            elif parts[0] == 'parameter':
                timeout = parts[1]
                if timeout != 'timeout':
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
        while True:
            #debugPrint('Top of run loop in server.py')
            # check for sockets who have idled TODO fix this
            if (time.time() - self.begin) > self.timeout:
                self.debugPrint('Entering mark and sweep method')
                self.markAndSweepIdleSockets()
                self.begin = time.time()
            # poll sockets
            try:
                fds = self.poller.poll(timeout=1)
            except:
                return
            for (fd,event) in fds:
                self.last_event[fd] = time.time()
                self.debugPrint('Cycling through events')
                # handle errors
                if event & (select.POLLHUP | select.POLLERR):
                    self.handleError(fd)
                    continue
                # handle the server socket
                if fd == self.server.fileno():
                    self.handleServer()
                    self.debugPrint('Handling server socket')
                    continue
                # handle client socket
                self.debugPrint('Handling client socket')
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
                self.debugPrint('Data received: ' + data)
                self.cache[fd] += data
                blankline = data.find('\r\n\r\n')
                if blankline >= 0:  # end of message
                    self.debugPrint('Found blank line, end of message')
                    message = self.cache[fd]
                    message = message[:blankline]
                    # remove request (up to and including blankline), 
                    # leave anything after request in cache still
                    self.cache[fd] = message[blankline:]
                    processed = self.processHTTP(message, fd)
                    if processed: # no entity body present, done
                        self.cache[fd] = ""
                        self.debugPrint('Returned from processing the request and are done')
                        self.clients[fd].close()
                        del self.clients[fd]
                        break
            else:
                self.poller.unregister(fd)
                self.clients[fd].close()
                del self.clients[fd]


    def markAndSweepIdleSockets(self):
        print 'Marking and sweeping'
        curr_time = time.time()
        for socket in self.clients:
            last_time = self.last_event[socket.fileno()]
            if ((curr_time - last_time) > self.timeout):
                socket.close()
                del socket


    def processHTTP(self, request, fd):
        processed, response_code = True, ('200', 'OK')
        self.debugPrint('Entering processHTTP with this: ' + request)

        # read and parse the http request message
        lines = request.split('\r\n')
        request_line = lines[0]
        header_lines = lines[1:]
        headers = {}
        try:
            method, uri, version = request_line.split(' ')
        except ValueError:
            response_code = ('400', 'Bad Request')
        if method.strip() not in ('OPTIONS', 'GET', 'HEAD', 'POST', 'PUT', 'DELETE','TRACE', 'CONNECT'):
            response_code = ('400', 'Bad Request')
        if method.strip() != 'GET':
            response_code = ('501', 'Not implemented')

        if response_code[0] == '200':
            for header in header_lines:
                # implement General Headers (Date), Request Headers (Host),
                # Response Headers (Server), and Entity Headers(Content-Type, Content-Length, and Last-Modified)
                # however, it doesn't really matter if I split them up into their categories right now
                splits = header.split(':')
                field_name = splits[0] #TODO check this
                value = splits[1]
                # field_name, value = header.split(':')
                if field_name not in ('Host', 'Date', 'Server', 'Content-Type', 'Content-Length', 'Last-Modified'):
                    # ignore the others, according the lab spec
                    pass
                headers[field_name] = value.strip()
        
            # translate the uri to a file name
            #   need web server configuration to determine the document root
            filename = ''
            path = self.hosts['default']
            if uri == '/':
                uri = '/index.html'
            #elif uri[0] == '/': # absolute path, no prepending host?
            if not headers.has_key('Host'):
                debugPrint('No Host Header')
                response_code = ('400', 'Bad Request')
            else:
                host_value = headers['Host']
                if self.hosts.has_key(host_value): #response_code = ('400', 'Bad Request') # request has host this server can't handle
                    path = self.hosts[host_value]
            filename = path.strip() + uri
            self.debugPrint('Filename: ' + filename)   

        # generate and transmit the response
        #   error code or file or results of script
        #   must be a valid HTTP message with appropriate headers
        current_time = getTime(time.time())
        general_headers = ['Date: ' + current_time + '\r\n']
        response_headers = ['Server: cs360-mchristensen/1.1.11 (Ubuntu)\r\n']
        
        entity_headers = []
        content_size = 0    
        if response_code[0] == '200': # means we're good so far at least
            # determine whether the request is authorized
            #   check file permissions or other authorization procedure
            outfile = None
            try:
                outfile = open(filename)
            except IOError as (errno,strerror):
                if errno == 13:
                    # 403 Forbidden
                    response_code = ('403','Forbidden')
                    self.debugPrint('Cannot read the file')
                elif errno == 2:
                    # 404 Not Found
                    response_code = ('404','Not Found')
                else:
                    # 500 Internal Server Error
                    response_code = ('500','Internal Server Error')

            if (response_code[0] == '200'): # means file exists
                filetype = 'text/plain' #default for files with no extension
                if outfile:
                    if outfile.name.find('.'): #if it has an extension, supposedly
                        filesplit = outfile.name.split('.')
                        fileext = filesplit[-1]
                        if (self.media.has_key(fileext)): #if it's a recognized extension
                            filetype = self.media[fileext] 
                content_size = os.stat(outfile.name).st_size
                last_mod = os.stat(outfile.name).st_mtime
                last_mod_time = getTime(last_mod)
                entity_headers = ['Content-Type: ' + filetype + '\r\n', \
                                    'Last-Modified: ' + str(last_mod_time) + '\r\n']
        entity_headers.append('Content-Length: ' + str(content_size) + '\r\n')

        status_line = 'HTTP/1.1' + ' ' + response_code[0] + ' ' + response_code[1] + '\r\n'

        response = status_line 
        response += ''.join(general_headers)
        response += ''.join(response_headers)
        response += ''.join(entity_headers)
        if content_size > 0 and response_code[0] == '200':
            response += '\r\n'
            response += outfile.read()


        response_size = len(response)
        amount_sent = 0
        self.debugPrint('Response size: ' + str(response_size))
        # TODO fix this?
        #while amount_sent < response_size:
            #self.debugPrint('Haven\'t sent enough')
        amount_sent  += self.clients[fd].send(response)
            #self.debugPrint('Amount sent so far: ' + str(amount_sent))
            #response = response[amount_sent:]
        self.debugPrint('Sent:\n' + repr(response))
        
        # log request and any errors

        if headers.has_key('Content-Length'):
            content_length = headers['Content-Length']
            #processed = False
            processed = True
            # an entity body comes after the blank line that ended this request
            # however, the spec doesn't have us doing anything with the entity body of a request.
            # we would continue with the calling function to keep reading until we've reached this length
            # of bytes read
        return processed

def getTime(t):
    gmt = time.gmtime(t)
    format = '%a, %d %b %Y %H:%M:%S GMT'
    time_string = time.strftime(format,gmt)
    return time_string
        