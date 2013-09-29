#include "server.h"
#include "client-handler.h"
#include <sstream>
#include <vector>
#include <stdexcept>      // std::out_of_range
#include <climits>
#include <iterator>

void *work(void *);
void *handle_client(void *);

Server::Server(int port, bool debug) {
    // setup variables
    port_ = port;
    max_num_threads_ = 10;
    debug_ = debug;

    struct worker_data wd;
    // create semaphores and data structures, store in struct for passing
    sem_init(&num_clients_in_queue_, 0, 0);
    sem_init(&empty_spots_in_queue_, 0, max_num_threads_);
    sem_init(&client_queue_lock_, 0, 1);
    sem_init(&message_map_lock_, 0, 1);
    wd.num_clients_in_queue = num_clients_in_queue_;
    wd.empty_spots_in_queue = empty_spots_in_queue_;
    wd.client_queue_lock = client_queue_lock_;
    wd.message_map_lock = message_map_lock_;
    // create shared queue (vector of integers)
    client_queue_ = new queue<int>();
    wd.client_queue = client_queue_;
    // create message storage
    message_map_ = new map<string, vector<message> >();
    wd.messages = message_map_;

    // create worker thread that handles clients, pass in shared stuff
    pthread_t worker;
    pthread_create(&worker, NULL, &work, &wd);
    pthread_join(worker, NULL);

    // create the server
    create();
    // run the server
    serve();
}

Server::~Server() {
    delete client_queue_;
    delete message_map_;
}

//Consumer
void *
work(void *vptr) {
    struct worker_data* wd;
    wd = (struct worker_data*) vptr;
    int client;

    while (true) {
        // take client from queue
        sem_wait(&wd->num_clients_in_queue);
        sem_wait(&wd->client_queue_lock);
        client = wd->client_queue->front();
        wd->client_queue->pop();
        sem_post(&wd->client_queue_lock);
        sem_post(&wd->empty_spots_in_queue);

        // handle it -- create a client_handler thread
        struct client_data cdata;
        cdata.client = client;
        cdata.messages = wd->messages;
        cdata.message_sem = wd->message_map_lock;
        pthread_t client_handler;
        pthread_create(&client_handler, NULL, &handle_client, &cdata);
        pthread_join(client_handler, NULL);
    }
}

void *
handle_client(void *vptr) {
    struct client_data* cd;
    cd = (struct client_data*) vptr;

    Client_Handler ch = Client_Handler(cd->client, cd->messages, cd->message_sem);
    ch.handle_client();
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

//producer
void
Server::serve() {
    // setup client
    int client;
    struct sockaddr_in client_addr;
    socklen_t clientlen = sizeof(client_addr);
    if (debug_) cout << "Serving" << endl;

      // accept clients
    while ((client = accept(server_,(struct sockaddr *)&client_addr,&clientlen)) > 0) {
        if (debug_) cout << "Accepting a client" << endl;
        sem_wait(&empty_spots_in_queue_);
        sem_wait(&client_queue_lock_);
        client_queue_->push(client);
        sem_post(&client_queue_lock_);
        sem_post(&num_clients_in_queue_);
    }
    
    close(server_);

}