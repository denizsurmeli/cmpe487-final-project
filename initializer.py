import threading
import json
import time
import time

from communicator import Communicator

HELLO_MESSAGE = {
    "type": "hello"
}

HELLO_GAME_MESSAGE = {
    "type": "game",
    "total": 0,
    "vampire": 0,
    "doctor": 0,
    "current": 0,
    "myname": ""
}

JOIN_MESSAGE = {
    "type": "join",
    "myname": ""
}

ACCEPT_MESSAGE = {
    "type": "accept",
    "myname": "",
    "name_ips": []
}

# For future usage
REJECT_MESSAGE = {
    "type": "reject"
}

JOIN_ACK_MESSAGE = {
    "type": "ack",
    "action": "add",
    "name": "",
    "ip": ""
}

LEAVE_ACK_MESSAGE = {
    "type": "ack",
    "action": "remove",
    "name": "",
    "ip": ""
}

STAGE1_ROLE_MESSAGE = {
    "stage": 1,
    "type": "role",
    "number": 0,
    "role": "",
}

STAGE1_KEY_MESSAGE = {
    "stage": 1,
    "type": "key",
    "number": 0,
    "key": "",
}

STAGE1_END_MESSAGE = {
    "stage": 1,
    "type": "end"
}

STAGE2_SEND_REQ_MESSAGE = {
    "stage": 2,
    "type": "send_req"
}

STAGE2_SEND_ACPT_MESSAGE = {
    "stage": 2,
    "type": "send_acpt"
}

STAGE2_ROLE_MESSAGE = {
    "stage": 2,
    "type": "role",
    "number": 0,
    "role": "",
}

STAGE2_END_MESSAGE = {
    "stage": 2,
    "type": "end"
}

class Initializer:
    def initter_post_func(self, name, ip):
        with self.player_lock:
            self.players.remove((name, ip))
        print(name, "left.")
        with self.comm.persons_lock:
            for ip in self.comm.persons.keys():
                remove_msg = LEAVE_ACK_MESSAGE
                remove_msg["ip"] = ip
                remove_msg["name"] = self.comm.persons[ip]
                self.comm.socket_send(ip, remove_msg)

    def __init__(self, comm: Communicator):
        self.players = ()
        self.player_lock = threading.Lock()
        self.stage2 = threading.Event()
        self.complete = threading.Event()
        self.choice = int(input("Setup modes:\n1 for founder\n2 for joiner\nChoice: "))
        while not 1 <= self.choice <= 2:
            self.choice = int(input("Please enter a valid range: "))

        if self.choice == 1:
            self.ping_msg = HELLO_GAME_MESSAGE
            #self.blacklists = list(map(str.strip, input("Please enter blacklist ips seperated with comma: ").split(",")))
            self.ping_msg["total"] = int(input("Please enter player amount: "))
            self.ping_msg["vampire"] = int(input("Please enter vampire amount: "))
            self.ping_msg["doctor"] = int(input("Please enter doctor amount: "))
            self.ping_msg["myname"] = comm.myname
            self.post_func = lambda name, ip: self.initter_post_func(name, ip)
            print("Please press enter when ready...")
        else:
            self.ping_msg = HELLO_MESSAGE
            print("Please enter the initializer's name of the game you want to join:")
            self.post_func = lambda name, ip: print(name, "left.")
            self.waiting = False

        self.stage = 0

        self.comm = comm
        self.comm.recv_parser_change(self.recv_parser)

        discover_thread = threading.Thread(target=self.comm.discover_nodes, args = (self.ping_msg), daemon=True)
        discover_thread.start()
        cleanup_thread = threading.Thread(target=self.comm.cleanup_service, args = (), daemon=True)
        cleanup_thread.start()

    def information(self):
        choice = input()
        if self.choice == 2:
            while True:
                with self.comm.persons_lock:
                    if choice in self.comm.ips:
                        break
                choice = input("Please enter a valid name: ")
            join_msg = JOIN_MESSAGE
            join_msg["myname"] = self.comm.myname
            self.comm.discovery_exit_event.set()
            self.comm.socket_send(self.comm.persons[choice], join_msg)
            print("Wait for accept:")
        else:
            pass # Stage 1
        self.stage2.wait()


    def recv_parser(self, fmsg, ip):
        fmsg = json.loads(fmsg)
        # Discovery message type
        if self.choice == 1:
            if fmsg["type"] == "hello":
                self.comm.socket_send(ip, self.ping_msg)
            elif fmsg["type"] == "join":
                accept = ACCEPT_MESSAGE
                accept["myname"] = self.comm.myname
                self.comm.add_person(fmsg["myname"])
                print(f'{fmsg["myname"]} with ip {ip} joined the game')
                # (names, ips)
                with self.player_lock:
                    self.players.append((fmsg["myname"], ip))
                with self.comm.persons_lock:
                    accept["name_ips"] = list(zip(self.comm.ips.keys(), self.comm.persons.keys()))
                self.comm.socket_send(ip, accept)
                with self.comm.persons_lock:
                    for ip in self.comm.persons.keys():
                        join_msg = JOIN_ACK_MESSAGE
                        join_msg["ip"] = ip
                        join_msg["name"] = self.comm.persons[ip]
                        self.comm.socket_send(ip, join_msg)
        else:
            if fmsg["type"] == "game":
                if self.comm.add_person(fmsg["myname"]):
                    print(f'Game initializator with name: {fmsg["myname"]}, total player: {fmsg["total"]}, vampires: {fmsg["vampire"]}, doctors: {fmsg["doctor"]}')
            elif fmsg["type"] == "accept":
                self.comm.remove_persons()
                self.comm.add_person(fmsg["myname"])
                # (names, ips)
                with self.player_lock:
                    self.players = fmsg["name_ips"]
                print("Accepted. Waiting for the game to start. Players:", ",".join(x[0] for x in fmsg["name_ips"]))
            elif fmsg["type"] == "ack":
                if fmsg["action"]=="add":
                    with self.player_lock:
                        self.players.append((fmsg["name"], fmsg["ip"]))
                    print(fmsg["name"], "joined.")
                else:
                    with self.player_lock:
                        self.players.remove((fmsg["name"], fmsg["ip"]))
                    print(fmsg["name"], "left.")

