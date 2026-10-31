"""The operation's reading of a timing process container's output (ADR-0145 slice (6)).

``ARCHITECTURE/decisions/ADR-0145-od14-first-case-container-measurement.md``
makes a C program of the harness, *the waiter*, process 1 of the container of
a ``cpu_standin`` timing process. After its child has ended and every other
process of the container is gone, the waiter writes one LF and then one last
line, ended by one LF (its step W5). :func:`read` is the rule of its decision 3,
"What the operation takes": it takes the last line of the client's standard
output as the waiter's, removes the one LF of W5 before it and returns the
bytes before that LF, unchanged, as the report, with the memory figure by the
Linux unit rule of its decision 4. It is bound to no tool and no operation;
:func:`hilclaw.standin_answer.read_timing_process` calls it.

The waiter's line (W5 leaves its spelling to the code; the C waiter of ADR-0145
slice (5) is written against this text). It is ASCII, ended by one LF, and
exactly one of:

- the value line ``waiter_max_rss_kib <v>`` (:data:`VALUE_KEYWORD`, one space,
  then ``<v>``), where ``<v>`` is the raw ``ru_maxrss`` of the waited child as
  ``printf("%ld")`` writes a ``long`` of at most 64 bits: an optional ``-``,
  then ``0`` or digits that do not start with ``0``, from -2**63 to
  2**63 - 1. The waiter writes it only where it was compiled for Linux, so
  ``<v>`` is in KiB;
- the none line ``waiter_max_rss none`` (:data:`NONE_LINE`), written where the
  waiter was compiled for another system.

Neither shares a keyword with the report of ADR-0009 decision 8
(``resolution_ns``, ``interval_ns``, ``stop``).

The figure is ``memory_ceiling.figure(v, "linux")``: ``v`` times 1024 for a
``v`` of at least 1 and no figure otherwise (ADR-0052 decision 4). The unit
rule is the container's system, so :data:`sys.platform` is never read.

A figure is taken only from the last line because a kernel can write a line of
the waiter's form on the report channel, and that line must stay inside the
report, which is then broken, rather than give a figure (ADR-0145 decision 5).

A stream has no waiter's line when it is empty, is not ended by an LF, has an
empty last line or no LF before its last line (ADR-0145 decision 3), and, by
this module's reading of that decision, when its last line is of neither
spelling above. :func:`read` then returns ``None`` with no report.

What this module does not decide: what a call answers, and with which kind,
for a stream with no waiter's line, a waiter that ended with a non-zero status
or a waiter's build that failed (ADR-0145 decision 6; OD-18 sub-question 19;
HQ-0021, HQ-0026), so such a stream is a plain return value and raises
nothing. It reads no exit status of the client: ADR-0145 decision 6 has no
status read as the run's before the waiter's line was looked for, and that
order is slice (4)'s. It neither parses nor judges the report (that is
:mod:`hilclaw.harness.timing`, above the cut of ADR-0061 decision 3), starts no
process and reads no file, clock or environment variable.
"""

import re
from typing import NamedTuple

from hilclaw.harness import memory_ceiling

VALUE_KEYWORD = b"waiter_max_rss_kib"
NONE_LINE = b"waiter_max_rss none"

_VALUE = re.compile(rb"0|-?[1-9][0-9]{0,18}")
_LONG_MIN, _LONG_MAX = -(2**63), 2**63 - 1


class WaiterRead(NamedTuple):
    """A stream with a waiter's line: the report before it and the figure.

    ``report`` is the ``bytes`` before the LF of W5, unchanged and possibly
    empty. ``memory_bytes`` is the figure in bytes, or ``None`` where the line
    is the none line or its value is below 1.
    """

    report: bytes
    memory_bytes: int | None


def read(stdout):
    """Return the :class:`WaiterRead` of ``stdout``, or ``None`` if it has no waiter's line.

    ``stdout`` is what the client of a timing process container wrote on its
    standard output, as exactly ``bytes``; anything else, a ``bytearray``, a
    ``memoryview`` and an instance of a subclass included, raises
    ``TypeError``. No ``bytes`` value raises.
    """
    if type(stdout) is not bytes:
        raise TypeError(f"stdout: must be bytes, got {type(stdout).__name__}")
    if not stdout.endswith(b"\n"):
        return None
    cut = stdout.rfind(b"\n", 0, len(stdout) - 1)
    if cut < 0:
        return None
    report, line = stdout[:cut], stdout[cut + 1 : -1]
    if line == NONE_LINE:
        return WaiterRead(report, None)
    keyword, space, value = line.partition(b" ")
    if keyword != VALUE_KEYWORD or not space or not _VALUE.fullmatch(value):
        return None
    max_rss = int(value)
    if not _LONG_MIN <= max_rss <= _LONG_MAX:
        return None
    return WaiterRead(report, memory_ceiling.figure(max_rss, "linux"))
