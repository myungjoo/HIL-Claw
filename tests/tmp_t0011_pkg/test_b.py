"""Temporary nested test for the T-0011 one-time check."""

from hilclaw.tmp_t0011_pkg import b


def test_value():
    assert b.VALUE == 2
