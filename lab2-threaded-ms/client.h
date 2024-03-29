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
    Client(string, int, bool);
    ~Client();

private:

    void create();
    void prompt();
    bool send_request(string);
    bool get_response();

    void print_usage(string);
    string handle_input();
    string send_command(string, string);
    string list_command(string);
    string read_command(string, string);
    string format_and_output_response(string);
    string receive_message(int);
    string receive_list();

    int port_;
    string host_;
    int server_;
    int buflen_;
    char* buf_;
    string cache_;
    bool debug_;
};