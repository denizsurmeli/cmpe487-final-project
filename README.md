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

# Notes

Most challenging part was to keep player's role anonymous and secure their role alignment. Fortunately, we were able to secure the role distribution mechanism by our role distribution system. Therefore, cheating to select roles should be impossible now. Unfortunately, our code has some anonymity flaws. While our game phase is completely distributed and p2p as promised, there might be some ways to reveal a user's identity by writing a modified code. But it shouldn't make the game unplayable even if some players decided to cheat.

Please note that while we implemented whispering feature, it is not yet tested.

# The Wrap-Up
In this project, we have implemented the infamous mafia game as a multiplayer decentralized game. The game requires a minimum of 3 players and has three roles: villager, vampire, and doctor. The objective for the vampires is to dominate the game by killing villagers and doctors, while the villagers try to identify who the vampire is. The doctor has the additional ability to protect villagers from being killed by the vampire.

Implementing the game in a decentralized manner posed several challenges. One of the main challenges was the role distribution problem, as there is no centralized trusted entity. To address this, we developed a role distribution system that ensures anonymity and secures the role alignment. By doing so, cheating to select roles should be impossible. However, we acknowledge that there may still be ways to reveal a user's identity by modifying the code. Nonetheless, this should not render the game unplayable even if some players decide to cheat.

Synchronization among the nodes was another significant challenge. In order to keep all nodes in sync at each stage of the game, we employed gossip mechanisms. Whenever there is a state change, such as voting or killing, the information is buffered before being distributed to all peers. This ensures that the knowledge is not known before the next stage, even if there was an oracle that could decrypt the messages. While we have not implemented encryption for state changes, this approach still secures the integrity of the game.

Lastly, we tackled the voting mechanism. Each node casts a vote, but vampires have the special skill of broadcasting votes for other players. This introduces the potential for exploitation, so peers need to reach consensus about the broadcasts from the same peer. We have two types of votes: broadcasts and whispers. Whispers are utilized only when there are multiple broadcasts for one peer in a voting period. Peers gossip with each other through whispers, sharing information about whom they have voted for. Then, during each change synchronization, decisions are made based on whispers if there are multiple broadcasts.

Overall, while implementing the mafia game in a decentralized manner presented challenges, we have addressed the role distribution problem, ensured synchronization among nodes, and implemented a consensus mechanism for voting. These efforts aim to create an engaging and fair gameplay experience in a decentralized environment.

# How To Run
To run the game, first install any required packages
```
pip3 install -r requirements.txt
```
Then, please start the main.py file from this directory
```
python3 main.py
```

# How To Play
What a player can do?
## 1. Group chat
To chat, a player has two options:
```
send_all message
```
This would send the message to all players (group chat)
```
send user message
```
This would send the message to only the specific player (private chat)

## 2. Vote
A user can vote to kill a player at voting time. The aim of the game is to capture all vampires, but it is also possible to kill an innocent player
```
vote target
```

## 3. Kill
A vampire can kill a player at night time. Vampires must earn the count dominancy over the villagers to win the game. If a player is protected, this command will have no effect.
```
kill target
```

## 4. Protect
A doctor can protect a player from vampires at day time.
```
protect target
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
