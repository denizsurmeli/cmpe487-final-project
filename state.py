"""
Definitions and functionalities of the roles, the game state etc.
"""

import threading
import enum
from utility import parse_role, build_id

class Role(enum.Enum):
    vampire = 1
    doctor = 2
    villager = 3

class Partition(enum.Enum):
    day = 1
    night = 2
    voting = 3
    end_of_voting = 4
    end = 5

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
        # TODO: Do we need to remove these ?
        if "role" in data.keys():
            self.role = parse_role(data["role"])
        else:
            self.role = None

    def __eq__(self, other):
        return self.ip == other.ip and self.id == other.id
    
    def __hash__(self):
        return hash((self.ip, self.id))
    
    def __str__(self):
        return f"Player {self.name} ({self.ip}:{self.id})"
    


class State:
    def __init__(self, players: list[Player]):
        self.players = players # we don't drop the players from the list even though they are alive or not
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

    def change_state(self, partition):
        with self.partition_lock:
            self.partition = partition
    
    def kill(self, player):
        if self.partition == Partition.night:
            with self.killed_lock, self.protected_lock, self.alive_lock:
                if player not in self.protected.keys():
                    self.killed[player] = True
                    self.alive[player] = False
                else:
                    self.save(player)
    
    def save(self, player):
        with self.saved_lock:
            self.saved[player] = True

    def protect(self, player):
        if self.partition == Partition.day:
            with self.protected_lock:
                self.protected[player] = True

    def is_over(self):
        # if the number of alive people <= number of alive vampires, vampires win
        with self.alive_lock:
            alive_people_count = len([player for player, state in self.alive.items() if (state and player.role != Role.vampire)])
            alive_vampire_count = len([player for player, state in self.alive.items() if state]) - alive_people_count
        if alive_people_count <= alive_vampire_count:
            return (True, Role.vampire)
        elif alive_vampire_count == 0:
            return (True, Role.villager)
        else:
            return (False, None)
        
    def round_cleanup(self):
        # Only when voting period ends
        if self.partition == Partition.end_of_voting:
            with self.killed_lock:
                self.killed = dict()
            with self.saved_lock:
                self.saved = dict()
            # if game is over, change the state to end else rewind to a new round
            if self.is_over()[0]:
                self.change_state(Partition.end)
            else:
                self.change_state(Partition.day)
                self.round += 1

    def dump_state_change(self):
        # If the game in voting stage, show who killed an saved last night.
        if self.partition == Partition.voting:
            with self.killed_lock, self.saved_lock:
                dump = {
                    "killed": [player for player,state in self.killed.items() if state],
                    "saved": [player for player,state in self.saved.items() if state]
                }
            return dump
        
        



