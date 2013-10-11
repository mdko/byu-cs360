#include "struct-defs.h"
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
#include <pthread.h>
#include <semaphore.h>

using namespace std;

class Client_Handler {
public:
    Client_Handler(int, map<string, vector<message> >*, sem_t*);
    ~Client_Handler();

    void handle_client();

private:
    void handle(int);
    string get_request(int);
    bool send_response(int, string);
    
    string handle_request(int, string);
    string store_message(int, string, string, string);
    string list_messages(string);
    string retrieve_message(string, string);
    string reset_messages();
    string receive_message(int, int);

	int client_;
	sem_t* messages_lock_;
	map<string, vector<message> >* message_map_;
    char* buf_;
    int buflen_;
    string cache_;
    bool debug_;
};