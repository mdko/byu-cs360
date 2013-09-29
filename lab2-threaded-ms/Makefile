# Makefile for socket examples

CXX=			g++ $(CCFLAGS)
SERVER=			messaging-service-server.o server.o client-handler.o
CLIENT=			messaging-service-client.o client.o
OBJS =			$(SERVER) $(CLIENT) 

LIBS= 			-pthread

CCFLAGS= -g

all:	server client

server:$(SERVER)
	$(CXX) -o msgd $(SERVER) $(LIBS)

client:$(CLIENT)
	$(CXX) -o msg $(CLIENT) $(LIBS)

clean:
	rm -f $(OBJS) $(OBJS:.o=.d)

realclean:
	rm -f $(OBJS) $(OBJS:.o=.d) msgd msg


# These lines ensure that dependencies are handled automatically.
%.d:	%.cc
	$(SHELL) -ec '$(CC) -M $(CPPFLAGS) $< \
		| sed '\''s/\($*\)\.o[ :]*/\1.o $@ : /g'\'' > $@; \
		[ -s $@ ] || rm -f $@'

include	$(OBJS:.o=.d)