# gofish

A colorful terminal recreation of the classic BSD `gofish` card game. Play Go
Fish against the computer: ask for ranks, collect books of four, and try to
finish with more books than the computer when the deck runs out.

## Play

```sh
python3 gofish.py          # random game
python3 gofish.py 42        # seeded game (reproducible deal)
```

At each prompt, type a rank you already hold (`A`, `2`-`10`, `J`, `Q`, `K`).
Input is forgiving: `k`, `king`, `t`, `ten`, `ace` all work. Note that `q` is
the Queen; type `quit` (or press Ctrl-D) to leave.

## Features

- **ASCII card art.** Your hand is drawn as a row of little cards, each with a
  `><>` fish in the middle.
- **Cheat sheet.** Before your turn, a panel shows what the computer has
  legitimately deduced about your hand (the ranks it has seen you ask for and
  not yet taken or watched you book). Ask for those before it hunts them.
- **Bluff-aware trash talk.** The computer taunts you, and calls you out when
  it takes a rank you tipped it off about.

## Rules implemented

- Both players are dealt 7 cards; the rest form the pool.
- You may only ask for a rank you currently hold.
- Hit: the opponent hands over every card of that rank and you go again.
- Miss: **GO FISH!** You draw from the pool. If you draw the exact rank you
  asked for, you go again.
- Four of a kind is a "book," removed from your hand and scored.
- Most books when the deck and a hand run out wins.

The computer remembers ranks you have asked for and uses them to guess, just
like the original.

## Colors

Prompts, card ranks, books, and outcomes are colored with ANSI codes. Color is
on automatically when writing to a terminal. Override with:

- `NO_COLOR=1` to force it off
- `FORCE_COLOR=1` to force it on (e.g. when piping)

## Tests

```sh
python3 -m venv .venv && .venv/bin/pip install pytest
.venv/bin/python -m pytest -q
```

The game logic lives in `game.py` (pure, I/O-free, deterministic with a seed)
and is covered by `test_game.py`. The colored CLI is in `gofish.py`.
