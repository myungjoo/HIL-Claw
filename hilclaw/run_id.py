"""Building a ``run_id`` of the form of ADR-0027.

``ARCHITECTURE/decisions/ADR-0027-od8-run-id-form.md`` fixes in its decision 2
the form of a ``run_id`` that a component of the system builds:
``<time>-<random>``, 33 characters. ``<time>`` is the 16 characters
``YYYYMMDDthhmmssz``: the reading of a clock in UTC to the second, with a year
from ``0001`` to ``9999`` and the letters ``t`` and ``z`` in lower case.
``<random>`` is 64 bits as 16 characters of lower-case hexadecimal. The example
of the record is ``20261009t012331z-9f3a6c1e0b7d4a52``. Its decision 6 names the
two sources as properties - the UTC reading of the clock of the machine on
which the id is built, and the operating system's source of random bits, never
a generator that a caller seeds or that starts from a fixed or time-derived
seed - and leaves to the code whether a function takes the time and the bits
as arguments or obtains them itself. This module is that code and nothing
more: :func:`compose` writes a given time and given bits in the form, and
:func:`new` obtains the two from those sources and returns what
:func:`compose` writes of them.

Conventions of this module (not rules of the record):

- A time is exactly a ``datetime.datetime`` whose offset from UTC is zero,
  however its zone is spelled. A time without a zone and a time with another
  offset are refused and not converted: the form holds a UTC reading, and the
  digits written are then the digits given. A fraction of a second is dropped
  and not rounded, as the form is to the second.
- The bits are exactly an ``int`` with 0 <= bits < 2**64: a ``bool``, a
  ``float`` and an instance of a subclass of ``int`` are no bits.
- A value of another type raises :class:`TypeError` and a value of the right
  type that cannot be written in the form raises :class:`ValueError`. Nothing
  is clamped, wrapped, converted or replaced, and no message shows a value.
- :func:`new` asks the clock through the module-level name ``_utc_now`` and
  the random source through the module ``secrets``; a test replaces the two
  names in this module.
- The result is not passed through :func:`hilclaw.layout.check_run_id`: every
  string :func:`compose` returns matches the pattern of ADR-0004 decision 8,
  so the call could only be an assertion.

What this module does not do, in the words of ADR-0027 decisions 1 and 3 to 6:
the form binds what builds an id and is no rule of validity, so this module
checks, parses, recognises and compares no id, and what a valid ``run_id`` is
stays what :func:`hilclaw.layout.check_run_id` checks; an id states nothing,
no fact of a run is read from one, and the time part is the reading of a
clock at the moment of the build and no record of when a run started; two
names of the form whose time parts differ are in the byte order of those
parts, which for two results of :func:`new` is the order of two clock
readings and not of events, is for a person who lists ``runs/``, and is
nothing a component may depend on; that two results of :func:`new` differ
rests on a probability, whose bound holds as far as the draws are
independent, and the form is no check and no reservation, so collisions are
improbable, not excluded, and nothing here notices one; the clock is
compared with nothing and trusted for nothing. This module reads,
lists and creates no file or directory and takes no ``data_root``, how the
platform reaches its random source being the platform's; it keeps nothing
between two calls and draws once for an id; it is bound to no tool and to no
start of an instance; and it does not say what builds an id, when, which
events call for a new one, or whether a run may have an id the system did not
build (OD-8 sub-questions 1, 10, 17, 23 and 24; OD-23).
"""

import datetime
import functools
import secrets

_BITS = 64
_utc_now = functools.partial(datetime.datetime.now, datetime.UTC)


def compose(time, bits):
    """Return ``time`` and ``bits`` written in the form of ADR-0027 decision 2.

    The result is a ``str`` of 33 characters: the year of ``time`` in four
    digits and its month, day, hour, minute and second in two digits each,
    with leading zeros, as ``YYYYMMDDthhmmssz``; one hyphen; and ``bits`` as
    16 characters of lower-case hexadecimal with leading zeros. The function
    is pure: it asks no clock and no random source and knows nothing of where
    its two values came from, so the properties of ADR-0027 decision 6 are
    those of what :func:`new` hands it and not of every result.

    Raises, in this order: :class:`TypeError` when ``time`` is not exactly a
    ``datetime.datetime``; :class:`ValueError` when ``time`` has no offset
    from UTC (a naive time) or an offset that is not zero; :class:`TypeError`
    when ``bits`` is not exactly an ``int``; :class:`ValueError` when ``bits``
    is outside 0 <= bits < 2**64. What the ``tzinfo`` of ``time`` raises when
    it is asked for the offset is passed on.
    """
    if type(time) is not datetime.datetime:
        raise TypeError("time must be a datetime.datetime")
    if time.utcoffset() != datetime.timedelta(0):
        raise ValueError("time must have an offset of zero from UTC")
    if type(bits) is not int:
        raise TypeError("bits must be an int")
    if not 0 <= bits < 1 << _BITS:
        raise ValueError("bits must be an int with 0 <= bits < 2**64")
    return (
        f"{time.year:04d}{time.month:02d}{time.day:02d}"
        f"t{time.hour:02d}{time.minute:02d}{time.second:02d}z-{bits:016x}"
    )


def new():
    """Return an id of the form built from the clock and the random source.

    The time is the UTC reading of the clock of this machine at the call and
    the bits are 64 bits drawn by ``secrets.randbits`` from the random source
    of the operating system; each is asked exactly once and the result is
    what :func:`compose` writes of the two. The function takes no argument:
    it cannot be handed a time, bits, a seed or a generator, it uses neither
    the module ``random`` nor anything derived from the time, the process or
    a caller for the bits, and it looks at no ``runs/`` directory and at no
    earlier id.

    What the platform raises when it has no random source is passed on, and
    no id is returned.
    """
    return compose(_utc_now(), secrets.randbits(_BITS))
