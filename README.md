# Uncia

A simple discord bot built with pycord to facilitate games of Word Chain.

## Rules

The rules of Word Chain are:

- For each turn, players take turns saying words that have not already been said.
- The words must be valid words (and cannot be proper nouns).
- Each new word after the first must start with the ending letter of the prior word.

When a turn infringes on any of the aforementioned rules, the message will be reacted to with either:

- 🚫 - Invalid word
- ❌ - Wrong starting letter
- 🔄 - Word already said
- 🖐️ - Not your turn
- 🖐️1️⃣🅿️ - Not enough players

Otherwise, if the play is valid, the message will be reacted to with a checkmark.

If a valid word is not said within the next 10 seconds, the player gets knocked out.

In order to submit a word for validation, start the word with a semicolon: `;example`

## Features

- Multiplayer matches
- Word verification
- Stat tracking

## Upcoming features

- Singleplayer games
- Correspondence games
- Ranking system
- Improved scoring
- Additional gameplay

## Usage

### /start

Starts a match in a channel (the channel it is used in). Does nothing if there is already a match in the channel.

> Games will not proceed if there is only one player. After 60 seconds, the game will be aborted.

### /join

Joins a match in a channel (the channel it is used in). Does nothing if there is not a match in the channel, or if the user is already in the match.
