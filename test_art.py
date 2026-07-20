"""Tests for the ASCII card art in art.py."""

import art
from art import CARD_WIDTH, render_card, render_row


def test_card_has_seven_lines_of_fixed_width():
    lines = render_card("A")
    assert len(lines) == 7
    assert all(len(line) == CARD_WIDTH for line in lines)


def test_card_shows_rank_top_left_and_bottom_right():
    lines = render_card("A")
    assert lines[1] == "|A    |"
    assert lines[5] == "|    A|"


def test_card_handles_two_character_rank():
    lines = render_card("10")
    assert all(len(line) == CARD_WIDTH for line in lines)
    assert lines[1] == "|10   |"
    assert lines[5] == "|   10|"


def test_card_has_fish_in_the_middle():
    lines = render_card("K")
    assert art.FISH in lines[3]


def test_row_of_cards_aligns_and_joins():
    lines = render_row(["A", "K"])
    assert len(lines) == 7
    # two cards plus a one-space gap
    assert all(len(line) == CARD_WIDTH * 2 + 1 for line in lines)


def test_empty_row_has_placeholder():
    assert render_row([]) == ["(no cards)"]
