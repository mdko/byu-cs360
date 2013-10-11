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
#include <queue>

using namespace std;

class Server {
public:
    Server(int, bool);
    ~Server();

private:

    void create();

    int port_;
    int server_;
    int num_threads_;
    int client_queue_size_;
    bool debug_;
};