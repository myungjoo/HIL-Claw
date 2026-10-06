"""Claude Code ``PreToolUse`` guard that refuses ``gh pr merge`` unless the PR checks are green.

The hook payload (one JSON object with ``tool_input.command`` and ``cwd``) is
read from stdin. For every ``gh pr merge`` found in the shell command the guard
runs the read-only ``gh pr checks <selector> --json name,bucket`` and nothing
else: it never merges, comments, edits or pushes.

Command line: ``python -m hilclaw.merge_guard``. Exit status is 0 with nothing
on stdout when the tool call may proceed, and 2 with a ``merge guard: ...``
reason on stderr when it is refused. The guard only refuses, it never grants a
permission, and it fails closed: every failure of the guard itself exits 2.
"""

import argparse
import json
import re
import shlex
import subprocess
import sys

EXIT_PROCEED = 0
EXIT_REFUSE = 2
TIMEOUT_SECONDS = 60

_SEPARATORS = ";&|()`\n"
_LONG_VALUE_FLAGS = frozenset(
    {
        "--body",
        "--body-file",
        "--subject",
        "--author-email",
        "--match-head-commit",
        "--repo",
    }
)
_SHORT_VALUE_FLAGS = frozenset("bFtAR")
_GH = re.compile(r"(?:.*/)?gh(?:\.exe)?", re.IGNORECASE)
_LOOKS_LIKE_MERGE = re.compile(
    r"\bgh(?:\.exe)?\b.*?\bpr\b.*?\bmerge\b", re.DOTALL | re.IGNORECASE
)


def merge_invocations(command):
    """Return the ``gh pr checks`` arguments of every ``gh pr merge`` in a shell command line.

    Each item is the PR selector if one is given, followed by ``--repo <value>``
    if one is given. An empty list means the command does not merge a PR. Text
    inside a quoted argument is never a merge. Raises :class:`ValueError` when
    the command cannot be tokenised but looks like a merge, or when the selector
    starts with ``-``.
    """
    lex = shlex.shlex(
        command.replace("\r\n", "\n").replace("\\\n", ""),
        posix=True,
        punctuation_chars=_SEPARATORS,
    )
    lex.whitespace = " \t\r"
    lex.whitespace_split = True
    lex.commenters = ""
    try:
        tokens = list(lex)
    except ValueError as e:
        if _LOOKS_LIKE_MERGE.search(command):
            raise ValueError(
                f"cannot parse a command that looks like gh pr merge ({e})"
            ) from e
        return []
    found, words = [], []
    for token in [*tokens, ";"]:
        if token and not token.strip(_SEPARATORS):
            found += _merges_in(words)
            words = []
        else:
            words.append(token)
    return found


def _merges_in(words):
    found = []
    for i, word in enumerate(words):
        if not _GH.fullmatch(word):
            continue
        positionals, repo = _split_flags(words[i + 1 :])
        if positionals[:2] != ["pr", "merge"]:
            continue
        selector = positionals[2:3]
        if selector and selector[0].startswith("-"):
            raise ValueError(f"unsupported gh pr merge selector {selector[0]!r}")
        found.append(selector + (["--repo", repo] if repo else []))
    return found


def _split_flags(words):
    positionals, repo, i = [], None, 0
    while i < len(words):
        word = words[i]
        i += 1
        if word == "--":
            positionals += words[i:]
            break
        if not word.startswith("-") or word == "-":
            positionals.append(word)
            continue
        if word.startswith("--"):
            name, attached, value = word.partition("=")
            if name not in _LONG_VALUE_FLAGS:
                continue
        else:
            at = next(
                (k for k, c in enumerate(word) if k and c in _SHORT_VALUE_FLAGS), None
            )
            if at is None:
                continue
            name, value = word[at], word[at + 1 :].removeprefix("=")
            attached = value
        if not attached:
            value = words[i] if i < len(words) else None
            i += 1
        if name in ("--repo", "R"):
            repo = value
    return positionals, repo


def checks_problem(checks):
    """Return ``None`` if the ``gh pr checks`` entries allow a merge, else a one-line reason.

    A merge is allowed when at least one check has the bucket ``pass`` and every
    other check is ``pass`` or ``skipping``.
    """
    bad = [
        f"{c.get('name', '?')} ({c.get('bucket', '?')})"
        for c in checks
        if c.get("bucket") not in ("pass", "skipping")
    ]
    if bad:
        return f"checks are not successful: {', '.join(bad)}"
    if not any(c.get("bucket") == "pass" for c in checks):
        return f"no check has passed ({len(checks)} reported, none with bucket pass)"
    return None


def _checks_of(args, cwd, run):
    argv = ["gh", "pr", "checks", *args, "--json", "name,bucket"]
    try:
        done = run(
            argv,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=TIMEOUT_SECONDS,
        )
    except FileNotFoundError as e:
        return f"cannot run gh: gh or the working directory was not found ({e})"
    except subprocess.TimeoutExpired:
        return f"gh pr checks timed out after {TIMEOUT_SECONDS} s"
    except Exception as e:
        return f"cannot run gh pr checks: {type(e).__name__}: {e}"
    try:
        checks = json.loads(done.stdout)
    except (TypeError, ValueError):
        checks = None
    if not isinstance(checks, list) or not all(isinstance(c, dict) for c in checks):
        said = " ".join(f"{done.stderr or ''} {done.stdout or ''}".split())[:300]
        return f"gh pr checks did not report a list of checks: {said or 'no output'}"
    return checks_problem(checks)


def evaluate(payload, run=None):
    """Return ``None`` to let the tool call of a hook payload proceed, else the denial reason.

    ``run`` replaces :func:`subprocess.run` (the default) so that tests need no
    real ``gh`` process. A payload without a string ``tool_input.command``
    proceeds; every merge invocation in the command must pass.
    """
    tool_input = payload.get("tool_input")
    command = tool_input.get("command") if isinstance(tool_input, dict) else None
    if not isinstance(command, str):
        return None
    try:
        invocations = merge_invocations(command)
    except ValueError as e:
        return str(e)
    cwd = payload.get("cwd")
    if not isinstance(cwd, str) or not cwd:
        cwd = None
    for args in invocations:
        problem = _checks_of(args, cwd, run or subprocess.run)
        if problem:
            return f"{problem} [{' '.join(['gh pr checks', *args])}]"
    return None


def main(argv=None):
    """Read one hook payload from stdin and return the exit status (0 proceed, 2 refuse)."""
    argparse.ArgumentParser(
        prog="python -m hilclaw.merge_guard",
        description="PreToolUse hook: refuse gh pr merge unless the PR checks are green.",
    ).parse_args(argv)
    try:
        raw = getattr(sys.stdin, "buffer", sys.stdin).read()
        try:
            payload = json.loads(raw)
        except ValueError as e:
            reason = f"the hook payload on stdin is not JSON ({e})"
        else:
            if isinstance(payload, dict):
                reason = evaluate(payload)
            else:
                reason = "the hook payload on stdin is not a JSON object"
    except Exception as e:
        reason = f"the guard itself failed: {type(e).__name__}: {e}"
    if reason is None:
        return EXIT_PROCEED
    print(f"merge guard: {reason}", file=sys.stderr)
    return EXIT_REFUSE


if __name__ == "__main__":
    raise SystemExit(main())
