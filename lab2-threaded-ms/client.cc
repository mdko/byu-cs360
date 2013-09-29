#include "client.h"
#include <sstream>
#include <vector>
#include <stdexcept>      // std::out_of_range  
#include <climits>

Client::Client(string host, int port, bool debug) {
    // setup variables
    host_ = host;
    port_ = port;
    buflen_ = 1024;
    buf_ = new char[buflen_+1];
    debug_ = debug;

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

    if (debug_) cout << "Client is trying to connect to server" << endl;
    // connect to server
    if (connect(server_,(const struct sockaddr *)&server_addr,sizeof(server_addr)) < 0) {
        perror("connect");
        exit(-1);
    }
}

void
Client::print_usage(string original_string) {
    cout << "error invalid command/format: \"" << original_string << "\"" << endl;
    cout << "usage: [command]" << endl;
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
    try {
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
            request = "";
        } 
    } catch (const std::out_of_range& oor) {
        // not enough arguments provided
        cout << "error handling request in client -- to few arguments" << endl;
        request = "";
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

string
Client::format_and_output_response(string response) {
    string original_response = response;
    if (debug_) cout << "entering format_and_output_response, input: " << response << endl;
    std::ostringstream resp;
    vector<string> tokens;
    // Tokenize
    int pos = response.find_first_of(" ");
    while (pos != string::npos) {
        tokens.push_back(response.substr(0, pos));
        response.erase(0, pos+1);
        pos = response.find_first_of(" \t");
    }
    pos = response.find_first_of("\n");
    if (pos != string::npos) {
        response.erase(pos,1);
    }
    tokens.push_back(response);

    try {
        string resp_command = tokens.at(0);

        if (resp_command.compare("list") == 0) {
            if (debug_) cout << "list response detected" << endl;
            int number = strtol(tokens.at(1).c_str(), NULL, 10);
            if (number == 0L || number == LONG_MAX || number == LONG_MIN) {
                resp << "error coudldn't parse the number field in the list returned from the server\n";
            } else {
                resp << receive_list() << "\n";
                // for (int i = 0; i < number; i += 2) {
                //     resp << tokens.at(2 + i) << " " << tokens.at(3 + i) << "\n";
                // }
            }
        } else if (resp_command.compare("message") == 0) {
            if (debug_) cout << "message response detected" << endl;
            string subject = tokens.at(1);
            int length = strtol(tokens.at(2).c_str(), NULL, 10);
            if (length == 0L || length == LONG_MAX || length == LONG_MIN) {
                resp << "error coudldn't parse the length field in the message returned from the server\n";
            }
            else {
                resp << receive_message(length) << "\n";
            }
        } else if (resp_command.compare("error") == 0) { 
            resp << original_response;
        } else if (resp_command.compare("OK") == 0 ){ // OK (from reset or send)
            resp << "";
        } else {
            resp << "error invalid response returned from server";
        }

    } catch (const std::out_of_range& oor) {
        // not enough arguments provided
        resp << "error formatting response in client -- to few arguments\n";
    }
    if (debug_) cout << "returning from format_and_output_response with \"" << resp.str() << "\"" << endl;
    return resp.str();
}

string
Client::receive_list() {
    if (debug_) cout << "current cache \"" << cache_ << "\"" << endl;
    string list = "";
    // Tokenize
    cache_.erase(0, 1); // remove leading \n
    int pos = cache_.find_first_of("\n");
    while (pos != string::npos) {
        if (debug_) cout << "current cache \"" << cache_ << "\"" << endl;
        string line = cache_.substr(0, pos);
        //if (debug_) cout << "line being output " << line << endl;
        if (line.empty()) {
            break;
        }
        list += line + "\n";
        cache_.erase(0, pos+1);
        pos = cache_.find_first_of("\n");
    }
    pos = list.find_last_of("\n");  // remove the extra trailing \n for some reason
    if (pos == list.length() - 1)
        list.erase(pos,1);
    return list;
}

string
Client::receive_message(int length) {
    if (debug_) cout << "entering receive_message method" << endl;
    string message = cache_;
    int count = message.length();
    // read until we get a newline
    while (count < length) {
        if (debug_) cout << "current count " << count << endl;
        int nread = recv(server_,buf_,1024,0);
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

    // remove 1 preceeding newlines
    int pos = message.find_first_of("\n");
    message.erase(pos,1);
    // and 1 trailing newline
    pos = message.find_last_of("\n");
    if (pos != string::npos && pos == message.length()-1)
        message.erase(pos,1);

    if (debug_) cout << "returning from receive_message method with " << message << endl;
    return message;
}

void
Client::prompt() {
    while (1) {
        cout << "% ";
        string request = handle_input();
        if (!request.empty()) {
            // send request
            if (debug_) cout << "client is sending the following to the server: " << request << endl;
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
    cache_ = "";
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

    int pos_mes = response.find_first_of("\n");
    cache_ += response.substr(pos_mes);
    response.erase(pos_mes);
    if (debug_) cout << "get_response: what came from server:\n" << response << endl;
    if (debug_) cout << "current cache: " << cache_ << endl;
    response = format_and_output_response(response);
    // int pos = response.find_last_of("\n");
    // if (pos != string::npos && pos == (response.length() - 1))
    //     response.erase(pos, 1);
    cout << response;
    return true;
}