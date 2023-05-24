"""
Functionality for the voting mechanism. 
"""
from communicator import Communicator
from state import State, Player, Role, Partition
import threading 
import time



VOTING_PERIOD = 60 # seconds

# TODO: update parser in the communicator to parse the vote message

# Vote for a player
VOTE_MESSAGE = {
    "type": "vote",
    "medium": "", # whisper or broadcast
    "voter": "",
    "choice": ""
}

# Ask the peer for who voter voted for
ASK_MESSAGE = {
    "type": "ask_vote",
    "voter": "",
}

# Respond to peer about who voter voted for
RESPOND_MESSAGE = {
    "type": "respond_vote",
    "voter": "",
    "choice": ""
}

class Vote:
    def __init__(self, vote: dict):
        # TODO: Enrich the votes with the ip of the voter, if the vote is a whisper
        self.ip = vote["ip"] # the ip
        self.voter = vote["voter"] # who voted
        self.choice = vote["choice"] # for whom
        self.medium = vote["medium"]

class House:
    def __init__(self, communicator: Communicator, state: State):
        self.communicator = communicator
        self.state = state

        state.change_state(Partition.voting)
        self.started_at = time.time()

        alive_players = [player for player, state in state.is_alive.items() if state]

        # So, the logic is as follows:

        # We first make an intermediate board for the votes, where everyone votes and 
        # we keep track of the whispers and broadcasts.
        # If we see that there are some players who have voted for more than one people,
        # they might be mind controlled by the vampire, so we ask each peer about the whispers.
        # After listening the intermediate period, we finalize the votes by looking at the whispers and broadcasts
        # and make the final call for each peer. This updates the state to the final period of voting, 
        # the ones that need to be killed are killed etc. 
        self.whispers = {player.ip: dict() for player in alive_players} # ip -> votes -> whisper_count
        self.whispers_lock = threading.Lock()

        self.broadcasts = {player.ip: dict() for player in alive_players} # ip -> votes -> broadcast_count
        self.broadcasts_lock = threading.Lock()



    def _vote(self, player: Player, vote: Player):
        message = VOTE_MESSAGE.copy()
        message["voter"] = player.name
        message["choice"] = vote.name
        message["medium"] = "broadcast"

        # broadcast the vote
        self.communicator.socket_send_all(VOTE_MESSAGE)

        message["medium"] = "whisper"
        # whisper the vote to all 
        with self.communicator.persons_lock:
            for ip in self.communicator.persons.keys():
                if ip != player.ip:
                    self.communicator.socket_send(ip, message)

    def vote(self, executor:Player ,player: Player, vote: Player):
        if executor.ip != player.ip and executor.role == Role.vampire:
            # vampire mind control case
            message = VOTE_MESSAGE.copy()
            message["voter"] = player.name
            message["choice"] = vote.name
            message["medium"] = "broadcast"
            self.communicator.socket_send_all(message)
        elif executor.ip == player.ip:
            self._vote(player, vote)
        else:
            # TODO: This is for debugging purposes, remove later.
            print("ERROR: Player", executor.name, "tried to vote for", player.name, "but is not a vampire.")

    def process_vote(self, vote: Vote):
        if vote.medium == "broadcast":
            with self.broadcasts_lock:
                self.broadcasts[vote.ip][vote.choice] = self.broadcasts[vote.ip].get(vote.choice, 0) + 1
                if len(self.broadcasts[vote.ip].keys()) > 1:
                    # ask peers about what's happening
                    message = ASK_MESSAGE.copy()
                    message["voter"] = vote.voter
                    self.communicator.socket_send_all(message)
            
        elif vote.medium == "whisper":
            with self.whispers_lock:
                self.whispers[vote.ip][vote.choice] = self.whispers[vote.ip].get(vote.choice, 0) + 1
        else:
            # TODO: This if for debugging purposes, remove later.
            print("ERROR: Unknown medium for vote:", vote.medium)

    def finalize_table(self):
        # finalize the votes. End of the partition, count the whispers and broadcasts
        # to make the final call for each peers vote

        # Strategy as follows:
        # If there are more than one broadcast for one peer, first, decide for that peer about the vote
        final_votes = dict() # ip -> vote
        with self.broadcasts_lock:
            for ip, votes in self.broadcasts.items():
                if len(votes.keys()) == 1:
                    final_votes[ip] = list(votes.keys())[0]
                else:
                    with self.whispers_lock:
                        table = dict()
                        for vote, count in self.whispers[ip].items():
                            table[vote] = table.get(vote, 0) + count
                        final_votes[ip] = max(table, key=table.get) 

        # The table is finalized, we select the candidates who will get killed.
        max_count = max(final_votes.values())
        candidates = [ip for ip, count in final_votes.items() if count == max_count]

        # TODO: Discuss about the case where there are more than one candidate
        # if len(candidates) > 1:
        #     alive_players = [player for player, state in self.state.is_alive.items() if state]

        # update the state
        with self.state.is_alive_lock, self.state.killed_lock:
            for ip in candidates:
                self.state.is_alive[ip] = False
                self.state.killed[ip] = True
    


                    







        


