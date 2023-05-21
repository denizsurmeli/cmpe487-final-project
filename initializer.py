import threading
import json
import time
import time

from communicator import Communicator

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
    def __init__(self, comm: Communicator):
        self.comm = comm
        self.comm.recv_parser_change(self.recv_parser)

    def recv_parser(self, fmsg, ip):
        fmsg = json.loads(fmsg)
        # Discovery message type
        if fmsg["type"] == "hello":
            name = fmsg["myname"].strip()
            self.comm.add_person(name, ip)
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
