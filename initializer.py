import threading
import json
import time
import random

from cryptography.fernet import Fernet
import base64

from communicator import Communicator

HELLO_MESSAGE = {
    "type": "hello"
}

HELLO_GAME_MESSAGE = {
    "type": "game",
    "total": 0,
    "vampire": 0,
    "doctor": 0,
    "current": 1, # Distributor themselves are also a player
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
STAGE0_END_MESSAGE = {
    "stage": 0,
    "type": "end"
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

STAGE2_SEND_RJCK_MESSAGE = {
    "stage": 2,
    "type": "send_rjck"
}

STAGE2_ROLE_MESSAGE = {
    "stage": 2,
    "type": "role",
    "number": 0,
    "role": "",
}

# If a player couldn't distributed their own key, they can get it.
# It is an exceptional case, and cannot be used for cheating purposes in non-initializer nodes.
# Even if initializer cheats, it should happen seldomly, so it shouldn't cause a problem.
# Theoratically, if it happens, it should only happen to one node in a game.
STAGE2_KEYEXC_MESSAGE = {
    "stage": 2,
    "type": "key_exc",
    "number": 0,
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
            for ips in self.comm.persons.keys():
                remove_msg = LEAVE_ACK_MESSAGE
                remove_msg["ip"] = ip
                remove_msg["name"] = name
                self.comm.socket_send(ips, remove_msg)
        self.ping_msg["current"]-=1

    def __init__(self, comm: Communicator):
        self.players = []
        self.player_lock = threading.Lock()
        self.stage2 = threading.Event()
        self.answer = threading.Event()
        self.accepted = False
        self.complete = threading.Event()
        self.counter = 0
        self.counter_lock = threading.Lock()
        self.asked = None
        self.asked_receive = threading.Event()
        self.keys = {}
        self.keys_lock = threading.Lock()
        self.roles = {}
        self.roles_lock = threading.Lock()
        self.role = None
        self.role_lock = threading.Lock()
        self.distributor = None
        self.choice = int(input("Setup modes:\n1 for founder\n2 for joiner\nChoice: "))
        while not 1 <= self.choice <= 2:
            self.choice = int(input("Please enter a valid range: "))

        self.stage = 0
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


        self.comm = comm
        self.comm.recv_parser_change(self.recv_parser)

        discover_thread = threading.Thread(target=self.comm.discover_nodes, args = (self.ping_msg,), daemon=True)
        discover_thread.start()
        cleanup_thread = threading.Thread(target=self.comm.cleanup_service, args = (), daemon=True)
        cleanup_thread.start()

    def information(self):
        choice = input()
        if self.choice == 2:
            while True:
                while True:
                    with self.comm.persons_lock:
                        if choice in self.comm.ips:
                            break
                    choice = input("Please enter a valid name: ")
                join_msg = JOIN_MESSAGE
                join_msg["myname"] = self.comm.myname
                self.comm.discovery_exit.set()
                self.comm.socket_send(self.comm.ips[choice], join_msg)
                print("Wait for accept:")
                self.answer.wait()
                if self.accepted:
                    print("Accepted")
                    self.distributor = (choice, self.comm.ips[choice])
                    self.players.append(self.distributor)
                    break
                print("Rejected.")
                self.answer.clear()
            self.stage2.wait()
            print("Players:", self.players)
            print("Stage2 started, assigning unassigned players with roles...")
            print("To distribute:", self.keys, self.roles, len(self.roles))
            with self.player_lock:
                random.shuffle(self.players)
                cur_role = 0
                ok = False
                for player in self.players:
                    self.asked = player[1]
                    self.comm.socket_send(player[1], STAGE2_SEND_REQ_MESSAGE)
                    print("Asked:", player[0])
                    self.asked_receive.wait()
                    self.asked_receive.clear()
                    if self.asked:
                        msg = STAGE2_ROLE_MESSAGE
                        msg["number"] = list(self.roles.keys())[cur_role]
                        msg["role"] = self.roles[msg["number"]]
                        self.comm.socket_send(player[1], msg)
                        cur_role+=1
                        print("Sent role to", player[0])
                        if len(self.roles)<=cur_role:
                            ok=True
                            break
                        continue
                    print(self.players[0], "already received role")
                if not ok: # Couldn't send one role
                    print("One role couldn't distributed! Asking node for the key to acquire it.")
                    msg = STAGE2_KEYEXC_MESSAGE
                    msg["number"] = list(self.roles.keys())[cur_role]
                    self.comm.socket_send(self.distributor[1], msg)
                else:
                    print("Roles distributed successfully...")
                    while True:
                        with self.role_lock:
                            if not (self.role == None or self.role == "occupied"):
                                break
                        time.sleep(0.5)
                    self.comm.socket_send(self.distributor[1], STAGE2_END_MESSAGE)
        else:
            self.stage=1
            with self.player_lock:
                for player in self.players:
                    self.comm.socket_send(player[1], STAGE0_END_MESSAGE)
                role_list = ["vampire" for _ in range(self.ping_msg["vampire"])] + \
                            ["doctor" for _ in range(self.ping_msg["doctor"])]
                role_list = role_list + ["koylu" for _ in range(len(self.players)-len(role_list)+1)]
                random.shuffle(role_list)
                self.comm.cleanup_exit.set()
                self.comm.discovery_exit.set()

                # First one should send 2 because distributor cant send at stage 2
                self.players.append(self.players[0])

                cur = 0
                for role_player, role in zip(self.players, role_list):
                    key = Fernet.generate_key()
                    self.keys[cur] = key
                    token = Fernet(key).encrypt(role.encode())
                    for key_player in self.players:
                        if role_player==key_player:
                            msg = STAGE1_ROLE_MESSAGE
                            msg["number"]=cur
                            msg["role"] = base64.b64encode(token).decode()
                            self.comm.socket_send(role_player[1], msg)
                            continue
                        msg = STAGE1_KEY_MESSAGE
                        msg["number"]=cur
                        msg["key"] = base64.b64encode(key).decode()
                        self.comm.socket_send(key_player[1], msg)
                        
                    cur += 1
                self.players.pop()

                print("Sent all, wait for others to receive...")
                self.stage2.wait()
                print("Stage1 ended, now other nodes will distribute keys...")
                self.stage=2
        print("Transfers completed:", self.players)
        self.complete.wait()
        print("All completed:", self.role)
        return self.players, self.role
                

    def recv_parser(self, fmsg, ip):
        fmsg = json.loads(fmsg)
        #print(f"received: at stage {self.stage}", fmsg)
        # Discovery message type
        if self.stage==0:
            if self.choice == 1:
                if fmsg["type"] == "hello":
                    print("Echo hello")
                    self.comm.socket_send(ip, self.ping_msg)
                    
                    add = False
                    with self.comm.persons_lock:
                        add = ip in self.comm.persons.keys()
                    if add:
                        self.comm.add_person(fmsg["myname"], ip)
                elif fmsg["type"] == "join":
                    if self.ping_msg["current"] >= self.ping_msg["total"]:
                        self.comm.socket_send(ip, REJECT_MESSAGE)
                        return
                    accept = ACCEPT_MESSAGE
                    accept["myname"] = self.comm.myname
                    with self.comm.persons_lock:
                        accept["name_ips"] = list(zip(self.comm.ips.keys(), self.comm.persons.keys()))
                    self.comm.add_person(fmsg["myname"], ip)
                    print(f'{fmsg["myname"]} with ip {ip} joined the game')
                    # (names, ips)
                    with self.player_lock:
                        self.players.append((fmsg["myname"], ip))
                    self.comm.socket_send(ip, accept)
                    with self.comm.persons_lock:
                        for ips in self.comm.persons.keys():
                            if ip == ips:
                                continue
                            join_msg = JOIN_ACK_MESSAGE
                            join_msg["ip"] = ip
                            join_msg["name"] = self.comm.persons[ip]
                            self.comm.socket_send(ips, join_msg)
                    self.ping_msg["current"]+=1
            else:
                if fmsg["type"] == "game":
                    print("Echo game")
                    self.comm.add_person(fmsg["myname"], ip)
                    print(f'Game initializator with name: {fmsg["myname"]}, total player: {fmsg["total"]}, vampires: {fmsg["vampire"]}, doctors: {fmsg["doctor"]}')
                elif fmsg["type"] == "accept":
                    self.comm.remove_persons()
                    self.comm.add_person(fmsg["myname"], ip)
                    # (names, ips)
                    with self.player_lock:
                        self.players = fmsg["name_ips"]
                    print("Waiting for the game to start. Players:", ",".join(x[0] for x in fmsg["name_ips"]))
                    self.accepted = True
                    self.answer.set()
                elif fmsg["type"] == "reject":
                    self.accepted = False
                    self.answer.set()
                elif fmsg["type"] == "ack":
                    print("Player ack:", fmsg)
                    if fmsg["action"]=="add":
                        with self.player_lock:
                            self.players.append((fmsg["name"], fmsg["ip"]))
                        print(fmsg["name"], "joined.")
                    else:
                        with self.player_lock:
                            self.players.remove((fmsg["name"], fmsg["ip"]))
                        print(fmsg["name"], "left.")
                elif fmsg["type"] == "end":
                    self.stage = 1
                    self.comm.cleanup_exit.set()
                    self.comm.discovery_exit.set()
                    print("Stage0 ended, now initializer will distribute roles...")
        elif self.stage==1:
            if fmsg["type"] == "role":
                with self.roles_lock:
                    self.roles[fmsg["number"]]=fmsg["role"]
                self.comm.socket_send(self.distributor[1], STAGE1_END_MESSAGE)
                return
            if fmsg["type"] == "key":
                with self.keys_lock:
                    self.keys[fmsg["number"]]=base64.b64decode(fmsg["key"])
                self.comm.socket_send(self.distributor[1], STAGE1_END_MESSAGE)
                return
            if fmsg["type"] == "end":
                print("Receive end stage 1")
                if self.choice == 1:
                    with self.counter_lock:
                        self.counter+=1
                        print("Counter:", self.counter)
                        if self.counter >= (len(self.players)+1)**2:
                            self.stage = 2
                            self.stage2.set()
                            self.counter = 0
                            with self.player_lock:
                                for person in self.players:
                                    self.comm.socket_send(person[1], STAGE1_END_MESSAGE)
                else:
                    self.stage = 2
                    self.stage2.set()
            if fmsg["type"] == "send_req":
                self.stage = 2
                self.stage2.set()
                with self.role_lock:
                    if self.role == None:
                        self.role = "occupied"
                        self.comm.socket_send(ip, STAGE2_SEND_ACPT_MESSAGE)
                    else: 
                        self.comm.socket_send(ip, STAGE2_SEND_RJCK_MESSAGE)
        else:
            if fmsg["type"] == "send_req":
                with self.role_lock:
                    if self.role == None:
                        self.role = "occupied"
                        self.comm.socket_send(ip, STAGE2_SEND_ACPT_MESSAGE)
                    else: 
                        self.comm.socket_send(ip, STAGE2_SEND_RJCK_MESSAGE)
            if fmsg["type"] == "send_acpt":
                self.asked = True
                self.asked_receive.set()
            if fmsg["type"] == "send_rjck":
                self.asked = False
                self.asked_receive.set()
            if fmsg["type"] == "key_exc":
                with self.player_lock:
                    if (self.players[0][1] == ip and fmsg["number"] == len(self.players)) or self.players[fmsg["number"]][1] == ip:
                        time.sleep(5) # Wait to prevent cheating
                        msg = STAGE1_KEY_MESSAGE
                        msg["number"]=fmsg["number"]
                        msg["key"] = base64.b64encode(self.keys[fmsg["number"]]).decode()
                        self.comm.socket_send(ip, msg)
                return
            if fmsg["type"] == "key":
                with self.role_lock:
                    self.role=Fernet(base64.b64decode(fmsg["key"])).decrypt(base64.b64decode(self.roles[fmsg["number"]])).decode()
                print("Received role:", self.role)
                self.comm.socket_send(self.distributor[1], STAGE2_END_MESSAGE)
                return
            if fmsg["type"] == "role":
                with self.role_lock:
                    self.role=Fernet(self.keys[fmsg["number"]]).decrypt(base64.b64decode(fmsg["role"])).decode()
                print("Received role:", self.role)
            if fmsg["type"] == "end":
                if self.choice == 1:
                    with self.counter_lock:
                        self.counter+=1
                        print("Counter:", self.counter)
                        if self.counter >= len(self.players):
                            with self.player_lock:
                                for person in self.players:
                                    self.comm.socket_send(person[1], STAGE2_END_MESSAGE)
                            self.complete.set()
                else:
                    self.complete.set()
                