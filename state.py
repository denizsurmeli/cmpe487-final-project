"""
Definitions and functionalities of the roles, the game state etc.
"""

import threading
import enum

class Role(enum.Enum):
    vampire = 1
    doctor = 2
    villager = 3

class Partition(enum.Enum):
    day = 1
    night = 2
    voting = 3
    end = 4

class Player: 
    def __init__(self, data: dict):
        self.ip = data["ip"]
        self.id = data["id"] # TODO: Maybe we won't need this, wrapping up just in case. 
        self.name = data["name"]
        self.role = data["role"]
        self.key = data["key"]
    


class State:
    def __init__(self, players: list[Player]):
        self.players = players # we don't drop the players from the list even though they are alive or not
        self.round :int = 1
        self.partition :Partition = Partition.day
        self.partition_lock = threading.Lock()

        # This map is persistent, others are renewed every round.
        self.is_alive = dict()
        self.is_alive_lock = threading.Lock()

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
        with self.killed_lock, self.protected_lock, self.is_alive_lock:
            if player not in self.protected:
                self.killed[player] = True
                self.is_alive[player] = False
                self.save(player)
    
    def save(self, player):
        with self.saved_lock:
            self.saved[player] = True

    def protect(self, player):
        with self.protected_lock:
            self.protected[player] = True

    def is_over(self):
        # if the number of alive people <= number of alive vampires, vampires win
        with self.is_alive_lock:
            alive_people_count = len([player for player, state in self.is_alive.items() if state and player.role != Role.vampire])
            alive_vampire_count = len([player for player, state in self.is_alive.items() if state and player.role == Role.vampire])

        if alive_people_count <= alive_vampire_count:
            return (True, Role.vampire)
        elif alive_vampire_count == 0:
            return (True, Role.villager)
        else:
            return (False, None)
        
    def round_cleanup(self):
        with self.killed_lock:
            self.killed = dict()
        with self.saved_lock:
            self.saved = dict()
        self.round += 1
        self.change_state(Partition.day)
        
        
        



