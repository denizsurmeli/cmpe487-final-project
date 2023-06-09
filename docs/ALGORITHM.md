# The Initializer Logic
- Initiator initializes the game variables
- Participants ask to join to the game. If the game is not full, they will be accepted. Otherwise, they will be rejected.
- When initializor thinks that they can start the game, they press the `Enter` button and initialization mechanism will be switched to stage 1.
- At stage 1, initiator will distribute encrypted roles to each player and the keys to all other players except the node who got the current role. After that, initializor will broadcast the end of stage 1.
![stage 1](imgs/stage1.png)
- At stage 2, all other nodes will distribute the encrypted roles to each other. When they distribute the roles they have, they will wait until they receive a role and decrypt it. At that point, they will inform the initiator. When all nodes informed the initiator and initiator got a role, initiator will broadcast the end of stage 2 and the game will begin.
![stage 2](imgs/stage2.png)
- In some cases, one player may not be able to receive a role and all other nodes would have received a role. At this point, that node can ask the initiator for the key of that role. Initiator will wait for 5 seconds before sending that key to prevent cheating.
![exceptional case](imgs/exception.png)


# The Game Logic
There are practically three stages that the user deals with. Each stage can be stated briefly as follows:
- State: Day
    - Communicate with others. 
    - Select the saved ones.
- State: Night
    - Vampires target the ones they want to kill.
- State: Voting
    - Cast votes, select a peer to be killed. 

This logic obviously over simplified here but this is the heart of it really.

## Voting Logic
- You practically vote as is:
    - Broadcasts
    - Whispers
- We first make an intermediate board for the votes, where everyone votes and we keep track of the whispers and broadcasts.
- The whispers are propagated immediately by the voter, they first broadcast to all, then whisper each player one-by-one.
- After listening the intermediate period, we finalize the votes by looking at the whispers and broadcasts and make the final call for each peer.
