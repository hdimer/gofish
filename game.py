"""Core Go Fish game logic.

Pure, deterministic, and I/O-free so it can be tested in isolation. The CLI
frontend (gofish.py) drives this module and handles all printing and input.

A recreation of the classic BSD `gofish` game: two players (you and the
computer) draw from a shared pool, ask each other for ranks, and collect
"books" of four matching cards. Suits are irrelevant to scoring, so a card is
represented simply by its rank string.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

# Ranks in ascending order. Suits do not matter for Go Fish, so the deck is
# four copies of each rank.
RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]

HAND_SIZE = 7  # cards dealt to each player at the start


def make_deck() -> list[str]:
    """Return a fresh 52-card deck as a list of ranks (4 of each)."""
    return [rank for rank in RANKS for _ in range(4)]


def normalize_rank(text: str) -> str | None:
    """Map loose user input to a canonical rank, or None if unrecognized.

    Accepts single letters (a/j/q/k), numbers, and common words so the prompt
    is forgiving. Returns one of RANKS or None.
    """
    if text is None:
        return None
    cleaned = text.strip().lower()
    aliases = {
        "a": "A", "ace": "A", "1": "A",
        "j": "J", "jack": "J",
        "q": "Q", "queen": "Q",
        "k": "K", "king": "K",
        "t": "10", "10": "10", "ten": "10",
    }
    if cleaned in aliases:
        return aliases[cleaned]
    words = {
        "two": "2", "three": "3", "four": "4", "five": "5", "six": "6",
        "seven": "7", "eight": "8", "nine": "9",
    }
    if cleaned in words:
        return words[cleaned]
    if cleaned in {"2", "3", "4", "5", "6", "7", "8", "9"}:
        return cleaned
    return None


# Quit is a full word, never a bare letter: "q" is the Queen in Go Fish.
QUIT_WORDS = {"quit", "exit"}


def parse_command(raw: str) -> tuple[str, str | None]:
    """Classify a line of player input at the ask prompt.

    Returns one of:
      ("quit", None)   - the player wants to leave
      ("rank", RANK)   - a recognized rank to ask for
      ("unknown", None) - unrecognized input
    """
    text = (raw or "").strip()
    if text.lower() in QUIT_WORDS:
        return ("quit", None)
    rank = normalize_rank(text)
    if rank is None:
        return ("unknown", None)
    return ("rank", rank)


def extract_books(hand: list[str]) -> list[str]:
    """Remove any complete book (4 of a rank) from hand, in place.

    Returns the list of ranks that were completed and removed.
    """
    books: list[str] = []
    for rank in RANKS:
        if hand.count(rank) >= 4:
            books.append(rank)
            # Remove all four cards of that rank from the hand.
            while rank in hand:
                hand.remove(rank)
    return books


@dataclass
class Player:
    name: str
    hand: list[str] = field(default_factory=list)
    books: list[str] = field(default_factory=list)
    is_human: bool = False


class GoFishGame:
    """Encapsulates the full state of a Go Fish match.

    Determinism: pass a seed (or a pre-seeded random.Random) so tests and
    replays are reproducible. No printing happens here.
    """

    def __init__(self, seed: int | None = None, rng: random.Random | None = None):
        self.rng = rng if rng is not None else random.Random(seed)
        self.pool: list[str] = make_deck()
        self.rng.shuffle(self.pool)
        self.you = Player("You", is_human=True)
        self.cpu = Player("The computer")
        for _ in range(HAND_SIZE):
            self.you.hand.append(self.pool.pop())
            self.cpu.hand.append(self.pool.pop())
        # The computer remembers ranks you have asked for, since asking reveals
        # that you hold that rank. This mirrors the BSD opponent's memory.
        self.cpu_memory: set[str] = set()
        # Collect any books dealt outright (rare but possible).
        self._collect_books(self.you)
        self._collect_books(self.cpu)

    # --- Queries -----------------------------------------------------------

    def opponent_of(self, player: Player) -> Player:
        return self.cpu if player is self.you else self.you

    def total_books(self) -> int:
        return len(self.you.books) + len(self.cpu.books)

    def cpu_seen(self) -> list[str]:
        """Ranks the computer currently believes you hold, in deal order.

        Ranks are returned in rank order. This is the honest basis for the
        cheat-sheet panel and the bluff-aware banter: the computer only "knows"
        a rank is in your hand because you asked for it (revealing you held it)
        and it has not since taken every copy or watched you lay it down as a
        book.
        """
        return [rank for rank in RANKS if rank in self.cpu_memory]

    def is_over(self) -> bool:
        """Game ends when all 13 books are made, or nobody can move."""
        if self.total_books() >= len(RANKS):
            return True
        # If the pool is empty and either hand is empty, no more asking can
        # happen for that player; the game is over.
        if not self.pool and (not self.you.hand or not self.cpu.hand):
            return True
        return False

    def winner(self) -> Player | None:
        """Return the winning player, or None for a tie (only when over)."""
        if self.you.books == self.cpu.books == []:
            return None
        if len(self.you.books) > len(self.cpu.books):
            return self.you
        if len(self.cpu.books) > len(self.you.books):
            return self.cpu
        return None

    # --- Mechanics ---------------------------------------------------------

    def _collect_books(self, player: Player) -> list[str]:
        made = extract_books(player.hand)
        player.books.extend(made)
        return made

    def draw_from_pool(self, player: Player) -> str | None:
        """Draw one card into player's hand; return it, or None if empty."""
        if not self.pool:
            return None
        card = self.pool.pop()
        player.hand.append(card)
        return card


@dataclass
class TurnResult:
    """A structured record of one ask, for the frontend to narrate."""

    asker: Player
    target: Player
    rank: str
    received: int            # cards taken from the opponent (0 = go fish)
    went_fishing: bool       # did the asker draw from the pool?
    drew_card: str | None    # the card drawn, if any
    drew_asked_rank: bool    # drew the very rank asked for (bonus turn)
    books_made: list[str]    # books completed by the asker this turn
    asker_goes_again: bool   # true if the asker keeps the turn


def resolve_ask(game: GoFishGame, asker: Player, rank: str) -> TurnResult:
    """Resolve one ask of `rank` by `asker` against their opponent.

    Standard Go Fish rules: if the target holds the rank, all such cards move
    to the asker and the asker goes again. Otherwise the asker "goes fishing"
    (draws from the pool); if the drawn card matches the rank asked for, the
    asker also goes again.
    """
    target = game.opponent_of(asker)

    # Remember that the asker holds this rank (used by the CPU's strategy).
    if asker is game.you:
        game.cpu_memory.add(rank)

    def collect_books() -> list[str]:
        # Collect the asker's completed books, and if the asker is the human,
        # let the computer forget those ranks: a book is laid face-up, so the
        # computer sees it leave your hand.
        made = game._collect_books(asker)
        if asker is game.you:
            for done in made:
                game.cpu_memory.discard(done)
        return made

    received = target.hand.count(rank)
    if received > 0:
        for _ in range(received):
            target.hand.remove(rank)
            asker.hand.append(rank)
        # If the computer just took every copy of this rank from you, it knows
        # your hand no longer holds it.
        if target is game.you:
            game.cpu_memory.discard(rank)
        books = collect_books()
        # If the target just emptied their hand, refill it if possible.
        if not target.hand:
            game.draw_from_pool(target)
        return TurnResult(
            asker=asker, target=target, rank=rank, received=received,
            went_fishing=False, drew_card=None, drew_asked_rank=False,
            books_made=books, asker_goes_again=True,
        )

    # Go fish.
    drew = game.draw_from_pool(asker)
    drew_asked = drew == rank
    books = collect_books()
    # If the asker emptied their hand (e.g. book) and pool has cards, refill.
    if not asker.hand:
        game.draw_from_pool(asker)
    return TurnResult(
        asker=asker, target=target, rank=rank, received=0,
        went_fishing=True, drew_card=drew, drew_asked_rank=drew_asked,
        books_made=books, asker_goes_again=drew_asked,
    )


def cpu_choose_rank(game: GoFishGame) -> str | None:
    """Pick a rank for the computer to ask for, or None if it cannot ask.

    Strategy: prefer ranks the computer holds that it has also seen the human
    ask for (a likely hit), otherwise a random rank from its own hand.
    """
    cpu = game.cpu
    if not cpu.hand:
        return None
    held = set(cpu.hand)
    smart = [r for r in game.cpu_memory if r in held]
    if smart:
        return game.rng.choice(smart)
    return game.rng.choice(sorted(held))
