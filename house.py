"""
Functionality for the voting mechanism. 
"""
from communicator import Communicator
from state import State, Player, Role, Partition
import threading 

# TODO: update parser in the communicator to parse the vote message
VOTE_MESSAGE = {
    "type": "vote",
    "medium": "", # whisper or broadcast
    "voter": "",
    "choice": ""
}

ASK_MESSAGE = {
    "type": "ask_vote",
    "voter": "",
}

class Vote:
    def __init__(self, vote: dict):
        # TODO: Enrich the votes with the ip of the voter, if the vote is a whisper
        self.ip = vote["ip"]
        self.voter = vote["voter"]
        self.choice = vote["choice"]
        self.medium = vote["medium"]

class House:
    def __init__(self, communicator: Communicator, state: State):
        self.communicator = communicator
        self.state = state

        alive_players = [player for player, state in state.is_alive.items() if state]
        self.board = {player.ip: dict() for player in alive_players} # ip -> votes -> whisper_count, broadcast_count
        self.board_lock = threading.Lock()

        self.final_board = {player.ip: 0 for player in alive_players} # ip -> vote
        self.final_board_lock = threading.Lock()

    def _vote(self, player: Player, vote: Player):
        message = VOTE_MESSAGE.copy()
        message["voter"] = player.name
        message["choice"] = vote.name
        message["medium"] = "broadcast"

    
        self.state.vote(player, vote)
        # broadcast the vote
        self.communicator.send_to_all(VOTE_MESSAGE)

        message["medium"] = "whisper"
        # whisper the vote to all 
        with self.communicator.persons_lock:
            for ip in self.communicator.persons.keys():
                if ip != player.ip:
                    self.communicator.socket_send(ip, message)

    def vote(self, executor:Player ,player: Player, vote: Player):
        if executor.ip != player.ip and executor.role == Role.vampire:
            # vampire mind control
            message = VOTE_MESSAGE.copy()
            message["voter"] = player.name
            message["choice"] = vote.name
            message["medium"] = "broadcast"
            self.communicator.send_to_all(message)
        else:
            self._vote(player, vote)

    def process_vote(self, vote: Vote):
        with self.board_lock:
            if vote.choice not in self.board[vote.ip].keys():
                self.board[vote.ip][vote.choice] = [0,1] if vote.medium == "broadcast" else [1,0]
            else:
                self.board[vote.ip][vote.choice][1 if vote.medium == "broadcast" else 0] += 1


    def finalize_table(self):
        # finalize the votes. End of the partition, count the whispers and broadcasts
        # to make the final call for each peers vote
        # TODO: implement
                    







        


