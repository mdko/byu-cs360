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
        self.supported_methods = ('GET', 'HEAD')
        self.supported_header_names = ('Host', 'Date', 'Server', 'Content-Type', 'Content-Length', 'Last-Modified', 'Range')
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
            #self.debugPrint('Elapsed time: ' + str(elapsed))
            if elapsed > self.sweep_wait:
                #self.debugPrint('Entering mark and sweep method')
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
            #self.debugPrint('No more events to handle, going up to top of loop')

    def handleError(self,fd):
        self.poller.unregister(fd)
        if fd == self.server.fileno():
            # recreate server socket
            self.server.close()
            self.open_socket()
            self.poller.register(self.server,self.pollmask)
            self.server.setblocking(0)
        else:
            # close the socket
            self.clients[fd].close()
            del self.clients[fd]

    def handleServer(self):
        (client,address) = self.server.accept()
        self.clients[client.fileno()] = client
        self.cache[client.fileno()] = ""
        self.poller.register(client.fileno(),self.pollmask)
        client.setblocking(0)

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
                    self.cache[fd] = alldata[blankline:]
                    processed, response = self.processHTTP(message, fd)
                    if processed:
                        response_size = len(response)
                        total_amount_sent = 0
                        while total_amount_sent < response_size:
                            try:
                                amount_sent  = self.clients[fd].send(response[total_amount_sent:])
                            except:
                                continue
                            total_amount_sent += amount_sent
                        self.cache[fd] = ""
                        break
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

            try:
                last_time = self.last_event[socket]
                if ((curr_time - last_time) > self.timeout):
                    socket.close()
                    self.poller.unregister(socket)
                    del socket
            except:
                continue

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
        docroot = self.hosts['default']
        # Remove the attached port if necessary
        host = host.split(':')[0]
        if uri == '/':
            uri = 'index.html'
        if self.hosts.has_key(host): #If this host is identified in the configuration file, we won't use the 'default' value
            docroot = self.hosts[host]
        if uri.startswith('/'):
            uri = uri[1:]
        filename = docroot + '/' + uri
        return filename

    def fillEntity(self, method, headers, ifile):
        filetype = 'text/plain' #Default for files with no extension
        entity_headers = {}
        last_mod = os.stat(ifile.name).st_mtime
        last_mod_time = self.getTime(last_mod)
        entity_body = ''
        response_code = ('200', 'OK')

        try:
            name,sep,ext = ifile.name.rpartition('.')
            # If there was a way to separate the file name by the dot ('name' will be empty if it wasn't possible)
            if len(name) > 0:
                # Try and see if the extension given is recognized
                filetype = self.media[ext]
        except KeyError:
            pass

        if method == 'GET':
            self.debugPrint('Found a HEAD request')
            if headers.has_key('Range'):
                filerange = headers['Range']
                filerange = filerange.split('=')[1]
                filerange = filerange.split('-')
                start, end = int(filerange[0]), int(filerange[1])
                ifile.seek(start)
                entity_body = ifile.read((end-start)+1)
                response_code = ('206', 'Partial Content')
            else:
                entity_body = ifile.read()
        elif method == 'HEAD':
            self.debugPrint('Found a HEAD request')
            

        #content_size = os.stat(ifile.name).st_size
        entity_headers['Content-Type'] = filetype
        entity_headers['Content-Length'] = len(entity_body)
        entity_headers['Last-Modified'] = last_mod_time

        return entity_headers, entity_body, response_code

    def fillGeneralHeaders(self):
        current_time = self.getTime(time.time())
        general_headers = {'Date': current_time}
        return general_headers

    def fillResponseHeaders(self):
        response_headers = {'Server':'cs360-mchristensen/1.1.11 (Ubuntu)'}
        return response_headers

    def makeErrorEntityBody(self, response_code):
        if response_code[0] == '400':
            return 'Bad request sent to the server.'
        elif response_code[0] == '403':
            return 'Cannot access the requested resource due to permissions'
        elif response_code[0] == '404':
            return 'Requested resource cannot be found'
        elif response_code[0] == '500':
            return 'The server has experience an internal error'
        elif response_code[0] == '501':
            return 'Requested method is not implemented by this server'
        else:
            return 'No error'


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
            if response_code[0] != '200':
                entity_body = self.makeErrorEntityBody(response_code)
                entity_headers['Content-Type'] = 'text/plain'
                entity_headers['Content-Length'] = len(entity_body)         
            else:
                # Header Line (We assume there must be one header fields, at least a 'Host' header, so it is an error if we can't slice like this)
                header_lines = lines[1:]
                headers = self.parseHeaders(header_lines) # Normally we'd do stuff with these headers, but we only need the 'Host' value for the basic functionality
                
                # Translate the uri to a file name
                host = headers['Host']
                filename = self.formFileName(host, uri)
                self.debugPrint('Desired file: ' + filename)

                # Try to access the file requested
                outfile = open(filename)
                entity_headers, entity_body, response_code = self.fillEntity(method, headers, outfile)

        except (ValueError, IndexError, KeyError) as error:
            self.debugPrint('Exception: %s' % error)
            response_code = ('400', 'Bad Request')
            entity_body = self.makeErrorEntityBody(response_code)
            entity_headers['Content-Type'] = 'text/plain'
            entity_headers['Content-Length'] = len(entity_body) 
        except IOError as (errno, strerror):
            if errno == 13:
                response_code = ('403','Forbidden')
            elif errno == 2:
                response_code = ('404','Not Found')
            else:
                response_code = ('500','Internal Server Error')
            entity_body = self.makeErrorEntityBody(response_code)
            entity_headers['Content-Type'] = 'text/plain'
            entity_headers['Content-Length'] = len(entity_body)

        
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

        ###### Make response ready for sending by calling method #######
        #self.debugPrint('Outgoing response:\n' + response)

        return processed, response