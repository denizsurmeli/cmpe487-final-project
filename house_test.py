import unittest
import threading

from house import House, Vote
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

def pair_to_vote(player: Player, vote: Player, medium: str) -> dict:
    return {
        "type":"vote",
        "id": player.id,
        "voter": player.id,
        "choice": vote.id,
        "medium": medium
    }

### THIS CLASS IS FOR TESTING PURPOSES ONLY
class MockCommunicator:
    def __init__(self,ip, name, address_list = [Player]):
        self.persons = {player.id:player.name for player in address_list}
        self.persons_lock = threading.Lock() # since the interface obeys this, we put a mock lock 
        self.message_count = 0
    
    def socket_send_all(self, message: dict):
        self.message_count += 1
        return

    def socket_send(self,ip:str,  message: dict):
        self.message_count += 1
        return


class TestHouse(unittest.TestCase):
    def setUp(self):
        players = [Player(tuple_to_player(player)) for player in PLAYERS]
        self.state = State(players)
        self.communicator = MockCommunicator("0", "0", players)
        self.house = House(self.communicator, self.state)        

    def test_simple_vote(self):
        executor = self.state.players[0]
        player = self.state.players[0]
        vote = self.state.players[1]

        self.house.vote(executor, player, vote)
        self.house.process_vote(Vote(pair_to_vote(player, vote, "whisper")))

        self.assertTrue(vote.id in self.house.broadcasts[player.id])
        self.assertEqual(self.house.whispers[player.id][vote.id], 1)

    def test_vampire_vote(self):
        executor = self.state.players[8]
        player = self.state.players[0]
        vote = self.state.players[1]

        self.house.vote(executor, player, vote)
        self.assertTrue(vote.id in self.house.broadcasts[player.id])

    def test_process_whisper_vote(self):
        player = Player(tuple_to_player(PLAYERS[0]))
        vote = Player(tuple_to_player(PLAYERS[1]))
        vote = Vote({
            "type":"vote",
            "id": player.id,
            "voter": player.id,
            "choice": vote.id,
            "medium": "whisper"
        })
        self.house.process_vote(vote)
        self.assertEqual(self.house.whispers[player.id][vote.choice], 1)
    

    def test_process_broadcast_vote(self):
        player = Player(tuple_to_player(PLAYERS[0]))
        vote = Player(tuple_to_player(PLAYERS[1]))
        vote = Vote({
            "type":"vote",
            "id": player.id,
            "voter": player.id,
            "choice": vote.id,
            "medium": "broadcast"
        })
        self.house.process_vote(vote)
        self.assertTrue(vote.choice in self.house.broadcasts[player.id])

    def test_simple_round(self):
        # SETUP:
        ## We have 10 players, 2 vampires, 1 doctor, 7 villagers.
        ## The vampires are players 7 and 8, the doctor is player 9.
        ## Everyone will vote for player 0, except for player 9 and player 0, who will vote for player 1.
        majority = [i for i in range(1,9)]
        minority = [0, 9]
        
        for i in majority:
            executor = self.state.players[i]
            player = self.state.players[i]
            vote = self.state.players[0]


            self.house.vote(executor, player, vote)
            # mock the whisper
            for peer in self.state.players:
                if peer.id != executor.id:
                    self.house.process_vote(Vote(pair_to_vote(player, vote, "whisper")))

        for i in minority:
            print(i)
            executor = self.state.players[i]
            player = self.state.players[i]
            vote = self.state.players[1]
        
            self.house.vote(executor, player, vote)
            # mock the whisper
            for peer in self.state.players:
                if peer.id != executor.id:
                    self.house.process_vote(Vote(pair_to_vote(player, vote, "whisper")))
        
        # everyone has voted, so we should be able to close the house
        # is_open = self.house.is_open()
        # self.assertFalse(is_open)

        # now we should be able to process the votes
        self.house.finalize_table()

        # expect that player[0] is dead, and everyone else is alive
        for i in range(1, 10):
            player = self.state.players[i]
            self.assertTrue(self.state.alive[player], f"Player {player.id} is dead, but should be alive")
        
        player = self.state.players[0]
        self.assertFalse(self.state.alive[player])

    def test_tie_round(self):
        # SETUP:
        ## We have 10 players, 2 vampires, 1 doctor, 7 villagers.
        ## The vampires are players 7 and 8, the doctor is player 9.
        ## Four players will vote for player 0, four players will vote for player 1, and two players will vote for player 2.
        p0_voters = [i for i in range(1,5)]
        p1_voters = [i for i in range(5,9)]
        p2_voters = [0, 9]
        actions = [(0,p0_voters), (1,p1_voters), (2,p2_voters)]

        for pair in actions:
            k = pair[0]
            votelist = pair[1]
            for i in votelist:
                executor = self.state.players[i]
                player = self.state.players[i]
                vote = self.state.players[k]


                self.house.vote(executor, player, vote)
                # mock the whisper
                for peer in self.state.players:
                    if peer.id != executor.id:
                        self.house.process_vote(Vote(pair_to_vote(player, vote, "whisper")))
        
        # everyone has voted, so we should be able to close the house
        # is_open = self.house.is_open()
        # self.assertFalse(is_open)

        # now we should be able to process the votes
        self.house.finalize_table()

        # expect that player[0],player[1] is dead, and everyone else is alive
        for i in range(2, 10):
            player = self.state.players[i]
            self.assertTrue(self.state.alive[player], f"Player {player.id} is dead, but should be alive")
        
        player = self.state.players[0]
        self.assertFalse(self.state.alive[player])

        player = self.state.players[1]
        self.assertFalse(self.state.alive[player])

    def test_vampire_round(self):
        # SETUP:
        ## We have 10 players, 2 vampires, 1 doctor, 7 villagers.
        ## The vampires are players 7 and 8, the doctor is player 9. 
        ## Everyone will vote for player 0, except for player 9 and player 0, who will vote for player 1.
        ## The player 9 is vampire, so he will broadcast a vote for player 1 too, and broadcast a vote for player 2.

        majority = [i for i in range(1,9)]
        minority = [0, 9]

        for i in majority:
            executor = self.state.players[i]
            player = self.state.players[i]
            vote = self.state.players[0]


            self.house.vote(executor, player, vote)
            # mock the whisper
            for peer in self.state.players:
                if peer.id != executor.id:
                    self.house.process_vote(Vote(pair_to_vote(player, vote, "whisper")))
            
        for i in minority:
            executor = self.state.players[i]
            player = self.state.players[i]
            vote = self.state.players[1]
        
            self.house.vote(executor, player, vote)
            # mock the whisper
            for peer in self.state.players:
                if peer.id != executor.id:
                    self.house.process_vote(Vote(pair_to_vote(player, vote, "whisper")))
        
        executor = self.state.players[8]
        player = self.state.players[1]
        vote = self.state.players[2]

        self.house.vote(executor, player, vote)

        self.house.finalize_table()

        # expect that player[0] is dead, and everyone else is alive
        for i in range(1, 10):
            player = self.state.players[i]
            self.assertTrue(self.state.alive[player], f"Player {player.id} is dead, but should be alive")
        
        player = self.state.players[0]
        self.assertFalse(self.state.alive[player])





                

        

        






if __name__ == "__main__":
    unittest.main()


    

