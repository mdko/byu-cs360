#include <arpa/inet.h>
#include <errno.h>
#include <netdb.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <unistd.h>

#include <fstream>
#include <iostream>
#include <string>

using namespace std;

class Client {
public:
    Client(string, int);
    ~Client();

private:

    void create();
    void prompt();
    bool send_request(string);
    bool get_response();

    void print_usage(string);
    bool handle_input();
    bool send_command(string, string);
    bool list_command(string);
    bool read_command(string, string);

    int port_;
    string host_;
    int server_;
    int buflen_;
    char* buf_;
};