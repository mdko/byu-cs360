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
        self.known_methods = ('OPTIONS', 'GET', 'HEAD', 'POST', 'PUT', 'DELETE','TRACE', 'CONNECT')
        self.supported_methods = ('GET')
        self.supported_header_names = ('Host', 'Date', 'Server', 'Content-Type', 'Content-Length', 'Last-Modified')
        self.last_event = {}
        self.begin = time.time()
        self.sweep_wait = 3
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
            curr_time = time.time()
            elapsed = curr_time - self.begin
            self.debugPrint('Elapsed time: ' + str(elapsed))
            if elapsed > self.sweep_wait:
                self.debugPrint('Entering mark and sweep method')
                self.markAndSweepIdleSockets()
                self.begin = time.time()
            # poll sockets
            try:
                fds = self.poller.poll(timeout=1)
            except:
                return
            for (fd,event) in fds:
                self.debugPrint('I\'ve been polled!')
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
            self.debugPrint('No more events to handle, going up to top of loop')

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
                    alldata = self.cache[fd]
                    message = alldata[:blankline]
                    # remove request (up to and including blankline), 
                    # leave anything after request in cache still
                    self.cache[fd] = alldata[blankline:]
                    processed = self.processHTTP(message, fd)
                    if processed: # no entity body present, done
                        self.cache[fd] = ""
                        #break
            else:
                self.poller.unregister(fd)
                self.clients[fd].close()
                del self.clients[fd]
                break




    def markAndSweepIdleSockets(self):
        curr_time = time.time()
        for socket in self.clients:
            if socket == self.server.fileno():
                continue

            last_time = self.last_event[socket]
            if ((curr_time - last_time) > self.timeout):
                socket.close()
                self.poller.unregister(socket)
                del socket

    # Can raise Exceptions, which are handled by caller in processHTTP
    def parseRequest(self, request_line):
        method, uri, version = request_line.split(' ', 2) # Should be space delimited, will throw error if more than 3 values to unpack
        response_code = ('200', 'OK')
        if method not in self.known_methods:
            response_code = ('400', 'Bad Request')
        elif method not in self.supported_methods:
            response_code = ('501', 'Not implemented')  
        return method, uri, version, response_code

    # Implements:
    #   General Headers (Date)
    #   Request Headers (Host)
    #   Response Headers (Server)
    #   Entity Headers(Content-Type, Content-Length, and Last-Modified)
    def parseHeaders(self, header_lines):
        headers = {}
        for header in header_lines:
            field_name, value = header.split(':', 1)
            field_name, value = field_name.strip(), value.strip() #TODO not sure if I should be accepting this type of malformed values (with extra ws)
            # Ignore the others, according the lab specification
            if field_name not in self.supported_header_names:
                pass
            headers[field_name] = value
        return headers


    # Use web server configuration to determine the document root
    def formFileName(self, host, uri):
        hostname = self.hosts['default']
        # Remove the attached port if necessary
        host = host.split(':')[0]
        if uri == '/':
            uri = 'index.html'
        if self.hosts.has_key(host): #If this host is identified in the configuration file, we won't use the 'default' value
            hostname = self.hosts[host]
        filename = hostname + '/' + uri
        return filename

    def fillEntityHeaders(self, ifile):
        filetype = 'text/plain' #Default for files with no extension
        entity_headers = {}
        try:
            name,sep,ext = ifile.name.rpartition('.')
            # If there was a way to separate the file name by the dot ('name' will be empty if it wasn't possible)
            if len(name) > 0:
                # Try and see if the extension given is recognized
                filetype = self.media[ext]
        except KeyError:
            pass
        content_size = os.stat(ifile.name).st_size
        last_mod = os.stat(ifile.name).st_mtime
        last_mod_time = self.getTime(last_mod)
        entity_headers['Content-Type'] = filetype
        entity_headers['Content-Length'] = content_size
        entity_headers['Last-Modified'] = last_mod_time
        return entity_headers

    def fillGeneralHeaders(self):
        current_time = self.getTime(time.time())
        general_headers = {'Date': current_time}
        return general_headers

    def fillResponseHeaders(self):
        response_headers = {'Server':'cs360-mchristensen/1.1.11 (Ubuntu)'}
        return response_headers

    def buildLines(self, headerDict):
        lines = ''
        for (key, value) in headerDict.items():
            lines += key + ': ' + str(value) + '\r\n'
        return lines

    def getTime(self, t):
        gmt = time.gmtime(t)
        format = '%a, %d %b %Y %H:%M:%S GMT'
        time_string = time.strftime(format,gmt)
        return time_string  

    # Read and respond to the http request message
    def processHTTP(self, request, fd):
        self.debugPrint('Incoming request:\n' + request)

        processed, response_code = True, ('200', 'OK')
        lines = request.split('\r\n')

        ####### Parse the request and build up part of the response #######
        general_headers = {}
        response_headers = {}
        entity_headers = {}
        entity_body = ''
        try:
            request_line = lines[0].strip()
            method, uri, version, response_code = self.parseRequest(request_line)

            # Header Line (We assume there must be one header fields, at least a 'Host' header, so it is an error if we can't slice like this)
            header_lines = lines[1:]
            headers = self.parseHeaders(header_lines) # Normally we'd do stuff with these headers, but we only need the 'Host' value for the basic functionality
            
            # Translate the uri to a file name
            host = headers['Host']
            filename = self.formFileName(host, uri)
            self.debugPrint('Desired file: ' + filename)

            # Try to access the file requested
            outfile = open(filename)
            entity_headers = self.fillEntityHeaders(outfile)
            entity_body = outfile.read()

        except (ValueError, IndexError, KeyError) as error:
            self.debugPrint('Exception: %s' % error)
            response_code = ('400', 'Bad Request')
        except IOError as (errno, strerror):
            entity_headers['Content-Length'] = 0
            #entity_headers['Content-Type'] = 'text/plain' # This shouldn't be required if there is no entity-body included
            if errno == 13:
                response_code = ('403','Forbidden')
            elif errno == 2:
                response_code = ('404','Not Found')
            else:
                response_code = ('500','Internal Server Error')
        
        ####### Generate the response #######
        status_line = 'HTTP/1.1' + ' ' + response_code[0] + ' ' + response_code[1] + '\r\n'
        general_headers = self.fillGeneralHeaders()
        response_headers = self.fillResponseHeaders()

        response = status_line 
        response += self.buildLines(general_headers)
        response += self.buildLines(response_headers)
        response += self.buildLines(entity_headers)
        response += '\r\n'
        response += entity_body

        ###### Send the response #######
        self.debugPrint('Outgoing response:\n' + response)

        response_size = len(response)
        amount_sent = 0
        while amount_sent < response_size:
            amount_sent  += self.clients[fd].send(response)
            response = response[amount_sent:]


        # if headers.has_key('Content-Length'):
        #     content_length = headers['Content-Length']
        #     #processed = False
        #     processed = True
        #     # an entity body comes after the blank line that ended this request
        #     # however, the spec doesn't have us doing anything with the entity body of a request.
        #     # we would continue with the calling function to keep reading until we've reached this length
        #     # of bytes read
        return processed
        