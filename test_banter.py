"""Tests for the trash-talk selection in banter.py."""

import random

import banter
from banter import pick_line


def test_pick_line_returns_a_member_of_the_category():
    rng = random.Random(0)
    line = pick_line("cpu_miss", rng)
    assert line in banter.LINES["cpu_miss"]


def test_pick_line_fills_in_rank():
    rng = random.Random(0)
    line = pick_line("cpu_knows", rng, rank="7")
    assert "{rank}" not in line
    assert "7" in line


def test_unknown_category_returns_empty_string():
    assert pick_line("nope", random.Random(0)) == ""


def test_selection_is_deterministic_under_seed():
    assert pick_line("cpu_book", random.Random(3), rank="K") == \
           pick_line("cpu_book", random.Random(3), rank="K")


def test_every_category_has_lines():
    for category, options in banter.LINES.items():
        assert options, f"{category} has no lines"
