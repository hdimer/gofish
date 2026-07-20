#!/usr/bin/env python3
"""gofish - a colorful recreation of the classic BSD Go Fish card game.

Play Go Fish against the computer in your terminal. Ask for ranks, collect
books of four, and try to make more books than the computer before the deck
runs out.

Colors are applied to the prompts and card ranks. Set NO_COLOR=1 (or pipe the
output somewhere that isn't a terminal) to disable them.
"""

from __future__ import annotations

import os
import sys

import art
import banter
import game
from game import GoFishGame, Player, TurnResult, cpu_choose_rank, parse_command, resolve_ask


# --- Color support -----------------------------------------------------------

class Palette:
    """ANSI color helpers that no-op when color is disabled."""

    def __init__(self, enabled: bool):
        self.enabled = enabled

    def _wrap(self, code: str, text: str) -> str:
        if not self.enabled:
            return text
        return f"\033[{code}m{text}\033[0m"

    def prompt(self, t):   return self._wrap("1;36", t)   # bold cyan
    def you(self, t):      return self._wrap("1;32", t)   # bold green
    def cpu(self, t):      return self._wrap("1;35", t)   # bold magenta
    def rank(self, t):     return self._wrap("1;33", t)   # bold yellow
    def book(self, t):     return self._wrap("1;33", t)   # bold yellow
    def win(self, t):      return self._wrap("1;32", t)   # bold green
    def lose(self, t):     return self._wrap("1;31", t)   # bold red
    def fish(self, t):     return self._wrap("1;34", t)   # bold blue
    def dim(self, t):      return self._wrap("2", t)      # dim
    def bold(self, t):     return self._wrap("1", t)      # bold


def color_enabled() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    return sys.stdout.isatty()


# --- Rendering ---------------------------------------------------------------

def print_hand_cards(hand: list[str], pal: Palette) -> None:
    """Print the hand as a row of ASCII cards, sorted by rank."""
    order = {r: i for i, r in enumerate(game.RANKS)}
    cards = sorted(hand, key=lambda r: order[r])
    for line in art.render_row(cards):
        print(pal.rank("  " + line))


def print_cheatsheet(g: GoFishGame, pal: Palette) -> None:
    """Show what the computer has deduced about your hand."""
    seen = g.cpu_seen()
    print(pal.fish("  🔎 Cheat sheet - what the computer has seen:"))
    if seen:
        cards = " ".join(pal.rank(r) for r in seen)
        print(f"     It's onto your {cards}.")
        print(pal.dim("     Expect it to hunt those. Ask for them before it does."))
    else:
        print(pal.dim("     Nothing yet - your hand is still a mystery to it."))
    print()


def render_books(player: Player, pal: Palette) -> str:
    if not player.books:
        return pal.dim("none yet")
    return " ".join(pal.book(f"[{b}]") for b in player.books)


def print_scoreboard(g: GoFishGame, pal: Palette) -> None:
    print()
    print(pal.bold("  ── Books ──"))
    print(f"  {pal.you('You'):<20} {render_books(g.you, pal)}")
    print(f"  {pal.cpu('Computer'):<20} {render_books(g.cpu, pal)}")
    print(pal.dim(f"  Cards left in the pool: {len(g.pool)}"))
    print()


# --- Narration ---------------------------------------------------------------

def narrate(result: TurnResult, pal: Palette) -> None:
    asker_is_you = result.asker.is_human
    who = pal.you("You") if asker_is_you else pal.cpu("The computer")
    verb = "ask" if asker_is_you else "asks"
    target = "the computer" if asker_is_you else "you"
    rank = pal.rank(result.rank)

    print(f"{who} {verb} {target} for {rank}s.")

    if result.received > 0:
        # The card comes FROM the target: the computer when you ask, you when
        # the computer asks. Match the verb to that subject.
        source = "The computer" if asker_is_you else "You"
        handed = "hands over" if asker_is_you else "hand over"
        print(f"  {source} {handed} {pal.rank(str(result.received))} "
              f"{rank}{'s' if result.received != 1 else ''}.")
    else:
        print(f"  {pal.fish('GO FISH!')}")
        if result.went_fishing and result.drew_card is not None:
            if asker_is_you:
                print(f"  You draw a {pal.rank(result.drew_card)} from the pool.")
            else:
                print(f"  The computer draws from the pool.")
            if result.drew_asked_rank:
                print(f"  {pal.fish('Lucky draw!')} It was a {rank} "
                      f"{pal.dim('- go again.')}")

    for b in result.books_made:
        owner = "You complete" if asker_is_you else "The computer completes"
        print(f"  {pal.book('*** ' + owner + ' the book of ' + b + 's! ***')}")


def cpu_comment(result: TurnResult, informed: bool, pal: Palette, rng) -> None:
    """Print the computer's trash talk reacting to its own turn."""
    if result.received > 0 and informed:
        # Bluff-aware: it took a rank it had watched you ask for.
        line = banter.pick_line("cpu_knows", rng, rank=result.rank)
    elif result.books_made:
        line = banter.pick_line("cpu_book", rng, rank=result.books_made[0])
    elif result.went_fishing and result.drew_asked_rank:
        line = banter.pick_line("cpu_lucky_fish", rng)
    elif result.received == 0:
        line = banter.pick_line("cpu_miss", rng)
    else:
        line = ""
    if line:
        print(pal.cpu(f'  💬 "{line}"'))


def human_comment(result: TurnResult, pal: Palette, rng) -> None:
    """Print the computer's reaction to something you did."""
    if result.books_made:
        line = banter.pick_line("human_book", rng)
    elif result.went_fishing and result.drew_asked_rank:
        line = banter.pick_line("human_lucky", rng)
    else:
        line = ""
    if line:
        print(pal.cpu(f'  💬 The computer mutters: "{line}"'))


# --- Input -------------------------------------------------------------------

def prompt_for_rank(g: GoFishGame, pal: Palette) -> str | None:
    """Ask the human for a rank they hold. Return the rank, or None to quit."""
    held = sorted(set(g.you.hand), key=lambda r: game.RANKS.index(r))
    while True:
        print("Your hand:")
        print_hand_cards(g.you.hand, pal)
        choices = pal.dim("(" + ", ".join(held) + ")")
        try:
            raw = input(pal.prompt(f"Ask the computer for which rank? {choices} "))
        except (EOFError, KeyboardInterrupt):
            print()
            return None
        kind, rank = parse_command(raw)
        if kind == "quit":
            return None
        if kind == "unknown":
            print(pal.lose("  I don't recognize that rank. Try again "
                           "(A, 2-10, J, Q, K).\n"))
            continue
        if rank not in g.you.hand:
            print(pal.lose(f"  You can only ask for a rank you hold. "
                           f"You have no {rank}s.\n"))
            continue
        return rank


# --- Game loop ---------------------------------------------------------------

def play_turn(g: GoFishGame, player: Player, pal: Palette) -> bool:
    """Play one full turn (including bonus asks). Return False if the human quit."""
    while True:
        if not player.hand:
            # Try to refill an empty hand; if impossible, the turn ends.
            if g.draw_from_pool(player) is None:
                return True

        if player.is_human:
            rank = prompt_for_rank(g, pal)
            if rank is None:
                return False
            result = resolve_ask(g, player, rank)
            narrate(result, pal)
            human_comment(result, pal, g.rng)
        else:
            rank = cpu_choose_rank(g)
            if rank is None:
                return True
            # Capture whether this was an informed ask before resolving, since
            # resolving may prune the rank from the computer's memory.
            informed = rank in g.cpu_memory
            result = resolve_ask(g, player, rank)
            narrate(result, pal)
            cpu_comment(result, informed, pal, g.rng)
        print()

        if g.is_over() or not result.asker_goes_again:
            return True
        print(pal.dim("  You go again!" if player.is_human
                      else "  The computer goes again."))


def main() -> int:
    pal = Palette(color_enabled())
    seed = None
    if len(sys.argv) > 1:
        try:
            seed = int(sys.argv[1])
        except ValueError:
            seed = None

    g = GoFishGame(seed=seed)

    print(pal.win("\n  🐟  Welcome to Go Fish!  🐟\n"))
    print("  Collect books of four matching cards. Ask the computer for a")
    print("  rank you already hold. Most books when the deck runs out wins.")
    print(pal.dim("  Type quit (or press Ctrl-D) to leave at any prompt.\n"))

    human_turn = True
    while not g.is_over():
        header = pal.you("── Your turn ──") if human_turn else pal.cpu("── Computer's turn ──")
        print(header)
        if human_turn:
            print_cheatsheet(g, pal)
        keep_playing = play_turn(g, g.you if human_turn else g.cpu, pal)
        if not keep_playing:
            print(pal.dim("\n  Thanks for playing. Bye!"))
            return 0
        print_scoreboard(g, pal)
        human_turn = not human_turn

    # Game over.
    print(pal.bold("\n  ══════ Game over ══════"))
    print_scoreboard(g, pal)
    winner = g.winner()
    if winner is None:
        print(pal.bold("  It's a tie!"))
    elif winner.is_human:
        print(pal.win("  🎉 You win! 🎉"))
    else:
        print(pal.lose("  The computer wins. Better luck next time!"))
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
