"""Command-line front of the tool registry (ADR-0010 decision 4).

Command line: ``python -m hilclaw <tool name>``. The tool name is the only
argument and no option exists. The request is read from standard input to its
end: one JSON object in UTF-8.

Exit status 0 means a result: standard output holds that one JSON object and
one LF. Any other status means a tool failure: standard output holds
``{"error": {"kind": ..., "message": ...}}`` and one LF. Status 3 is a failure
of the call (the tool function raised one, crashed or returned no result);
status 4 is what the front answers by itself, with the kinds ``bad_usage``
(not exactly one argument), ``unknown_tool`` and ``bad_request`` (standard
input cannot be read or is not a request). When standard output cannot be
written, the status is 4 too, or 120 if the interpreter's own flush at exit
fails as well. The values 1 and 2, which the interpreter uses for an uncaught
exception and for its own usage errors, are never returned.

Standard error gets one line of free text on a failure and is never parsed.
"""

import contextlib
import sys

from hilclaw import tools

EXIT_RESULT = 0
EXIT_TOOL_FAILURE = 3
EXIT_FRONT_FAILURE = 4

KIND_BAD_USAGE = "bad_usage"
KIND_UNKNOWN_TOOL = "unknown_tool"
KIND_BAD_REQUEST = "bad_request"


def _refused(kind, message):
    return EXIT_FRONT_FAILURE, tools.ToolFailure(kind, message).error_object()


def _outcome(args, registry, stdin):
    if len(args) != 1:
        usage = f"expected one argument, the tool name, got {len(args)}"
        return _refused(KIND_BAD_USAGE, usage)
    try:
        registry.get(args[0])
        request = tools.decode_request(stdin.read())
        return EXIT_RESULT, tools.call(registry, args[0], request)
    except tools.UnknownToolError as e:
        return _refused(KIND_UNKNOWN_TOOL, str(e))
    except tools.InvalidRequestError as e:
        return _refused(KIND_BAD_REQUEST, str(e))
    except OSError as e:
        return _refused(KIND_BAD_REQUEST, f"cannot read standard input: {e}")
    except tools.ToolFailure as e:
        return EXIT_TOOL_FAILURE, e.error_object()


def _say(stderr, text):
    with contextlib.suppress(OSError):
        stderr.write(f"hilclaw: {text}\n".encode("utf-8", "backslashreplace"))
        stderr.flush()


def main(argv=None, *, registry=None, stdin=None, stdout=None, stderr=None):
    """Answer one tool call and return the exit status (0 result, 3 or 4 tool failure).

    ``argv`` defaults to ``sys.argv[1:]`` and ``registry`` to
    :func:`hilclaw.tools.default_registry`. ``stdin``, ``stdout`` and
    ``stderr`` are binary streams and default to the standard ones.
    """
    args = sys.argv[1:] if argv is None else list(argv)
    registry = tools.default_registry() if registry is None else registry
    stdin = sys.stdin.buffer if stdin is None else stdin
    stdout = sys.stdout.buffer if stdout is None else stdout
    stderr = sys.stderr.buffer if stderr is None else stderr
    status, answer = _outcome(args, registry, stdin)
    if status != EXIT_RESULT:
        error = answer["error"]
        _say(stderr, f"{error['kind']}: {error['message']}")
    try:
        stdout.write(tools.encode(answer))
        stdout.flush()
    except OSError as e:
        _say(stderr, f"cannot write standard output: {e}")
        return EXIT_FRONT_FAILURE
    return status


if __name__ == "__main__":
    raise SystemExit(main())
