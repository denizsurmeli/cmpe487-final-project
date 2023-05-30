import threading
import time

from communicator import Communicator
from state import State, Partition, Player, Role, id_to_player
from house import House, Vote
from utility import build_id, recv_parser, GROUP_CHAT_MESSAGE, PRIVATE_CHAT_MESSAGE 

# couple with functions to be called
COMMANDS = {
    "send_all":None,
    "send":None,
    "vote":None,
    "kill":None,
    "protect":None,
}

DAY_PERIOD = 30 # seconds
NIGHT_PERIOD = 10 # seconds
VOTING_PERIOD = 30 # seconds


CATCHUP_PERIOD = 3 # seconds

class Game:
    def __init__(self, client: Player, communicator: Communicator, state:State, clock:float):
        self.client = client
        self.communicator = communicator
        self.state = state
        self.clock = clock

        self.house = None
        self.house_lock = threading.Lock()

        # bind methods to commands
        self.commands = COMMANDS.copy()
        self.commands["send_all"] = self.send_all
        self.commands["send"] = self.send
        self.commands["vote"] = self.vote
        self.commands["kill"] = self.kill
        self.commands["protect"] = self.protect

        self.user_listener = threading.Thread(target=self.listen_user).start()
        self.runner = threading.Thread(target=self.run).start()


    def run(self):
        print("Game started")
        while self.state.is_over()[0] != True:
            print("Round: ", self.state.round)
            # always starts with day
            print("Day started")
            day_point = time.time()
            # in the beginnig, parser is set to default.
            self.communicator.recv_parser_change(lambda message, ip:recv_parser(self=self.communicator, message=message, ip=ip))
            while time.time() - day_point < DAY_PERIOD:
                # Do nothing, let people chat
                continue
            print("Day over")

            print("Night started")
            # change the state to night
            self.state.change_state(Partition.night)
            night_point = time.time()
            while time.time() - night_point < NIGHT_PERIOD:
                # Do nothing, let vampires kill
                continue
            print("Night over")

            print("Prevote started")
            # prevote
            self.state.change_state(Partition.prevote)
            self.communicator.recv_parser_change(self.state.recv_parser)
            # distribute delta among peers 
            state_delta = self.state.dump_delta()
            self.communicator.socket_send_all(state_delta)

            # let all peers catchup
            print("Waiting for peers to catch up...")
            time.sleep(CATCHUP_PERIOD)
            print("Done")
            print("Prevote over")
            self.state.sync_delta()

            print("Voting started")
            # voting
            self.state.change_state(Partition.voting)
            voting_point = time.time()
            house = House(self.communicator, self.state)
            with self.house_lock:
                self.house = house
            self.communicator.recv_parser_change(house.recv_parser)
            while time.time() - voting_point < VOTING_PERIOD:
                # Do nothing, let people vote
                pass
            
            print("Voting over")
            house.finalize_table()

            print("Postvote started")
            # resync state
            self.state.change_state(Partition.postvote)
            self.communicator.recv_parser_change(self.state.recv_parser)
            # distribute delta among peers
            state_delta = self.state.dump_delta()
            self.communicator.socket_send_all(state_delta)

            # let all peers catchup
            print("Waiting for peers to catch up...")
            time.sleep(CATCHUP_PERIOD)
            print("Done")
            print("Postvote over")

            self.state.sync_delta()

            print("Round over")
            with self.house_lock:
                self.house = None

            self.state.round_cleanup()
        # if we are out of the loop, game is over
        _, result = self.state.is_over()
        if result == Role.vampire:
            print("Vampires won!")
        else:
            print("Villagers won!")


    def listen_user(self):
        ### listens the inputs from the user
        # What can user do?
            # 1. Group chat
            # 2. Whisper
            # 3. Vote
            # 4. Kill
            # 5. Protect
        while True:
            prompt = input(">>> ")
            command = prompt.split()[0]
            if command not in COMMANDS:
                print("Invalid command.")
                continue
            else:
                self.commands[command](prompt)

    def send_all(self, prompt):
        ### sends a message to all players
        with self.state.alive_lock, self.state.partition_lock:
            if self.state.alive[self.client] == False:
                print("You are dead. You can't communicate with others.")
                return
            if self.state.partition == Partition.day or self.state.partition == Partition.voting:
                # content
                payload = GROUP_CHAT_MESSAGE.copy()
                message = " ".join(prompt.split(" ")[1:])
                payload["content"] = message
                self.communicator.socket_send_all(payload)
            else:
                print("You can't send a message now")


    def send(self, prompt):
        ### sends a message to a specific player
        with self.state.alive_lock, self.state.partition_lock:
            if self.state.alive[self.client] == False:
                print("You are dead. You can't communicate with others.")
                return
            if self.state.partition == Partition.day or self.state.partition == Partition.voting:
                # content
                payload = PRIVATE_CHAT_MESSAGE.copy()
                target = prompt.split(" ")[1].strip()
                message = " ".join(prompt.split(" ")[2:])
                payload["content"] = message
                # resolve to ip
                target = self.communicator.ips[target]
                self.communicator.socket_send(target, payload)
            else:
                print("You can't send a message now")

    def vote(self, prompt):
        ### votes a player
        ## vote <player_name>
        with self.state.alive_lock, self.state.partition_lock:
            if self.state.partition != Partition.voting:
                print("You can't vote now")
                return
            if self.state.alive[self.client] == False:
                print("You are dead. You can't vote.")
                return
        params = prompt.split(" ")
        if len(params) == 2: # naive vote
            target_name = prompt.split(" ")[1].strip()
            target_ip = self.communicator.ips[target_name]
            
            target_id = build_id(target_ip, target_name)
            target = id_to_player(target_id, self.state.players)

            if target == None:
                print("Invalid target")
                return
            else:
                with self.house_lock:
                    if self.house != None:
                        self.house.vote(self.client, self.client, target)
        if len(params) == 3: # vampire attempt
            # vote <manipulated_players_name> <vote>
            target_name = prompt.split(" ")[2]
            target_ip = self.communicator.ips[target_name]
            
            target_id = build_id(target_ip, target_name)
            target = id_to_player(target_id, self.state.players)

            if target == None:
                print("Invalid target")
                return
        
            manipulated_name = prompt.split(" ")[1].strip()
            manipulated_ip = self.communicator.ips[manipulated_name]

            manipulated_id = build_id(manipulated_ip, manipulated_name)
            manipulated = id_to_player(manipulated_id, self.state.players)

            if manipulated == None:
                print("Invalid target")
                return
            else:
                with self.house_lock:
                    if self.house != None:
                        self.house.vote(self.client, manipulated, target)
        
    def kill(self, prompt):
        ### kills a player
        ## kill <player_name>
        with self.state.alive_lock, self.state.partition_lock:
            # conditions
            if self.state.partition != Partition.night:
                print("You can't kill now")
                return
            if self.state.alive[self.client] == False:
                print("You are dead. You can't kill.")
                return
            if self.client.role != Role.vampire:
                print("You are not a vampire. You can't kill.")
                return
            
        target_name = prompt.split(" ")[1].strip()
        target_ip = self.communicator.ips[target_name]
        
        target_id = build_id(target_ip, target_name)
        target = id_to_player(target_id, self.state.players)

        if target == None:
            print("Invalid target")
            return
        else:
            self.state.kill(target)

    def protect(self, prompt):
        ### protects a player
        ## protect <player_name>
        with self.state.alive_lock, self.state.partition_lock:
            # conditions
            if self.state.partition != Partition.day:
                print("You can't protect now")
                return
            if self.state.alive[self.client] == False:
                print("You are dead. You can't protect.")
                return
            if self.client.role != Role.doctor:
                print("You are not a doctor. You can't protect.")
                return
            
        target_name = prompt.split(" ")[1].strip()
        target_ip = self.communicator.ips[target_name]
        
        target_id = build_id(target_ip, target_name)
        target = id_to_player(target_id, self.state.players)

        if target == None:
            print("Invalid target")
            return
        else:
            self.state.protect(target)
            


