import os
import threading
import json
import time
import socket
import time

PORT = 12345
BUFFERSIZE = 1024
persons = {} # ip -> name
persons_lock = threading.Lock()
ttl = {} # ip -> time
ttl_lock = threading.Lock()
ips = {} # name -> ip
ips_lock = threading.Lock()
myip = None
myname = None

HELLO_MESSAGE = {
    "type": "hello",
    "myname": None
}

GAME_MESSAGE = {
    "type": "game",
    "total": 0,
    "vampire": 0,
    "doctor": 0,
    "current": 0,
    "myname": None
}

HELLO_MESSAGE = {
    "type": "hello",
    "myname": None
}

JOIN_MESSAGE = {
    "type": "join",
    "myname": None
}

ACCEPT_MESSAGE = {
    "type": "accept"
}

STAGE1_ROLE_MESSAGE = {
    "type": "stage1",
    "data_type": "role",
    "number": 0,
    "role": "",
}

STAGE1_KEY_MESSAGE = {
    "type": "stage1",
    "data_type": "key",
    "number": 0,
    "key": "",
}

STAGE2_SEND_REQ_MESSAGE = {
    "type": "stage2",
    "data_type": "send_req"
}

STAGE2_SEND_ACPT_MESSAGE = {
    "type": "stage2",
    "data_type": "send_acpt"
}

STAGE2_ROLE_MESSAGE = {
    "type": "stage2",
    "data_type": "role",
    "number": 0,
    "role": "",
}

class Initializer:
    def socket_send(host, msg):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((host, PORT))
                s.sendall(msg.encode('UTF-8'))
        except Exception as e:
            return False
        return True

    def broadcast_send(msg):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.bind(('',0))
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST,1)
            s.sendto(msg.encode('UTF-8'), ('<broadcast>', PORT))

    def recv_parser(fmsg, ip):
        fmsg = json.loads(fmsg)
        # Discovery message type
        if fmsg["type"] == "hello":
            name = fmsg["myname"].strip()
            with ttl_lock: ttl[ip] = time.time()
            # Prevent double addition, person already added
            with persons_lock:
                if ip in persons.keys():
                    return
                persons[ip] = name
            with ips_lock: ips[name] = ip
            print(name, "with ip", ip, "joined.")
            hello_msg = json.dumps({"type": "aleykumselam", "myname": myname})
            socket_send(ip, hello_msg)
        # Reply message type
        elif fmsg["type"] == "aleykumselam":
            name = fmsg["myname"].strip()
            with ttl_lock: ttl[ip] = time.time()
            # Prevent double addition, person already added
            with persons_lock:
                if ip in persons.keys():
                    return
                persons[ip] = name
            with ips_lock: ips[name] = ip
            print(name, "with ip", ip, "joined.")
        elif fmsg["type"] == "message":
            with persons_lock:
                print(f"{persons[ip]} - {fmsg['content']}")
        else:
            print("(???) Unresolved message -", fmsg)

    def recv_msg():
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((myip, PORT))
            while True:
                # Check port for any incoming message
                s.listen()
                conn, addr = s.accept()
                fmsg=""
                try:
                    with conn:
                        while True:
                            data = conn.recv(BUFFERSIZE)
                            if not data:
                                break
                            fmsg+=data.decode('UTF-8')
                    threading.Thread(target=recv_parser, args=(fmsg, addr[0]), daemon=True).start()
                except Exception as e:
                    print("Error receiving message from",addr, ":", e)
                    pass

    def recv_broadcast():
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.bind(('', PORT))
            while True:
                data, addr = s.recvfrom(1024)
                if(addr[0] == myip):
                    continue
                threading.Thread(target=recv_parser, args=(data.decode('UTF-8'), addr[0]), daemon=True).start()

    def discover_nodes():
        print("Started node discovery...")
        hello_msg = json.dumps({"type": "hello", "myname": myname})
        # Discover for ever
        while True:
            broadcast_send(hello_msg)
            time.sleep(60)

    def send_msg(ip, msg):
        content_msg = json.dumps({"type": "message", "content": msg})
        socket_send(ip, content_msg)

    # Remove expired ips
    def cleanup_service():
        while True:
            to_remove = []
            with persons_lock:
                for ip in persons.keys():
                    if ttl[ip] + 120 < time.time():
                        to_remove.append(ip)
            with persons_lock, ips_lock, ttl_lock:
                for ip in to_remove:
                    name = persons[ip]
                    ttl.pop(ip)
                    persons.pop(ip)
                    ips.pop(name)
                    print(name, "left.")
            to_remove.clear()
            time.sleep(9) # Check for expired ttls for every 9 seconds
