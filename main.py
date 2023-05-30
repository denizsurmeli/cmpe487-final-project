import os
import time
from communicator import Communicator
from initializer import Initializer
from state import State, Player, pair_to_player, parse_role
from utility import client_setup
from game import Game


if __name__ == "__main__":
    ip, name = client_setup()
    comm :Communicator = Communicator(ip, name)

    # glock is the global clock distributed among all players
    role, clock = Initializer(comm).information(), time.time()
    # TODO: @artun-akdogan: return clock, villager count etc as in here
    counts = (2,1,1)
    # set client herself
    client = Player({"ip": ip, "name": name, "role": role})
    print(client.role)

    players = [pair_to_player(ip,player) for ip, player in comm.dump_addressbook().items()]
    players.append(client)
    
    state = State(players, client, comm, counts)
    game = Game(client, comm, state, clock)

    # game.run()


