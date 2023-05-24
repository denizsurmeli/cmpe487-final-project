import unittest


from house import House
from state import State, Player, Role, Partition
from communicator import Communicator

PLAYERS = [
    (0,0,"a", "villager"),
    (1,1,"b", "villager"),
    (2,2,"c", "villager"),
    (3,3,"d", "villager"),
    (4,4,"e", "villager"),
    (5,5,"f", "villager"),
    (6,6,"g", "villager"),
    (7,7,"h", "vampire"),
    (8,8,"i", "vampire"),
    (9,9,"j", "doctor"),
]

def tuple_to_player(player: tuple) -> dict:
    return {
        "ip": player[0],
        "id": player[1],
        "name": player[2],
        "role": player[3],
        "key": ""
    }

class TestState(unittest.TestCase):
    def setUp(self):
        self.state = State([Player(tuple_to_player(player)) for player in PLAYERS])


    def test_kill(self):
        self.state.change_state(Partition.night)
        self.state.kill(self.state.players[0])
        self.state.kill(self.state.players[1])

        self.state.change_state(Partition.day)
        self.state.kill(self.state.players[2])

        self.assertFalse(self.state.alive[self.state.players[0]])
        self.assertFalse(self.state.alive[self.state.players[1]])
        self.assertTrue(self.state.alive[self.state.players[2]])

    def test_protect(self):
        self.state.protect(self.state.players[0])
        self.state.change_state(Partition.night)
        self.state.kill(self.state.players[0])

        self.assertTrue(self.state.alive[self.state.players[0]])
        self.assertTrue(self.state.saved[self.state.players[0]])

    def test_is_over_vampire(self):
        # game is not over in this round
        self.state.change_state(Partition.night)
        self.state.kill(self.state.players[0])
        self.state.kill(self.state.players[1])

        self.state.change_state(Partition.day)
        self.state.kill(self.state.players[2])

        is_over, side = self.state.is_over()
        self.assertFalse(is_over)
        self.assertTrue(side == None)    


        # game is over in this round
        self.state.change_state(Partition.night)
        # kill all villagers except remain one
        for i in range(2, 6):
            self.state.kill(self.state.players[i])
        
        self.state.change_state(Partition.day)
        is_over, side = self.state.is_over()

        self.assertTrue(is_over)
        self.assertTrue(side == Role.vampire)

    def test_is_over_villager(self):
        # game is not over in this round
        self.state.change_state(Partition.night)
        self.state.kill(self.state.players[0])
        self.state.kill(self.state.players[1])

        self.state.change_state(Partition.day)
        self.state.kill(self.state.players[2])

        is_over, side = self.state.is_over()
        self.assertFalse(is_over)
        self.assertTrue(side == None)    

        # game is over in this round
        self.state.change_state(Partition.night)
        # kill all vampires except remain none
        for i in range(7, 9):
            self.state.kill(self.state.players[i])
        
        self.state.change_state(Partition.day)
        is_over, side = self.state.is_over()

        self.assertTrue(is_over)
        self.assertTrue(side == Role.villager)

    def test_cleanup(self):
        self.state.protect(self.state.players[0])

        self.state.change_state(Partition.night)
        self.state.kill(self.state.players[0])
        self.state.kill(self.state.players[1])
        self.state.kill(self.state.players[2])

        self.state.change_state(Partition.end_of_voting)
        dump = self.state.dump_state_change()
        self.state.round_cleanup()

        for i in range(3, 10):
            self.assertTrue(self.state.alive[self.state.players[i]])
        
        self.assertTrue(dump["saved"] == [self.state.players[0]])
        self.assertTrue(dump["killed"] == [self.state.players[1], self.state.players[2]])
        print(self.state.saved, self.state.killed)
        self.assertTrue(len(self.state.saved) == 0)
        self.assertTrue(len(self.state.killed) == 0)
        
        
if __name__ == '__main__':
    unittest.main()
    


        