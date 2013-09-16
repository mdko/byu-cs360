#include "client.h"
#include <sstream>

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
Client::prompt() {
    string whitespace = " \t";
    string ending_whitespace = " \n\t";
    string line, command, params;
    while (1) {
        cout << "% ";
        getline(cin, line);
        line = line.substr(line.find_first_not_of(whitespace));                 // removes leading whitespace
        line = line.substr(0, line.find_last_not_of(ending_whitespace) + 1);    // removes trailing whitespace

        if (line.empty()) {
            // possibly print usage as well?
            continue;
        }

        int first_ws = line.find_first_of(whitespace);
        command = line.substr(0, first_ws);                             // get command
        
        params = line.substr(first_ws);                                 // get the string holding the parameters
        params = params.substr(params.find_first_not_of(whitespace));   // with leading whitespace removed
        bool valid_usage = true;

        string request;
        if (command.compare("send") == 0) {
            string user, subject;
            first_ws = params.find_first_of(whitespace);
            user = params.substr(0, first_ws);
            // TODO check to to see if there is possibly a second parameter, 
            //  which there should be, else we'll get a segfault/out of bounds thing
            params = params.substr(first_ws);
            subject = params.substr(params.find_first_not_of(whitespace));

            cout << "- Type your message. End with a blank line -" << endl;

            string message, curr_line;
            getline(cin, curr_line);
            while (!curr_line.empty()) {    // want to test this first in case the entire message is blank
                message += curr_line;       // TODO check if the curr_line is filled with the \n.
            }

            std::ostringstream ostr;
            ostr << "put " << user << " " << subject << " " << message.length() <<  "\n" << message;
            cout << ostr.str() << endl;          

        } else if (command.compare("list") == 0) {
            // parse [user]

        } else if (command.compare("read") == 0) {
            // parse [user] [index]

        } else if (command.compare("quit") == 0) {

        } else {
            cout << "Invalid command: " << command << endl;
            cout << "Usage: [command]" << endl;
            cout << "where [command] is one of the following:" << endl;
            cout << "\tsend [user] [subject]" << endl;
            cout << "\tlist [user]" << endl;
            cout << "\tread [user] [index]" << endl;
            cout << "\tquit" << endl;
            continue;
        }

        if (valid_usage) {
            // send request
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