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
    void serve();

    int port_;
    int server_;
    int max_num_threads_;
    bool debug_;

    sem_t num_clients_in_queue_; // in producer-consumer problem, n - coordinates when the queue is empty
    sem_t empty_spots_in_queue_; // in producer-consumer problem, e - coordinates when queue is empty enough to put stuff in
    sem_t client_queue_lock_;    // in producer-consumer problem, s - control access to critial section
    sem_t message_map_lock_;     // for storing messages

    queue<int>* client_queue_;

    map<string, vector<message> >* message_map_;
};