import threading
import json
import time
import socket
import time

class Communicator:
    def __init__(self, myip, myname):
        self.PORT = 12345
        self.BUFFERSIZE = 1024
        self.myname = myname
        self.myip = myip
        self.persons = {} # ip -> name
        self.ttl = {} # ip -> time
        self.ips = {} # name -> ip
        self.persons_lock = threading.Lock()
        self.recv_parser = lambda fmsg, addr: None
        self.recv_parser_lock = threading.Lock()
        self.discovery_exit = threading.Event()
        self.cleanup_exit = threading.Event()

        # Start listening to port
        read_thread = threading.Thread(target=self.recv_msg, daemon=True)
        read_thread.start()

        # Get greeting from other peers
        broadcast_thread = threading.Thread(target=self.recv_broadcast, daemon=True)
        broadcast_thread.start()

        # Discover other peers
        #discover_thread = threading.Thread(target=self.discover_nodes, daemon=True)
        #discover_thread.start()

        # Periodic cleanup service
        #cleanup_thread = threading.Thread(target=self.cleanup_service, daemon=True)
        #cleanup_thread.start()

    def recv_parser_change(self, new_func):
        with self.recv_parser_lock:
            self.recv_parser = new_func

    def add_person(self, name, ip):
        # Prevent double addition, person already added
        with self.persons_lock:
            self.ttl[ip] = time.time()
            if ip in self.persons.keys():
                return False
            self.persons[ip] = name
            self.ips[name] = ip
        return True
    
    def socket_send(self, host, msg):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((host, self.PORT))
                s.sendall(msg.encode('UTF-8'))
        except Exception as e:
            return False
        return True

    def broadcast_send(self, msg):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.bind(('',0))
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST,1)
            s.sendto(msg.encode('UTF-8'), ('<broadcast>', self.PORT))


    def recv_msg(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((self.myip, self.PORT))
            while True:
                # Check port for any incoming message
                s.listen()
                conn, addr = s.accept()
                fmsg=""
                try:
                    with conn:
                        while True:
                            data = conn.recv(self.BUFFERSIZE)
                            if not data:
                                break
                            fmsg+=data.decode('UTF-8')
                    threading.Thread(target=self.recv_parser, args=(fmsg, addr[0]), daemon=True).start()
                except Exception as e:
                    print("Error receiving message from",addr, ":", e)
                    pass

    def recv_broadcast(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.bind(('', self.PORT))
            while True:
                data, addr = s.recvfrom(1024)
                if(addr[0] == self.myip):
                    continue
                threading.Thread(target=self.recv_parser, args=(data.decode('UTF-8'), addr[0]), daemon=True).start()

    def discover_nodes(self, msg):
        # Discover for ever
        while not self.discovery_exit.wait(60):
            self.broadcast_send(msg)

    # Remove expired ips
    def cleanup_service(self, post_function = lambda name, ip: print(name, "left.")):
        while not self.cleanup_exit.wait(11):
            self.remove_persons(lambda ip: self.ttl[ip] + 120 < time.time(), post_function)

    def remove_persons(self, if_function = lambda ip: True, post_function = lambda name, ip: None):
        with self.persons_lock:
            for ip in self.persons.keys():
                if if_function(ip):
                    name = self.persons[ip]
                    self.ttl.pop(ip)
                    self.persons.pop(ip)
                    self.ips.pop(name)
                    post_function(name, ip)

    
