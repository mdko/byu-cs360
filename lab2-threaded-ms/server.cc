#include "server.h"
#include "client-handler.h"
#include <sstream>
#include <vector>
#include <stdexcept>      // std::out_of_range
#include <climits>
#include <iterator>

void *work(void *);
void *serve(void *);
void *handle_client(void *);

Server::Server(int port, bool debug) {
    // setup variables
    port_ = port;
    num_threads_ = 10;
    client_queue_size_ = 100;
    debug_ = debug;

    struct data wd;
    // create semaphores and data structures, store in struct for passing
    sem_init(&wd.num_clients_in_queue, 0, 0);
    sem_init(&wd.empty_spots_in_client_queue, 0, client_queue_size_);
    sem_init(&wd.client_queue_lock, 0, 1);
    sem_t * mml = new sem_t;
    sem_init(mml, 0, 1);
    wd.message_map_lock = mml;
    // create shared queue (vector of integers)
    wd.client_queue = new queue<int>();
    // create message storage
    wd.messages = new map<string, vector<message> >();

    // create the server
    create();
    wd.server = server_;

    // Call this ten times to create 10 worker threads that handle clients, passing in shared stuff
    for (int i = 0; i < num_threads_; i++) {
        pthread_t worker;
        pthread_create(&worker, NULL, &work, &wd);
    }

    // run the server (not a necessary thread, but I did this in case there was something
    // else I wanted to do after creating a thread to serve)
    pthread_t server;
    pthread_create(&server, NULL, &serve, &wd);

    //pthread_join-ing on the workers is unnecessary here since we're ending the program here
    pthread_join(server, NULL);
}

Server::~Server() {
}

//producer
void *
serve(void *vptr) {
    struct data* wd;
    wd = (struct data*) vptr;

    int client;
    struct sockaddr_in client_addr;
    socklen_t clientlen = sizeof(client_addr);

      // accept clients
    while ((client = accept(wd->server,(struct sockaddr *)&client_addr,&clientlen)) > 0) {
        sem_wait(&wd->empty_spots_in_client_queue);  // if using a finite buffer for client storage
        sem_wait(&wd->client_queue_lock);
        wd->client_queue->push(client);
        sem_post(&wd->client_queue_lock);
        sem_post(&wd->num_clients_in_queue);
    }
    
    close(wd->server);
}

//Consumer
void *
work(void *vptr) {
    struct data* wd;
    wd = (struct data*) vptr;
    int client;

    while (true) {

        // take client from queue
        sem_wait(&wd->num_clients_in_queue);
        sem_wait(&wd->client_queue_lock);

        client = wd->client_queue->front();
        wd->client_queue->pop();
        sem_post(&wd->client_queue_lock);
        sem_post(&wd->empty_spots_in_client_queue);  // using a finite buffer for client storage

        // call handle client directly instead of this dumb thread
        Client_Handler ch = Client_Handler(client, wd->messages, wd->message_map_lock);
        ch.handle_client();
    }
}

void
Server::create() {
    struct sockaddr_in server_addr;

    // setup socket address structure
    memset(&server_addr,0,sizeof(server_addr));
    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(port_);
    server_addr.sin_addr.s_addr = INADDR_ANY;

    // create socket
    server_ = socket(PF_INET,SOCK_STREAM,0);
    if (!server_) {
        perror("socket");
        exit(-1);
    }

    // set socket to immediately reuse port when the application closes
    int reuse = 1;
    if (setsockopt(server_, SOL_SOCKET, SO_REUSEADDR, &reuse, sizeof(reuse)) < 0) {
        perror("setsockopt");
        exit(-1);
    }

    // call bind to associate the socket with our local address and
    // port
    if (bind(server_,(const struct sockaddr *)&server_addr,sizeof(server_addr)) < 0) {
        perror("bind");
        exit(-1);
    }

      // convert the socket to listen for incoming connections
    if (listen(server_,SOMAXCONN) < 0) {
        perror("listen");
        exit(-1);
    }
}