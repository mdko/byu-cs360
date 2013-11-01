import argparse
from server import Server

class Main:
    def __init__(self):
        self.parse_arguments()


    def parse_arguments(self):
        ''' parse arguments, which include '-p' for port and '-d' for debugging '''
        parser = argparse.ArgumentParser(prog='Web Server', description='An event-driven web server', add_help=True)
        parser.add_argument('-p', '--port', type=int, action='store', help='port the server will bind to',default=8080)
        parser.add_argument('-d', '--debug', type=int, action='store', help='debug flag to turn on debugging on the server',default=False)
        self.args = parser.parse_args()


    def run(self):
        s = Server(self.args.port)
        s.run()


if __name__ == "__main__":
    m = Main()
    m.parse_arguments()
    try:
        m.run()
    except KeyboardInterrupt:
        pass
