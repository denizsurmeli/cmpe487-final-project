"""
Definitions and functionalities of the roles, the game state etc.
"""

import threading
import enum
from utility import build_id
import json


STATE_SYNC = {
    "type": "state_sync",
    "killed": [],
    "saved": [],
    "protected": []
}

DEAD_ACK = {
    "type": "dead_ack",
    "role": None,
    "id": None
}

class Role(enum.Enum):
    vampire = 1
    doctor = 2
    villager = 3

class Partition(enum.Enum):
    day = 1
    prenight = 2
    night = 3
    prevote = 4
    voting = 5
    postvote = 6
    end = 7

def parse_role(role: str) -> Role:
    if role == "vampire":
        return Role.vampire
    elif role == "doctor":
        return Role.doctor
    else:
        return Role.villager

class Player: 
    def __init__(self, data: dict):
        # In the dictionary, it's absolutely necessary to have ip and name, but role is optional
        self.ip = data["ip"]
        self.name = data["name"]
        self.id = build_id(self.ip, self.name)
        
        if "role" in data.keys() and data["role"] is not None:
            self.role = parse_role(data["role"])
        else:
            self.role = None

    def __eq__(self, other):
        if other is None:
            return False 
        return self.ip == other.ip and self.id == other.id
    
    def __hash__(self):
        return hash((self.ip, self.id))
    
    def __str__(self):
        return f"Player {self.name} ({self.ip}:{self.id})"
    

def pair_to_player(ip:str, name:str, role:str = None) -> Player:
    return Player({"ip": ip, "name": name, "role": role})

def id_to_player(id: str, players: list) -> Player:
    for player in players:
        if player.id == id:
            return player
    return None

class State:
    def __init__(self, players, client, communicator, counts:tuple):
        self.players = players # we don't drop the players from the list even though they are alive or not
        self.villager_count, self.vampire_count, self.doctor_count = counts[0], counts[1], counts[2] # (villager_count, vampire_count, doctor_count)
        self.client = client
        self.communicator = communicator

        self.round :int = 1
        self.partition :Partition = Partition.day
        self.partition_lock = threading.Lock()

        # This map is persistent, others are renewed every loop.
        self.alive = {player: True for player in players}
        self.alive_lock = threading.Lock()

        self.protected = dict()
        self.protected_lock = threading.Lock()

        self.killed = dict() 
        self.killed_lock = threading.Lock()

        self.saved = dict()
        self.saved_lock = threading.Lock()

        # what have changed in the last day&night
        self.delta = {"killed":[], "saved":[], "protected":[]}
        self.delta_lock = threading.Lock()

        # captured vampire count
        self.captured_vampire_count = 0
        self.captured_vampire_list = []
        self.captured_vampire_lock = threading.Lock()

        self.wait_partition_event = threading.Event()

    def change_state(self, partition: Partition):
        with self.partition_lock:
            self.partition = partition

    def sync_delta(self):
        if self.partition == Partition.prenight:
            with self.delta_lock:
                # process the delta
                for id in self.delta["protected"]:
                    self.protect(id_to_player(id, self.players))
                for id in self.delta["killed"]:
                    self.kill(id_to_player(id, self.players))
            # We dont want to erase states yet
            return
        if self.partition == Partition.prevote:
            with self.delta_lock:
                # process the delta
                for id in self.delta["protected"]:
                    self.protect(id_to_player(id, self.players))
                for id in self.delta["killed"]:
                    self.kill(id_to_player(id, self.players))
        if self.partition == Partition.postvote:
            with self.delta_lock:
                # process the delta
                for id in self.delta["killed"]:
                    print(f"Player {id} is killed by the vote.")
                    self.kill(id_to_player(id, self.players))

        with self.delta_lock:
            self.delta = {"killed":[], "saved":[], "protected":[]}

    def self_live_check(self, player):
        if player == self.client:
            # vampire is captured
            payload = DEAD_ACK.copy()
            payload["id"] = player.id
            payload["role"] = player.role.value
            self.communicator.socket_send_all(payload)
            print("You have been killed...")
            if player.role.value == Role.vampire.value and player.id not in self.captured_vampire_list:
                with self.captured_vampire_lock:
                    self.captured_vampire_count += 1
                    self.captured_vampire_list.append(player.id)
    
    def kill(self, player:Player):
        if self.partition == Partition.night or self.partition == Partition.prevote:
            with self.protected_lock:
                if player not in self.protected.keys():
                    print(f"Player {player.id} is killed by the vampire.")
                    with self.killed_lock:
                        self.killed[player] = True
                    with self.alive_lock:
                        self.alive[player] = False
                    self.self_live_check(player)
                else:
                    print(f"Player {player.id} is protected by the doctor.")
                    self.save(player)

        elif self.partition == Partition.postvote:
            with self.killed_lock:
                self.killed[player] = True
            with self.alive_lock:
                self.alive[player] = False
            self.self_live_check(player)
        # Only one vote is allowed
        if self.partition == Partition.night:
            self.wait_partition_event.wait()
            self.wait_partition_event.clear()

    
    def save(self, player):
        with self.saved_lock:
            self.saved[player] = True

    def protect(self, player:Player):
        if self.partition == Partition.day or self.partition == Partition.prenight:
            with self.protected_lock:
                self.protected[player] = True

    def is_over(self):
        # if the number of alive people <= number of alive vampires, vampires win
        with self.alive_lock:
            alive_player_count = len([player for player,state in self.alive.items() if state])
            print("Alive player count: ", alive_player_count)
            print("Alive vampire count: ", self.vampire_count - self.captured_vampire_count) 
        if self.captured_vampire_count >= self.vampire_count:
            # all vampires have been caught
            return (True, Role.villager)
        if alive_player_count <= 2*(self.vampire_count - self.captured_vampire_count):
            # vampires dominate the village, no chance for villagers to win
            return (True, Role.vampire)
        return (False, None)
                         
        
    def round_cleanup(self):
        with self.killed_lock:
            self.killed = dict()
        with self.saved_lock:
            self.saved = dict()
        with self.protected_lock:
            self.protected = dict()
        with self.delta_lock:
            self.delta = {"killed":[], "saved":[], "protected":[]}
        # if game is over, change the state to end else rewind to a new round
        if self.is_over()[0]:
            self.change_state(Partition.end)
        else:
            self.change_state(Partition.day)
            self.round += 1

    def dump_delta(self):
        # If the game is in prevoting stage, show who have been killed and saved last night.
        with self.killed_lock, self.saved_lock, self.protected_lock, self.delta_lock:
            delta = STATE_SYNC.copy()
            delta["killed"] = [player.id for player,state in self.killed.items() if state]
            delta["saved"] = [player.id for player,state in self.saved.items() if state]
            delta["protected"] = [player.id for player,state in self.protected.items() if state]
        return delta


    def recv_parser(self, message: str, ip: str):
        # only attached when the game is in prevoting stage
        try:
            message = json.loads(message)
        except Exception as e:
            print("FATALERR: Error while unmarshalling the message:", e, message)
            return

        with self.partition_lock,self.delta_lock, self.captured_vampire_lock:
            if self.partition in [Partition.prenight, Partition.prevote, Partition.postvote] and message["type"] == STATE_SYNC["type"]:
                    self.delta["killed"] += message["killed"]
                    self.delta["saved"] += message["saved"]
                    self.delta["protected"] += message["protected"]
            elif message["type"] == DEAD_ACK["type"]:
                if Role(message["role"]).value == Role.vampire.value and message["id"] not in self.captured_vampire_list:
                    self.captured_vampire_count += 1
                    self.captured_vampire_list.append(message["id"])
                print(f"Killed player {message['id']} was a {Role(message['role']).name}")
            elif self.partition not in [Partition.prevote, Partition.postvote] and message["type"] == STATE_SYNC["type"]:
                print("FATALERR: Received state change while not in prevote or postvote stage.")
            else:
                print("FATALERR: Received unknown message type:", message)
