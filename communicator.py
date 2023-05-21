import threading
import json
import time
import socket
import time

class Communicator:
    PORT = 12345
    BUFFERSIZE = 1024
    persons = {} # ip -> name
    persons_lock = threading.Lock()
    ttl = {} # ip -> time
    ttl_lock = threading.Lock()
    ips = {} # name -> ip
    ips_lock = threading.Lock()
    recv_parser = lambda fmsg, addr: None
    recv_parser_lock = threading.Lock()
    myip = None
    myname = None

    def __init__(self, myip, myname):
        self.myname = myname
        self.myip = myip

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
        cleanup_thread = threading.Thread(target=self.cleanup_service, daemon=True)
        cleanup_thread.start()

    def recv_parser_change(self, new_func):
        with self.recv_parser_lock:
            self.recv_parser = new_func

    def add_person(self, name, ip):
        with self.ttl_lock: self.ttl[ip] = time.time()
        # Prevent double addition, person already added
        with self.persons_lock:
            if ip in self.persons.keys():
                return
            self.persons[ip] = name
        with self.ips_lock: self.ips[name] = ip
    
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

    def discover_nodes(self):
        print("Started node discovery...")
        hello_msg = json.dumps({"type": "hello", "myname": self.myname})
        # Discover for ever
        while True:
            self.broadcast_send(hello_msg)
            time.sleep(60)

    # Remove expired ips
    def cleanup_service(self):
        while True:
            to_remove = []
            with self.persons_lock:
                for ip in self.persons.keys():
                    if self.ttl[ip] + 120 < time.time():
                        to_remove.append(ip)
            with self.persons_lock, self.ips_lock, self.ttl_lock:
                for ip in to_remove:
                    name = self.persons[ip]
                    self.ttl.pop(ip)
                    self.persons.pop(ip)
                    self.ips.pop(name)
                    print(name, "left.")
            to_remove.clear()
            time.sleep(9) # Check for expired ttls for every 9 seconds
