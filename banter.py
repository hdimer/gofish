"""Trash talk for the computer opponent.

Pure line selection so it stays deterministic under a seeded RNG and testable.
The "bluff-aware" bit is that some categories fire only when the computer is
acting on information you leaked (asking for a rank it saw you ask for), and
those lines call it out.

Line templates may contain "{rank}"; pick_line fills it in.
"""

from __future__ import annotations

import random

LINES: dict[str, list[str]] = {
    # Bluff-aware: the computer targets a rank you revealed you hold.
    "cpu_knows": [
        "You asked for {rank}s a minute ago. I don't forget.",
        "Hand them over. I know you're sitting on {rank}s.",
        "Nice try hiding those {rank}s from me.",
        "You tipped your hand on the {rank}s. Pay up.",
    ],
    # The computer fished the exact rank it asked for.
    "cpu_lucky_fish": [
        "Ha! Pulled it right out of the pool.",
        "The ocean provides.",
        "Would you look at that. Exactly what I wanted.",
    ],
    # The computer completed a book.
    "cpu_book": [
        "Book of {rank}s. Stack it up.",
        "Another set for me. Feeling the pressure yet?",
        "That's a wrap on {rank}s.",
    ],
    # The computer struck out and had to go fish.
    "cpu_miss": [
        "Go fish? Fine. The tide turns eventually.",
        "You got lucky that time.",
        "Hmph. I'll get them next round.",
    ],
    # You completed a book. The computer is unimpressed.
    "human_book": [
        "Beginner's luck.",
        "Enjoy it while it lasts.",
        "So you can count to four. Congratulations.",
    ],
    # You fished the exact rank you asked for.
    "human_lucky": [
        "Pfft. The pool likes you today.",
        "Don't get comfortable.",
    ],
}


def pick_line(category: str, rng: random.Random, rank: str = "") -> str:
    """Return one trash-talk line for `category`, or "" if there is none."""
    options = LINES.get(category)
    if not options:
        return ""
    return rng.choice(options).format(rank=rank)
