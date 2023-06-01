import os
import time
from datetime import datetime
from communicator import Communicator
from initializer import Initializer
from state import State, Player, pair_to_player, parse_role
from utility import client_setup
from game import Game


if __name__ == "__main__":
    ip, name = client_setup()
    comm :Communicator = Communicator(ip, name)

    # glock is the global clock distributed among all players
    role, counts = Initializer(comm).information()
    clock = time.time()
    print("Game started at:", datetime.fromtimestamp(clock), "with", counts[0], "villagers", counts[1], "vampires, and", counts[2], "doctors.")
    # set client herself
    client = Player({"ip": ip, "name": name, "role": role})
    print(client.role)

    players = [pair_to_player(ip,player) for ip, player in comm.dump_addressbook().items()]
    players.append(client)
    
    state = State(players, client, comm, counts)
    game = Game(client, comm, state, clock)
    game.run()
