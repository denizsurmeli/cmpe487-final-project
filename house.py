"""
Functionality for the voting mechanism. 
"""
import json
from communicator import Communicator
from state import State, Player, Role, Partition
import threading 
import time



VOTING_PERIOD = 60 # seconds

# Vote for a player
VOTE_MESSAGE = {
    "type": "vote",
    "id": "", # id of the player, empty if broadcast
    "medium": "", # whisper or broadcast
    "voter": "", # id of the voter
    "choice": "" # id of the choice
}

class Vote:
    def __init__(self, vote: dict):
        if vote["medium"] == "whisper":
            # TODO: Enrich the votes with the id of the voter, if the vote is a whisper
            self.id = vote["id"] # the id
            self.voter = vote["voter"] # who voted
            self.choice = vote["choice"] # for whom
            self.medium = vote["medium"]

        elif vote["medium"] == "broadcast":
            # if the vote is a broadcast, the id is the id of the voter
            self.voter = vote["voter"]
            self.id = vote["voter"]
            self.choice = vote["choice"]
            self.medium = vote["medium"]


class House:
    def __init__(self, communicator: Communicator, state: State):
        self.communicator = communicator
        self.state = state

        # update the parser on the communicator
        # TODO : Refactor this, add proper mechanism
        self.communicator.recv_parser_change(self.recv_parser)
        state.change_state(Partition.voting)

        self.started_at = time.time()
        self.open = True
        self.interval_lock = threading.Lock()

        alive_players = [player for player, state in state.alive.items() if state]

        # So, the logic is as follows:

        # We first make an intermediate board for the votes, where everyone votes and 
        # we keep track of the whispers and broadcasts.
        # If we see that there are some players who have voted for more than one people,
        # they might be mind controlled by the vampire, so we ask each peer about the whispers.
        # After listening the intermediate period, we finalize the votes by looking at the whispers and broadcasts
        # and make the final call for each peer. This updates the state to the final period of voting, 
        # the ones that need to be killed are killed etc. 

        # NOTE: The ip's are the the ip's of the **voters**
        self.whispers = {player.id: dict() for player in alive_players} # peer -> peer -> whom they have voted for(id)
        self.whispers_lock = threading.Lock()

        self.broadcasts = {player.id: list() for player in alive_players} # id -> [votes]
        self.broadcasts_lock = threading.Lock()

        self.has_voted = {player.id: False for player in alive_players} # id -> bool
        self.has_voted_lock = threading.Lock()

    def _vote(self, player: Player, vote: Player):
        message = VOTE_MESSAGE.copy()
        message["voter"] = player.id
        message["choice"] = vote.id
        message["medium"] = "broadcast"

        # update the client's state 
        with self.broadcasts_lock:
            self.broadcasts[player.id].append(vote.id)
        
        with self.has_voted_lock:
            self.has_voted[player.id] = True
            
        # broadcast the vote
        self.communicator.socket_send_all(message)

        message["medium"] = "whisper"
        self.process_vote(Vote(message))
        # whisper the vote to all 
        with self.communicator.persons_lock:
            for ip in self.communicator.persons.keys():
                if ip != player.ip:
                    self.communicator.socket_send(ip, message)
    

    def vote(self, executor:Player ,player: Player, vote: Player):
        with self.interval_lock, self.state.alive_lock:
            if vote not in self.state.alive.keys():
                print("ERROR: Player", vote.name, "is not alive.")
                return
        
            with self.has_voted_lock:
                if executor == player and self.has_voted[executor.id]:
                    print("ERROR: Player", executor.name, "has already voted.")
                    return

            if self.open and time.time() - self.started_at < VOTING_PERIOD:
                # vampire mind control case
                # NOTE: Executor information is only available for the player herself, so no information leak. 
                if executor.id != player.id and executor.role == Role.vampire:
                    message = VOTE_MESSAGE.copy()
                    message["voter"] = player.id
                    message["choice"] = vote.id
                    message["medium"] = "broadcast"
                    self.communicator.socket_send_all(message)

                    with self.broadcasts_lock:
                        self.broadcasts[player.id].append(vote.id)
                    
                    with self.has_voted_lock:
                        self.has_voted[player.id] = True
                # plain voting case
                elif executor.id == player.id:
                    self._vote(player, vote)
                else:
                    # TODO: This is for debugging purposes, remove later.
                    print("ERROR: Player", executor.name, "tried to vote for", player.name, "but is not a vampire.")
            else:
                print("ERROR: Voting period is over for this round.")
                # lock the vote state
                self.open = False
                return 
            
            # voters = [player for player, state in self.state.alive.items() if state]
            # voted = [id for id in self.broadcasts.keys() if len(self.broadcasts[id]) > 0]
            # # if voting period has passed or everyone has voted, lock the state and finalize the table
            # if len(voted) == len(voters):
            #     print("INFO: Everyone has voted, finalizing the table.")
            #     self.open = False

    def id_to_player(self, id: str):
        for player in self.state.players:
            if player.id == id:
                return player

    def process_vote(self, vote: Vote):
        if vote.medium == "broadcast":
            with self.broadcasts_lock:
                self.broadcasts[vote.voter].append(vote.choice)
        elif vote.medium == "whisper":
            with self.whispers_lock:
                # TODO: This should never happen
                if vote.voter not in self.whispers.keys():
                    self.whispers[vote.voter] = dict()
                self.whispers[vote.voter][vote.choice] = self.whispers[vote.voter].get(vote.choice, 0) + 1
        else:
            # TODO: This if for debugging purposes, remove later.
            print("ERROR: Unknown medium for vote:", vote.medium)

    def finalize_table(self):
        # finalize the votes. End of the partition, count the whispers and broadcasts
        # to make the final call for each peers vote

        # Strategy as follows:
        # If there are more than one broadcast for one peer, first, decide for that peer about the vote
        
        # NOTE: The ip's are number of votes **for that** ip.
        final_votes = dict() # ip -> vote

        # first determine who voted for who actually
        for id, votes in self.broadcasts.items():
            if len(votes) > 1:
                # there are two broadcast votes, go look at the whispers
                try:
                    final_votes[id] = max(self.whispers[id], key=self.whispers[id].get)
                except Exception as e:
                    # then this vote is by the vampire, so we can't see the whispers
                    final_votes[id] = votes[0]
            elif len(votes) == 1:
                final_votes[id] = votes[0]
            else:
                print(f"No votes casted this round for player with id: {id}.")

        if len(final_votes) == 0:
            print("ERROR: No votes casted this round for anyone.")
            return
        aggregated_result = dict() # vote -> count
        for vote in final_votes.values():
            aggregated_result[vote] = aggregated_result.get(vote, 0) + 1
        # The table is finalized, we select the candidates who will get killed.
        max_count = max(aggregated_result.values())
        candidates = [id for id, count in aggregated_result.items() if count == max_count]

        if len(candidates) <= 1:
            with self.state.killed_lock:
                id = candidates[0]
                player = self.id_to_player(id)
                self.state.alive[player] = False
                self.state.killed[player] = True
        else:
            print("ERROR: There are more than one candidates for killing. This round will be skipped with no effects.")

    def is_open(self):
        # Check if the voting is still open
        if time.time() - self.started_at > VOTING_PERIOD:
            with self.interval_lock:
                self.open = False
            self.state.change_state(Partition.postvote)
        return self.open

    def recv_parser(self, message: str, ip: str):
        # NOTE: While sending messages, you give dictionaries, but while receiving, you get json strings.
        # parse the message and update the state accordingly
        # TODO: Add messaging support maybe ? 
        try:
            message = json.loads(message)
        except:
            print("ERROR: Could not parse the message:", message)
            return
       
        if message["type"] == "vote":
            print(message)
            vote = Vote(message)
            self.process_vote(vote)
        else:
            print("ERROR: Unknown message type for parser attached in <house.py>:", message["type"])

                    







        


