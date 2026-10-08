"""The source of the seed of a correctness check (ADR-0021 decision 3).

``ARCHITECTURE/decisions/ADR-0021-od18-correctness-check-split.md`` fixes the
property in its decision 3, "The source, as a property and not an algorithm":
the seed comes from a source whose output nobody can predict or influence
before the draw - not derived from the request, the identity, any file of the
data plane or of the source, a clock, a counter or anything an earlier call
left - and it is drawn over the whole range of seeds the harness accepts. The
record leaves to the code how a source is bound and whether a test binds one of
its own; this module is that form and nothing more.

A *seed source* is a callable without arguments that returns a seed or fails.
A seed is what :func:`hilclaw.harness.verification.program_arguments` and
:func:`hilclaw.harness.verification_arrays.draw_inputs` accept as ``seed``:
exactly an ``int`` with 0 <= seed < 2**64. :func:`system` is the one source
this package offers, and :func:`draw` is the one place a source is asked: code
that needs a seed is built with a source in reach and calls :func:`draw` with
it. A test binds a source of its own by handing :func:`draw` another callable.

Conventions of this module (not rules of the record):

- The range is written here, as :data:`SEED_BITS` and :data:`SEED_LIMIT`, so
  that the module imports neither ``numpy`` nor a module that does. It is the
  range of ``hilclaw.harness.verification_arrays.SEED_LIMIT``.
- The rule for a value is the one the harness applies to ``seed``: a ``bool``,
  a ``float``, a NumPy integer and an instance of a subclass of ``int`` are no
  seeds.
- :class:`SeedSourceError` is the one class for a source that fails and for a
  source that names no seed. Its message names a type and the rule and never
  shows what a source returned or the message of what a source raised.

What this module does not do: it draws at no moment of its own and decides
neither who asks nor when; it keeps nothing between two calls and holds no
generator, no state and no default source; it reads no environment variable,
option, configuration, file or clock; it writes no file, no stream and no log;
it names no tool and no kind of tool failure; and it does not say whether a
seed may be kept or shown after it was used.
"""

import secrets

SEED_BITS = 64
SEED_LIMIT = 1 << SEED_BITS


class SeedSourceError(Exception):
    """A seed source failed or named no seed; no seed was returned."""


def system():
    """Return a seed drawn from the random generator of the operating system.

    The result is exactly an ``int``, drawn uniformly over the whole range
    0 <= seed < 2**64 by ``secrets.randbits``. The function takes no argument;
    it is not seeded and cannot be re-seeded, uses neither the default
    generator of the module ``random`` nor NumPy's, and derives nothing from
    an environment variable, a file, a clock, a counter or an earlier call.
    How hard its output is to predict is what the generator of the platform
    gives and nothing stronger. What the platform raises when it has no random
    source is passed on.
    """
    return secrets.randbits(SEED_BITS)


def draw(source):
    """Ask ``source`` exactly once and return the seed it named.

    ``source`` is a seed source: it is called without arguments. What it
    returns is returned unchanged when it is exactly an ``int`` with
    0 <= seed < 2**64. Nothing is repaired: no value is clamped, reduced,
    converted, replaced by the answer of another source or asked for again.
    Nothing is kept, written or printed, and two calls are independent.

    Raises, in this order: :class:`TypeError` when ``source`` is not callable,
    and nothing is asked; :class:`SeedSourceError` chained to what the source
    raised when it raises an :class:`Exception`, which includes a callable
    that cannot be called without arguments; :class:`SeedSourceError` when the
    source returns what is not exactly an ``int``; :class:`SeedSourceError`
    when it returns an ``int`` outside the range. A :class:`BaseException`
    that is no :class:`Exception` (``KeyboardInterrupt``) is passed on
    untouched. The chained exception is the source's own and is not filtered.
    """
    if not callable(source):
        raise TypeError("the seed source must be callable")
    try:
        named = source()
    except Exception as e:
        raise SeedSourceError(f"the seed source failed: {type(e).__name__}") from e
    if type(named) is not int:
        raise SeedSourceError(
            f"the seed source named no seed: got {type(named).__name__}, not an int"
        )
    if not 0 <= named < SEED_LIMIT:
        raise SeedSourceError(
            "the seed source named no seed: an int outside 0 <= seed < 2**64"
        )
    return named
