"""Tests for the pure Go Fish logic in game.py."""

import random

import game
from game import (
    GoFishGame,
    Player,
    RANKS,
    cpu_choose_rank,
    extract_books,
    make_deck,
    normalize_rank,
    parse_command,
    resolve_ask,
)


# --- Command parsing ---------------------------------------------------------

def test_q_means_queen_not_quit():
    # Regression: 'q' is the Queen, never a quit command (matches BSD gofish).
    assert parse_command("q") == ("rank", "Q")
    assert parse_command("Q") == ("rank", "Q")


def test_quit_requires_a_full_word():
    assert parse_command("quit") == ("quit", None)
    assert parse_command("exit") == ("quit", None)
    assert parse_command("QUIT") == ("quit", None)


def test_unknown_input_is_reported():
    assert parse_command("zzz") == ("unknown", None)
    assert parse_command("") == ("unknown", None)


# --- Deck --------------------------------------------------------------------

def test_make_deck_has_52_cards_four_of_each_rank():
    deck = make_deck()
    assert len(deck) == 52
    for rank in RANKS:
        assert deck.count(rank) == 4


# --- Rank normalization ------------------------------------------------------

def test_normalize_rank_accepts_letters_and_words():
    assert normalize_rank("a") == "A"
    assert normalize_rank("ACE") == "A"
    assert normalize_rank("k") == "K"
    assert normalize_rank("queen") == "Q"
    assert normalize_rank("t") == "10"
    assert normalize_rank("10") == "10"
    assert normalize_rank(" 7 ") == "7"
    assert normalize_rank("seven") == "7"


def test_normalize_rank_rejects_garbage():
    assert normalize_rank("z") is None
    assert normalize_rank("") is None
    assert normalize_rank("11") is None
    assert normalize_rank(None) is None


# --- Books -------------------------------------------------------------------

def test_extract_books_removes_completed_sets():
    hand = ["7", "7", "7", "7", "K", "2"]
    books = extract_books(hand)
    assert books == ["7"]
    assert sorted(hand) == ["2", "K"]


def test_extract_books_none_when_incomplete():
    hand = ["7", "7", "7", "K"]
    assert extract_books(hand) == []
    assert len(hand) == 4


# --- Setup -------------------------------------------------------------------

def test_new_game_deals_seven_cards_each():
    g = GoFishGame(seed=1)
    assert len(g.you.hand) == 7
    assert len(g.cpu.hand) == 7
    assert len(g.pool) == 52 - 14


def test_game_is_deterministic_with_seed():
    a = GoFishGame(seed=42)
    b = GoFishGame(seed=42)
    assert a.you.hand == b.you.hand
    assert a.cpu.hand == b.cpu.hand


# --- Asking: a hit -----------------------------------------------------------

def test_ask_hit_transfers_all_matching_cards_and_goes_again():
    g = GoFishGame(seed=1)
    g.you.hand = ["5", "9"]
    g.cpu.hand = ["5", "5", "K"]
    g.pool = ["2"]
    result = resolve_ask(g, g.you, "5")
    assert result.received == 2
    assert result.asker_goes_again is True
    assert result.went_fishing is False
    assert g.you.hand.count("5") == 3
    assert "5" not in g.cpu.hand


def test_ask_hit_completing_book_moves_it_to_books():
    g = GoFishGame(seed=1)
    g.you.hand = ["5", "5", "5"]
    g.cpu.hand = ["5", "K"]
    g.pool = ["2", "3"]
    result = resolve_ask(g, g.you, "5")
    assert result.books_made == ["5"]
    assert "5" in g.you.books
    assert "5" not in g.you.hand


# --- Asking: go fish ---------------------------------------------------------

def test_ask_miss_goes_fishing_and_passes_turn():
    g = GoFishGame(seed=1)
    g.you.hand = ["5", "9"]
    g.cpu.hand = ["K"]
    g.pool = ["2"]  # top card drawn is "2", not a "5"
    result = resolve_ask(g, g.you, "5")
    assert result.received == 0
    assert result.went_fishing is True
    assert result.drew_card == "2"
    assert result.drew_asked_rank is False
    assert result.asker_goes_again is False
    assert "2" in g.you.hand


def test_ask_miss_but_fishing_the_asked_rank_grants_another_turn():
    g = GoFishGame(seed=1)
    g.you.hand = ["5", "9"]
    g.cpu.hand = ["K"]
    g.pool = ["5"]  # you fish exactly what you asked for
    result = resolve_ask(g, g.you, "5")
    assert result.went_fishing is True
    assert result.drew_asked_rank is True
    assert result.asker_goes_again is True


def test_ask_miss_empty_pool_does_not_crash():
    g = GoFishGame(seed=1)
    g.you.hand = ["5"]
    g.cpu.hand = ["K"]
    g.pool = []
    result = resolve_ask(g, g.you, "5")
    assert result.drew_card is None
    assert result.asker_goes_again is False


# --- CPU strategy ------------------------------------------------------------

def test_cpu_prefers_ranks_it_saw_you_ask_for():
    g = GoFishGame(seed=1)
    g.cpu.hand = ["3", "8"]
    g.cpu_memory = {"8"}  # you previously asked for 8, cpu holds one
    assert cpu_choose_rank(g) == "8"


def test_cpu_returns_none_with_empty_hand():
    g = GoFishGame(seed=1)
    g.cpu.hand = []
    assert cpu_choose_rank(g) is None


def test_asking_records_rank_in_cpu_memory():
    g = GoFishGame(seed=1)
    g.you.hand = ["4"]
    g.cpu.hand = ["K"]
    g.pool = ["9"]
    resolve_ask(g, g.you, "4")
    assert "4" in g.cpu_memory


def test_cpu_forgets_rank_after_taking_all_of_it_from_you():
    g = GoFishGame(seed=1)
    g.you.hand = ["5", "5"]
    g.cpu.hand = ["5", "K"]
    g.pool = ["2", "3"]
    g.cpu_memory = {"5"}  # it saw you ask for 5s earlier
    resolve_ask(g, g.cpu, "5")  # cpu takes both your 5s
    assert "5" not in g.you.hand
    assert "5" not in g.cpu_memory


def test_cpu_forgets_rank_when_you_lay_down_a_book():
    g = GoFishGame(seed=1)
    g.you.hand = ["7", "7", "7"]
    g.cpu.hand = ["7", "K"]
    g.pool = ["2", "3"]
    g.cpu_memory = {"7"}
    resolve_ask(g, g.you, "7")  # you complete the book of 7s
    assert "7" in g.you.books
    assert "7" not in g.cpu_memory


def test_cpu_forgets_rank_when_you_book_it_by_fishing():
    # Regression: laying down a book completed from the pool (the go-fish
    # branch) must also clear the computer's belief that you hold that rank.
    g = GoFishGame(seed=1)
    g.you.hand = ["7", "7", "7", "K"]
    g.cpu.hand = ["A"]
    g.pool = ["7"]  # you fish the fourth 7 and lay down the book
    g.cpu_memory = {"7"}
    resolve_ask(g, g.you, "K")  # cpu has no K -> go fish -> draw 7 -> book
    assert "7" in g.you.books
    assert "7" not in g.cpu_memory
    assert "K" in g.cpu_memory  # you did reveal you hold Ks by asking


def test_cpu_seen_returns_sorted_beliefs():
    g = GoFishGame(seed=1)
    g.cpu_memory = {"K", "2", "10"}
    assert g.cpu_seen() == ["2", "10", "K"]


# --- End conditions ----------------------------------------------------------

def test_game_over_when_all_books_made():
    g = GoFishGame(seed=1)
    g.you.books = RANKS[:7]
    g.cpu.books = RANKS[7:]
    assert g.is_over() is True


def test_winner_is_player_with_most_books():
    g = GoFishGame(seed=1)
    g.you.books = ["A", "2", "3"]
    g.cpu.books = ["K"]
    assert g.winner() is g.you


def test_game_over_when_pool_empty_and_a_hand_empty():
    g = GoFishGame(seed=1)
    g.pool = []
    g.you.hand = []
    g.cpu.hand = ["K", "Q"]
    assert g.is_over() is True
