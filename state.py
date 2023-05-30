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

VAMPIRE_ACK = {
    "type": "vampire_ack",
    "id": None
}

class Role(enum.Enum):
    vampire = 1
    doctor = 2
    villager = 3

class Partition(enum.Enum):
    day = 1
    night = 2
    prevote = 3
    voting = 4
    postvote = 5
    end = 6

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
        self.captured_vampire_count_lock = threading.Lock()

    def change_state(self, partition: Partition):
        with self.partition_lock:
            self.partition = partition

    def sync_delta(self):
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
    
    def kill(self, player:Player):
        if self.partition == Partition.night:
            with self.killed_lock, self.protected_lock, self.alive_lock:
                if player == self.client and player.role == Role.vampire:
                    # vampire is captured
                    payload = VAMPIRE_ACK.copy()
                    payload["id"] = player.id
                    self.communicator.send_to_all(payload)
                if player not in self.protected.keys():
                    print(f"Player {player.id} is killed by the vampire.")
                    self.killed[player] = True
                    self.alive[player] = False
                else:
                    print(f"Player {player.id} is protected by the doctor.")
                    self.save(player)
    
    def save(self, player):
        with self.saved_lock:
            self.saved[player] = True

    def protect(self, player:Player):
        if self.partition == Partition.day:
            with self.protected_lock:
                self.protected[player] = True

    def is_over(self):
        # if the number of alive people <= number of alive vampires, vampires win
        with self.alive_lock:
            alive_player_count = len([player for player,state in self.alive.items() if state])
            print("Alive player count: ", alive_player_count) 
        if self.captured_vampire_count == self.vampire_count:
            # all vampires have been caught
            return (True, Role.villager)
        if alive_player_count <= self.vampire_count - self.captured_vampire_count:
            # vampires dominate the village, no chance for villagers to win
            return (True, Role.vampire)
        return (False, None)
                         
        
    def round_cleanup(self):
        # Only when voting period ends
        if self.partition == Partition.postvote:
            with self.killed_lock, self.saved_lock, self.protected_lock, self.delta_lock:
                self.killed = dict()
                self.saved = dict()
                self.protected = dict()
                self.delta = {"killed":[], "saved":[], "protected":[]}
            # if game is over, change the state to end else rewind to a new round
            if self.is_over()[0]:
                self.change_state(Partition.end)
            else:
                self.change_state(Partition.day)
                self.round += 1

    def dump_delta(self):
        # If the game is in prevoting stage, show who have been killed and saved last night.
        if self.partition == Partition.prevote or self.partition == Partition.postvote:
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
        except:
            print("FATALERR: Error while unmarshalling the message.")

        with self.partition_lock,self.delta_lock, self.captured_vampire_count_lock:
            if self.partition in [Partition.prevote, Partition.postvote] and message["type"] == STATE_SYNC["type"]:
                    self.delta["killed"].append(message["killed"])
                    self.delta["saved"].append(message["saved"])
            elif self.partition == Partition.pastvote and message["type"] == VAMPIRE_ACK["type"]:
                with self.captured_vampire_count_lock:
                    self.captured_vampire_count_lock += 1
                    self.kill(id_to_player(message["id"]))
            elif self.partition not in [Partition.prevote, Partition.postvote] and message["type"] == STATE_SYNC["type"]:
                print("FATALERR: Received state change while not in prevote or postvote stage.")


            else:
                print("FATALERR: Received unknown message type.")
