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