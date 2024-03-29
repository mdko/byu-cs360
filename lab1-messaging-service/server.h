#include <arpa/inet.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <unistd.h>
#include <map>
#include <vector>

#include <string>
#include <iostream>

using namespace std;

class Server {
public:
    Server(int, bool);
    ~Server();

private:

    void create();
    void serve();
    void handle(int);
    string get_request(int);
    bool send_response(int, string);
    
    string handle_request(int, string);
    string store_message(int, string, string, string);
    string list_messages(string);
    string retrieve_message(string, string);
    string reset_messages();
    string receive_message(int, int);

    int port_;
    int server_;
    int buflen_;
    char* buf_;
    string cache_;
    bool debug_;

    struct message {
        string subject;
        string contents;
    };

    map<string, vector<message> >* message_map_;
};