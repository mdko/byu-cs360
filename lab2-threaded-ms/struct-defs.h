#ifndef STRUCTS_H
#define STRUCTS_H    
#include <stdio.h>
#include <stdlib.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <unistd.h>
#include <map>
#include <vector>
#include <string>
#include <iostream>
#include <pthread.h>
#include <semaphore.h>
#include <string.h>
#include <queue>

using namespace std;

typedef struct msg {
    string subject;
    string contents;
} message;

struct worker_data {
    queue<int>* client_queue;
    map<string, vector<message> >* messages;
    sem_t num_clients_in_queue;
    sem_t empty_spots_in_queue;
    sem_t client_queue_lock;
    sem_t message_map_lock;
};

struct client_data {
    int client;
    map<string, vector<message> >* messages;
    sem_t message_sem;
};

#endif