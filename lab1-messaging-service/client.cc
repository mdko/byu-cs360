#include "client.h"
#include <sstream>
#include <vector>

#define DEBUG true

Client::Client(string host, int port) {
    // setup variables
    host_ = host;
    port_ = port;
    buflen_ = 1024;
    buf_ = new char[buflen_+1];

    // connect to the server and run echo program
    create();
    prompt();
}

Client::~Client() {
}

void
Client::create() {
    struct sockaddr_in server_addr;

    // use DNS to get IP address
    struct hostent *hostEntry;
    hostEntry = gethostbyname(host_.c_str());
    if (!hostEntry) {
        cout << "No such host name: " << host_ << endl;
        exit(-1);
    }

    // setup socket address structure
    memset(&server_addr,0,sizeof(server_addr));
    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(port_);
    memcpy(&server_addr.sin_addr, hostEntry->h_addr_list[0], hostEntry->h_length);

    // create socket
    server_ = socket(PF_INET,SOCK_STREAM,0);
    if (!server_) {
        perror("socket");
        exit(-1);
    }

    // connect to server
    if (connect(server_,(const struct sockaddr *)&server_addr,sizeof(server_addr)) < 0) {
        perror("connect");
        exit(-1);
    }
}

void
Client::print_usage(string original_string) {
    cout << "Invalid command/format: \"" << original_string << "\"" << endl;
    cout << "Usage: [command]" << endl;
    cout << "where [command] is one of the following:" << endl;
    cout << "\tsend [user] [subject]" << endl;
    cout << "\tlist [user]" << endl;
    cout << "\tread [user] [index]" << endl;
    cout << "\tquit" << endl;
}

string
Client::handle_input() {
    string line, command, original_line;
    string request = "";
    vector<string> tokens;
    
    // Tokenize
    getline(cin, line);
    original_line = string(line);
    if (line.empty()) {
        return request;
    }
    int pos = line.find_first_of(" \t");
    while (pos != string::npos) {
        tokens.push_back(line.substr(0, pos));
        line.erase(0, pos+1);
        pos = line.find_first_of(" \t");
    }
    tokens.push_back(line);
    
    command = tokens.at(0);
    if (command.compare("send") == 0) {
        string user = tokens.at(1);
        string subject = tokens.at(2);
        request = send_command(user, subject);
    } else if (command.compare("list") == 0) {
        string user = tokens.at(1);
        request = list_command(user);
    } else if (command.compare("read") == 0) {
        string user = tokens.at(1);
        string index = tokens.at(2);
        request = read_command(user, index);
    } else if (command.compare("reset") == 0) {
        request = "reset\n";
    } else if (command.compare("quit") == 0) {
        exit(0); 
    } else {
        print_usage(original_line);
    }
    return request;
}

string
Client::send_command(string user, string subject) {
    cout << "- Type your message. End with a blank line -" << endl;

    string message, curr_line;
    getline(cin, curr_line);
    while (!curr_line.empty()) {
        message += curr_line + "\n";
        getline(cin, curr_line);
    } 

    std::ostringstream ostr;
    ostr << "put " << user << " " << subject << " " << message.length() <<  "\n" << message;   
    return ostr.str();       
}

string
Client::list_command(string user) {
    std::ostringstream ostr;
    ostr << "list " << user << "\n";
    return ostr.str();
}

string
Client::read_command(string user, string index) {
    std::ostringstream ostr;
    ostr << "get " << user << " " << index << "\n";
    return ostr.str();
}

void
Client::prompt() {
    while (1) {
        cout << "% ";
        string request = handle_input();
        if (!request.empty()) {
            // send request
            if (DEBUG) cout << "client is sending the following to the server: " << request << endl;
            bool success = send_request(request);
            // break if an error occurred
            if (not success) {
                break;
            }
            // get a response
            success = get_response();
            // break if an error occurred
            if (not success) {
                break;
            }
        }
    }
    close(server_);
}

bool
Client::send_request(string request) {
    // prepare to send request
    const char* ptr = request.c_str();
    int nleft = request.length();
    int nwritten;
    // loop to be sure it is all sent
    while (nleft) {
        if ((nwritten = send(server_, ptr, nleft, 0)) < 0) {
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

bool
Client::get_response() {
    string response = "";
    // read until we get a newline
    while (response.find("\n") == string::npos) {
        int nread = recv(server_,buf_,1024,0);
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
        response.append(buf_,nread);
    }
    // a better client would cut off anything after the newline and
    // save it in a cache
    cout << response;
    return true;
}