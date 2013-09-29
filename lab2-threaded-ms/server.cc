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
    max_num_threads_ = 100;
    debug_ = debug;

    struct data wd;
    // create semaphores and data structures, store in struct for passing
    sem_init(&wd.num_clients_in_queue, 0, 0);
    sem_init(&wd.empty_spots_in_queue, 0, max_num_threads_);
    sem_init(&wd.client_queue_lock, 0, 1);
    sem_init(&wd.message_map_lock, 0, 1);
    // create shared queue (vector of integers)
    wd.client_queue = new queue<int>();
    // create message storage
    wd.messages = new map<string, vector<message> >();

    if (debug_) cout << "Creating the server" << endl;
    // create the server
    create();
    wd.server = server_;

    if (debug_) cout << "Creating thread to handle the distribution of clients" << endl;
    // create worker thread that handles clients, pass in shared stuff
    pthread_t worker;
    pthread_create(&worker, NULL, &work, &wd);

    // run the server
    if (debug_) cout << "Running the server" << endl;
    pthread_t server;
    pthread_create(&server, NULL, &serve, &wd);

    pthread_join(worker, NULL);
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
    //cout << "Serving" << endl;

      // accept clients
    while ((client = accept(wd->server,(struct sockaddr *)&client_addr,&clientlen)) > 0) {
        //cout << "Accepting a client" << endl;
        sem_wait(&wd->empty_spots_in_queue);
        sem_wait(&wd->client_queue_lock);
        wd->client_queue->push(client);
        sem_post(&wd->client_queue_lock);
        sem_post(&wd->num_clients_in_queue);
        //cout << "End of accept loop" << endl;
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
        //cout << "Start of consumer while loop" << endl;
        // take client from queue
        sem_wait(&wd->num_clients_in_queue);
        //cout << "Done waiting for something in queue" << endl;
        sem_wait(&wd->client_queue_lock);
        //cout << "Taking client from the queue" << endl;

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
        //cout << "End of consumer while loop" << endl;
    }
}

void *
handle_client(void *vptr) {
    struct client_data* cd;
    cd = (struct client_data*) vptr;

    //cout << "Calling client_handler" << endl;
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