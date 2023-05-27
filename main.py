import os
import time
from communicator import Communicator
from initializer import Initializer
from state import State, Player, pair_to_player
from utility import client_setup
from game import Game


if __name__ == "__main__":
    ip, name = client_setup()
    comm :Communicator = Communicator(ip, name)

    # glock is the global clock distributed among all players
    role, clock = Initializer(comm).information(), time.time()
    
    # set client herself
    client = Player({"ip": name, "name": name, "role": role})

    players = [pair_to_player(player,ip) for ip, player in comm.dump_addressbook().items()]
    players.append(client)
    
    state = State(players)
    game = Game(client, comm, state, clock)

    game.run()


