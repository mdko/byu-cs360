#include "server.h"
#include <sstream>
#include <vector>
#include <stdexcept>      // std::out_of_range
#include <climits>
#include <iterator>

Server::Server(int port, bool debug) {
    // setup variables
    port_ = port;
    buflen_ = 1024;
    buf_ = new char[buflen_+1];
    message_map_ = new map<string, vector<message> >();
    cache_ = "";
    debug_ = debug;

    // create and run the server
    create();
    serve();
}

Server::~Server() {
    delete buf_;
}

void
Server::create() {
    struct sockaddr_in server_addr;

    // setup socket address structure
    memset(&server_addr,0,sizeof(server_addr));
    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(port_);
    server_addr.sin_addr.s_addr = INADDR_ANY;

    // create socket
    server_ = socket(PF_INET,SOCK_STREAM,0);
    if (!server_) {
        perror("socket");
        exit(-1);
    }

    // set socket to immediately reuse port when the application closes
    int reuse = 1;
    if (setsockopt(server_, SOL_SOCKET, SO_REUSEADDR, &reuse, sizeof(reuse)) < 0) {
        perror("setsockopt");
        exit(-1);
    }

    // call bind to associate the socket with our local address and
    // port
    if (bind(server_,(const struct sockaddr *)&server_addr,sizeof(server_addr)) < 0) {
        perror("bind");
        exit(-1);
    }

      // convert the socket to listen for incoming connections
    if (listen(server_,SOMAXCONN) < 0) {
        perror("listen");
        exit(-1);
    }
}

void
Server::serve() {
    // setup client
    int client;
    struct sockaddr_in client_addr;
    socklen_t clientlen = sizeof(client_addr);

      // accept clients
    while ((client = accept(server_,(struct sockaddr *)&client_addr,&clientlen)) > 0) {

        handle(client);
        close(client);
    }
    
    close(server_);

}

string
Server::receive_message(int client, int length) {
    if (debug_) cout << "entering receive_message method" << endl;
    string message = cache_;
    int count = message.length();
    // read until we get a newline
    while (count < length) {
        if (debug_) cout << "current count " << count << endl;
        int nread = recv(client,buf_,1024,0);
        if (debug_) cout << "nread " << nread << endl;
        if (nread < 0) {
            if (errno == EINTR)
                // the socket call was interrupted -- try again
                continue;
            else
                // an error occurred, so break out
                return "";
        } else if (nread == 0) {
            // the socket is closed
            return "";
        }
        // be sure to use append in case we have binary data
        message.append(buf_,nread);
        if (debug_) cout << "message " << message << endl;
        count += nread;
    }
    if (debug_) cout << "returning from receive_message method" << endl;
    return message;
}

string
Server::store_message(int client, string name, string subject, string length) {
    if (debug_) cout << "entering store_message method" << endl;
    std::ostringstream response;
    message msg;
    msg.subject = subject;

    int length_i = strtol(length.c_str(), NULL, 10);
    if (length_i == 0L || length_i == LONG_MAX || length_i == LONG_MIN) {
        response << "error length "  << length << " is malformed\n";
    } else {
        msg.contents = receive_message(client, length_i);
        
        map<string, vector<message> >::iterator it = message_map_->find(name);
        if (it != message_map_->end()) { // key is already present
            if (debug_) cout << "found user " << name <<", inserting into map" << endl;
            it->second.push_back(msg);
        } else {
            if (debug_) cout << "could not find user " << name << " in map, creating new entry" << endl;
            vector<message> messages;
            messages.push_back(msg);
            message_map_->insert(std::make_pair(name, messages));
        }
        response << "OK\n";
    }
    if (debug_) cout << "returning from store_message method" << endl;
    return response.str();
}

string
Server::list_messages(string name) {
    if (debug_) cout << "entering list_messages method" << endl;
    map<string, vector<message> >::iterator it = message_map_->find(name);
    std::ostringstream response;
    if (it != message_map_->end()) {
        if (debug_) cout << "user " << name << " found, returning list of messages" << endl;
        vector<message> messages = it->second;
        int num_mesgs = messages.size();
        response << "list " << num_mesgs << "\n";
        for (int i=0; i<num_mesgs; i++) {
            response << i + 1 << " " << messages.at(i).subject << "\n";
        }
    } else {
        response << "error user " << name << " not found\n";
    }
    if (debug_) cout << "returning from list_messages method" << endl;
    return response.str();
}

string
Server::retrieve_message(string name, string index) {
    if (debug_) cout << "entering retrieve_message method" << endl;
    map<string, vector<message> >::iterator it = message_map_->find(name);
    std::ostringstream response;
    try {
        if (it != message_map_->end()) {
            vector<message> messages = it->second;
            int index_i = strtol(index.c_str(), NULL, 10);
            if (index_i == 0L || index_i == LONG_MAX || index_i == LONG_MIN) {
                response << "error index "  << index << " is malformed\n";
            } else {
                if (debug_) cout << "retrieving message " << index_i << " for " << name << endl;
                message msg = messages.at(index_i - 1);
                string subject = msg.subject;
                string contents = msg.contents;
                response << "message " << subject << " " << contents.size() << "\n" << contents;
            }
        } else {
            response << "error user " << name << " not found\n";
        }
    } catch (const std::out_of_range& oor) {
        response << "error no message at that index for " << name << "\n";
    }
    if (debug_) cout << "returning from retrieve_message method" << endl;
    return response.str();
}

string
Server::reset_messages() {
    if (debug_) cout << "entering reset_messages method" << endl;
    map<string, vector<message> >::iterator it = message_map_->begin();
    while (it != message_map_->end()) {
        it->second.clear();
        advance(it,1);
    }
    if (debug_) cout << "returning from reset_messages method" << endl;
    return "OK\n";
}

string
Server::handle_request(int client, string request) {
    vector<string> tokens;
    string response = "";
    
    if (request.empty()) {
        return response;
    }
    // Tokenize
    int pos = request.find_first_of(" ");
    while (pos != string::npos) {
        tokens.push_back(request.substr(0, pos));
        request.erase(0, pos+1);
        pos = request.find_first_of(" \t");
    }
    pos = request.find_first_of("\n");
    if (pos != string::npos) {
        request.erase(pos,1);
    }
    tokens.push_back(request);
    
    try {
        string command = tokens.at(0);
        if (command.compare("put") == 0) {
            if (debug_) cout << "put command detected in server" << endl;
            string name = tokens.at(1);
            string subject = tokens.at(2);
            string length = tokens.at(3);
            response = store_message(client, name, subject, length);
        } else if (command.compare("list") == 0) {
            if (debug_) cout << "list command detected in server" << endl;
            string name = tokens.at(1);
            response = list_messages(name);
        } else if (command.compare("get") == 0) {
            if (debug_) cout << "get command detected in server" << endl;
            string name = tokens.at(1);
            string index = tokens.at(2);
            response = retrieve_message(name, index);
        } else if (command.compare("reset") == 0) {
            if (debug_) cout << "reset command detected in server" << endl;
            response = reset_messages();
        } else {
            response = "error invalid command received in server";
        }
    } catch (const std::out_of_range& oor) {
        // not enough arguments provided
        response = "error handling request in server -- to few arguments";
    }
    return response;
}

void
Server::handle(int client) {
    // loop to handle all requests
    while (1) {
        // get a request
        string request = get_request(client);
        if (debug_) cout << "server received the following request from the client: \"" << request << "\"" << endl;
        // break if client is done or an error occurred
        if (request.empty())
            break;
        string response = handle_request(client, request);
        
        // send response
        if (debug_) cout << "server is sending the follwing response to the client: \"" << response << "\"" << endl;
        bool success = send_response(client,response);
        // break if an error occurred
        if (not success)
            break;
    }
}

string
Server::get_request(int client) {
    string request = "";
    // read until we get a newline
    while (request.find("\n") == string::npos) {
        int nread = recv(client,buf_,1024,0);
        if (nread < 0) {
            if (errno == EINTR)
                // the socket call was interrupted -- try again
                continue;
            else
                // an error occurred, so break out
                return "";
        } else if (nread == 0) {
            // the socket is closed
            return "";
        }
        // be sure to use append in case we have binary data
        request.append(buf_,nread);
    }
    int pos_mes = request.find_first_of("\n");
    cache_ += request.substr(pos_mes);
    request.erase(pos_mes);
    // a better server would cut off anything after the newline and
    // save it in a cache
    if (debug_) cout << "get_request: what came from client:\n" << request << endl;
    if (debug_) cout << "current cache: " << cache_ << endl;
    return request;
}

bool
Server::send_response(int client, string response) {
    cache_ = "";
    // prepare to send response
    const char* ptr = response.c_str();
    int nleft = response.length();
    int nwritten;
    // loop to be sure it is all sent
    while (nleft) {
        if ((nwritten = send(client, ptr, nleft, 0)) < 0) {
            if (errno == EINTR) {
                // the socket call was interrupted -- try again
                continue;
            } else {
                // an error occurred, so break out
                perror("write");
                return false;
            }
        } else if (nwritten == 0) {
            // the socket is closed
            return false;
        }
        nleft -= nwritten;
        ptr += nwritten;
    }
    return true;
}