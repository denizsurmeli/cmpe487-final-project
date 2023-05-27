# CMPE487-Final-Project (Distributed Mafia Game)
A mafia (or werewolf) game where there is no need for a server. This game runs in a distributed peer-to-peer manner; thus, players do not require to setup a server node and can play the game immediately.

# Game Structure
- First, an initiator broadcasts that she will start a game with `k` koylu's, `v` vampires and `d`  doctors. 
- Other participants join the game whether they want or not
- When initiator is satisfied with the participation, she starts the game
- *Role Distribution*: Each participant of the game is assigned a role. Ideally, no node should be beware of other player's role, even if they try to cheat with a modified code.
- *Game Phase*: Game begins.

# Roles and Descriptions
- `Koylu`: A participant that tries to capture all vampires. They can vote for killing.
- `Vampire`: A participant that tries to kill all koylus. They can vote for killing.
- `Doctor`: A koylu with special ability that each round, they can select a koylu for protecting that night, so that that night if a vampire attacks the koylu they are protecting, they don't die and the vampire that attacks them is caught. They can vote for killing.

# Brief Implementation
For more detailed information, please refer to [ALGORITHM.md](docs/ALGORITHM.md)

## Role Distribution
By definition, initializer has to initialize the game, which means that the role distributor will be that node. Nevertheless, a malign initiator could write a modified code where the initiator knows every other role of players, or even worse, they could manipulate the role distribution mechanism. To keep cheaters away, we implemented a distribution mechanism that each node cannot see other nodes' roles.
- Initiator initializes the game variables
- Participants ask to join to the game. If the game is not full, they will be accepted. Otherwise,  they will be rejected.
- When initializor thinks that they can start the game, they press the `Enter` button and initialization mechanism will be switched to stage 1.
- At stage 1, initiator will distribute encrypted roles to each player and the keys to all other players except the node who got the current role. After that, initializor will broadcast the end of stage 1.
- At stage 2, all other nodes will distribute the encrypted roles to each other. When they distribute the roles they have, they will wait until they receive a role and decrypt it. At that point, they will inform the initiator. When all nodes informed the initiator and initiator got a role, initiator will broadcast the end of stage 2 and the game will begin.
- In some cases, one player may not be able to receive a role and all other nodes would have received a role. At this point, that node can ask the initiator for the key of that role. Initiator will wait for 5 seconds before sending that key to prevent cheating.

## Game Phase
- 60 seconds of communications. 
- After that, first discussion period with updated state if vampires have killed someone or not, nominate a participant to blame or not in 30 seconds.
- Vampires have the ability to manipulate the voting broadcast of one player. Players will whisper to each other which player they voted for. At the end of the round, it will be clear that if any player had manipulated votes. While this is a powerful tool for the vampires to win the game, it can reveal their identity if used carelessly.
If the vote for killing is lower than the skipping vote, there is no effect for that round. If there is one leading participant to be killed, they are killed. If leading votes are equal, then the voting has no effect and no one is killed.
- **THE ONE WHO GETS KILLED MUST HONESTLY BROADCAST THEIR ROLE.**
- If there are only vampires after the voting, the round is won by vampires, else the game continues until all vampires are caught or vampires won.
- Else, the vampires select the participants they will kill in 15 seconds.
- After the game phase, the network is available for a new game.

# How To Run
To run the game, first install any required packages
```
pip3 install -r requirements.txt
```
Then, please start the main.py file from this directory
```
python3 main.py
```

## To run the game in a docker environment
First, build the game with dockerfile  
```
docker build . -t cmpe487
```
Then, create a network for the game to run. Please note that the game only checks the last byte of an ip address, so you need to create your network with bitmask: 255.255.255.0  
```
docker network create --subnet 192.168.0.0/24 mynetwork
```
Lastly, run the game containers. Ensure that they are all in the same network  
```
docker run -it --network=mynetwork cmpe487
```

# Authors
- Artun Akdoğan (artun.akdogan@boun.edu.tr)
- Deniz Sürmeli (deniz.surmeli@boun.edu.tr)
