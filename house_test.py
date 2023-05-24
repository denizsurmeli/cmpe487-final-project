import unittest


from house import House
from state import State, Player, Role, Partition
from communicator import Communicator

PLAYERS = [
    (0,0,"a", Role.villager),
    (1,1,"b", Role.villager),
    (2,2,"c", Role.villager),
    (3,3,"d", Role.villager),
    (4,4,"e", Role.villager),
    (5,5,"f", Role.villager),
    (6,6,"g", Role.villager),
    (7,7,"h", Role.vampire),
    (8,8,"i", Role.vampire),
    (9,9,"j", Role.doctor),
]

def tuple_to_player(player: tuple) -> dict:
    return {
        "ip": player[0],
        "id": player[1],
        "name": player[2],
        "role": player[3],
        "key": ""
    }


class MockCommunicator:
    def __init__(self):
        self.message_count = 0
    
    def socket_send_all(self, message: dict):
        self.message_count += 1
        return

    def socket_send(self):
        return self.messages.pop(0)

class TestHouse(unittest.TestCase):
    def setUp(self):
        self.state = State([Player(tuple_to_player(player)) for player in PLAYERS])
        self.communicator = Communicator()
        self.house = House(self.state, self.communicator)        


