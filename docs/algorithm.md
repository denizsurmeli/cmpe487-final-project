### The Game Logic

- State: Day
    - Communicate
    - Select the saved ones
        - Update the protected list
- State: Night
    - Vampires target the ones they want to kill
        - Update the killed list
        - Update the saved list
- State: Voting
    - Update the killed list
- If not end
    - Publish the state update
    - cleanup 
    - set state to day
- If end
    - Broadcast the result


### Voting Logic
- You practically vote as is:
- Broadcasts: (voter, heard votes, simply a list is sufficient)
- Whispers: (peers, dictionary of (voter, whom they whispered of))