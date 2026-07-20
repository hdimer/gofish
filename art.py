"""ASCII card art for Go Fish.

Pure rendering helpers: given a rank, produce the lines of a little card. No
color and no I/O here so the layout can be tested exactly; the CLI applies
color by wrapping whole lines.
"""

from __future__ import annotations

# Interior width of a card, in characters. Wide enough for the two-character
# rank "10" plus breathing room.
INNER = 5
CARD_WIDTH = INNER + 2  # including the two border columns
FISH = "><>"            # a little Go Fish mascot in the middle of every card


def render_card(rank: str) -> list[str]:
    """Return the 7 lines of a single card face for `rank`.

    Every line is exactly CARD_WIDTH characters wide, so cards align when
    stacked or placed side by side.
    """
    top = "." + "-" * INNER + "."
    bottom = "`" + "-" * INNER + "'"
    return [
        top,
        "|" + rank.ljust(INNER) + "|",
        "|" + " " * INNER + "|",
        "|" + FISH.center(INNER) + "|",
        "|" + " " * INNER + "|",
        "|" + rank.rjust(INNER) + "|",
        bottom,
    ]


def render_row(ranks: list[str]) -> list[str]:
    """Return the lines of several cards laid out in a horizontal row.

    Returns a placeholder line for an empty hand so the caller always has
    something to print.
    """
    if not ranks:
        return ["(no cards)"]
    cards = [render_card(r) for r in ranks]
    return [" ".join(card[line] for card in cards) for line in range(7)]
