"""Claude Code ``PreToolUse`` guard for ``gh pr merge`` and for three forbidden commands.

The hook payload (one JSON object with ``tool_input.command`` and ``cwd``) is
read from stdin. The guard refuses a shell command that holds a force push
(``git push --force``), a recursive forced removal (``rm -rf``) or
``gh repo delete``, the commands PROCESS/DRIVER.md 1-5 forbids. For every
``gh pr merge`` found in the command it runs the read-only
``gh pr checks <selector> --json name,bucket`` and nothing else: it never
merges, comments, edits, pushes or deletes.

Command line: ``python -m hilclaw.merge_guard``. Exit status is 0 with nothing
on stdout when the tool call may proceed, and 2 with a ``merge guard: ...``
reason on stderr when it is refused. The guard only refuses, it never grants a
permission, and it fails closed: every failure of the guard itself exits 2.

The guard reads the command line as text and is a second line behind the
discipline of the session, not a sandbox: a command built at run time (a
variable, ``eval``, ``bash -c "..."``, an alias) is not recognised, and the
guard does nothing until it is registered as a hook.
"""

import argparse
import json
import re
import subprocess
import sys

EXIT_PROCEED = 0
EXIT_REFUSE = 2
TIMEOUT_SECONDS = 60

_SEPARATORS = ";&|()`\n"
_NOT_IN_A_WORD = _SEPARATORS + " \t\r<>#"
_GROUP = "()"
_BACKSLASH_BEFORE_SPACE = re.compile(r"\\(?=\s)")
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
_GH = re.compile(r".*gh(?:\.(?:exe|cmd|bat))?", re.DOTALL | re.IGNORECASE)
_LOOKS_LIKE_MERGE = re.compile(r"gh\b.*?\bpr\b.*?\bmerge\b", re.DOTALL | re.IGNORECASE)
_GIT = re.compile(r"(?:.*[\\/])?git|.*git\.(?:exe|cmd|bat)", re.DOTALL | re.IGNORECASE)
_RM_NAMES = r"(?:rm|ri|rd|del|erase|rmdir|remove-item)"
_RM = re.compile(
    rf"(?:.*[\\/])?{_RM_NAMES}|.*{_RM_NAMES}\.(?:exe|cmd|bat)",
    re.DOTALL | re.IGNORECASE,
)
_GIT_VALUE_OPTIONS = frozenset(
    {
        "-C",
        "-c",
        "--git-dir",
        "--work-tree",
        "--namespace",
        "--super-prefix",
        "--config-env",
        "--attr-source",
    }
)
_RM_SHORT_FLAGS = frozenset("dfiIPrRvWx")
_FORCE_PUSH, _RM_RF, _REPO_DELETE = "git push --force", "rm -rf", "gh repo delete"
_LOOKS_FORBIDDEN = (
    (_FORCE_PUSH, (r"git\b", r"\bpush\b", r"(?<!\w)--?\w*f|\+")),
    (_RM_RF, (rf"(?<![\w.-]){_RM_NAMES}\b", r"(?<!\w)--?\w*[rf]")),
    (_REPO_DELETE, (r"gh\b", r"\brepo\b", r"\bdelete\b")),
)


def merge_invocations(command):
    """Return the ``gh pr checks`` arguments of every ``gh pr merge`` in a shell command line.

    Each item is the PR selector if one is given, followed by ``--repo <value>``
    if one is given. An empty list means the command does not merge a PR. Text
    inside a quoted argument is never a merge. Raises :class:`ValueError` when
    the command cannot be tokenised but looks like a merge, or when the selector
    starts with ``-``.
    """
    try:
        commands = _simple_commands(command)
    except ValueError as e:
        if _LOOKS_LIKE_MERGE.search(command):
            raise ValueError(
                f"cannot parse a command that looks like gh pr merge ({e})"
            ) from e
        return []
    return [args for words in commands for args in _merges_in(words)]


def _simple_commands(command, openers=None):
    text = command.replace("\r\n", "\n")
    commands, word, quote, redirected, i = [[]], None, None, False, 0

    def end_word():
        nonlocal word, redirected
        if word is not None:
            if not redirected:
                commands[-1].append(word)
            word, redirected = None, False

    while i < len(text):
        c = text[i]
        i += 1
        if quote:
            if c == quote:
                quote = None
            elif (
                c == "\\" and quote == '"' and text[i : i + 1] in ('"', "\\", "$", "`")
            ):
                word += text[i]
                i += 1
            else:
                word += c
        elif c in "'\"":
            quote, word = c, word or ""
        elif c == "\\":
            if text[i : i + 1] != "\n":
                word = (word or "") + text[i : i + 1]
            i += 1
        elif c == "#" and word is None:
            end = text.find("\n", i)
            i = len(text) if end < 0 else end
        elif c in " \t\r":
            end_word()
        elif c == "`" and text[i : i + 1] == "\n":
            end_word()
            i += 1
        elif c in "<>" or (c == "&" and text[i : i + 1] == ">"):
            if c != "&" and word and text[: i - 1].split()[-1].isdigit():
                if len(word) > 1:
                    raise ValueError(f"ambiguous redirection after {word}")
                word = None
            end_word()
            while text[i : i + 1] in ("<", ">", "&", "|"):
                i += 1
            redirected = True
        elif c in _SEPARATORS:
            if openers is not None:
                after = i
                while text[after : after + 2] == "\\\n":
                    after += 2
                glued = None if redirected else word is not None
                followed = text[after : after + 1] not in _NOT_IN_A_WORD
                openers.append((c, glued, followed))
            end_word()
            redirected = False
            commands.append([])
        else:
            word = (word or "") + c
    if quote:
        raise ValueError("no closing quotation")
    end_word()
    return commands


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


def forbidden_command(command):
    """Return ``None`` if a shell command line holds no forbidden command, else a one-line reason.

    The forbidden commands are those of PROCESS/DRIVER.md 1-5, and the reason
    names the one found:

    - ``git push --force``: a ``git push`` with ``--force``,
      ``--force-with-lease``, ``--force-if-includes`` (or an abbreviation down
      to ``--for``), a short-flag word that holds ``f``, or a ``+<refspec>``.
    - ``rm -rf``: ``rm`` with both a recursive and a force flag in any spelling
      and position, whatever the operands are; the PowerShell ``Remove-Item``
      and its aliases with ``-Recurse`` and ``-Force`` count as the same command.
    - ``gh repo delete``.

    A command is looked for in every simple command of the line, at any word, so
    ``sudo rm -rf x`` and ``env X=1 git push -f`` are found, and so is an
    unquoted mention such as ``echo rm -rf x``. The line is read in several
    ways, and one refusal is enough: cut at every separator, and with each
    ``$( )``, backtick substitution or parenthesis counted as one word, or as a
    part of the word it is glued to, of the command around it, so that the words
    after it belong to that command; with braces ignored at the ends of a word,
    and as the limits of a PowerShell script block; with a backslash before
    white space as an escape, and as the end of a Windows path. Text inside a
    quoted argument or a comment is never a forbidden command, a substitution
    inside double quotes included. A line that cannot be tokenised is refused
    when it looks like one of the three.

    Not recognised: flags or commands that only exist at run time (a variable,
    the output of a substitution, a brace expansion, ``$'...'``, standard input
    of ``xargs``); ``eval``, ``bash -c "..."``, ``iex``, ``Start-Process``,
    aliases and shell functions; an unquoted backslash path without ``.exe``; a
    force push by configuration (``remote.<name>.push=+...``, ``--mirror``); the
    ``cmd`` forms ``rd /s /q`` and ``del /s``; deletions through ``gh api``; a
    command between two quotes that the tokeniser pairs wrongly (a
    here-document body, a PowerShell backtick-escaped quote); a command inside
    ``"$( )"`` or backticks in double quotes; two PowerShell backtick escapes
    that pair up as a substitution; a ``case``
    pattern inside a substitution, whose unpaired ``)`` ends the substitution
    early; flags after a substitution that is directly followed by ``#``; a
    process substitution as the value of an option before the sub-command.
    """
    texts = dict.fromkeys((command, _BACKSLASH_BEFORE_SPACE.sub("/", command)))
    try:
        tokenised = [_tokenised(text) for text in texts]
    except ValueError as e:
        for name, patterns in _LOOKS_FORBIDDEN:
            if _holds_in_order(command, patterns):
                return (
                    f"cannot parse a command that looks like the forbidden {name} ({e})"
                )
        return None
    for commands, openers in tokenised:
        for outer in [*commands, *_outer_commands(commands, openers)]:
            unbraced = [word.strip("{}") or word for word in outer]
            for words in (unbraced, *_script_blocks(outer)):
                for i, word in enumerate(words):
                    name = _forbidden_at(word.rpartition(_GROUP)[2], words[i + 1 :])
                    if name:
                        return f"{name} is a forbidden command (PROCESS/DRIVER.md 1-5)"
    return None


def _tokenised(text):
    openers = []
    return _simple_commands(text, openers), openers


def _outer_commands(commands, openers):
    current, joined, enclosing, found = commands[0], False, [], []
    for (opener, glued, followed), words in zip(openers, commands[1:], strict=True):
        closes = opener == "`" and enclosing[-1:] and enclosing[-1][0] == "`"
        if opener == ")" and any(entry[0] == "(" for entry in enclosing):
            while enclosing[-1][0] != "(":
                _, outer, _, first = enclosing.pop()
                found.append(outer + first)
            closes = True
        if joined and (closes or opener not in "(`"):
            found.append(current)
        if closes:
            _, current, redirection, _ = enclosing.pop()
            if followed and words:
                if not redirection:
                    current = [*current[:-1], current[-1] + words[0]]
                words = words[1:]
            current, joined = current + words, True
        elif opener in "(`":
            if glued:
                current = [*current[:-1], current[-1] + _GROUP]
            elif glued is not None:
                current = [*current, _GROUP]
            enclosing.append((opener, current, glued is None, words))
            current, joined = words, False
        else:
            current, joined = words, False
    found += [current] if joined else []
    return [*found, *(outer + first for _, outer, _, first in enclosing)]


def _script_blocks(words):
    blocks = [[]]
    for word in words:
        first, *others = [word] if "${" in word else re.split("[{}]", word)
        blocks[-1] += [first] if first else []
        blocks += [[part] if part else [] for part in others]
    return blocks[1:] and blocks


def _holds_in_order(text, patterns):
    at = 0
    for pattern in patterns:
        found = re.compile(pattern, re.IGNORECASE).search(text, at)
        if not found:
            return False
        at = found.end()
    return True


def _forbidden_at(word, rest):
    if _GIT.fullmatch(word) and _is_force_push(rest):
        return _FORCE_PUSH
    if _RM.fullmatch(word) and _is_recursive_force(rest):
        return _RM_RF
    if _GH.fullmatch(word) and _split_flags(rest)[0][:2] == ["repo", "delete"]:
        return _REPO_DELETE
    return None


def _is_force_push(words):
    i = 0
    while i < len(words) and words[i].startswith("-"):
        i += 2 if words[i] in _GIT_VALUE_OPTIONS else 1
    if words[i : i + 1] != ["push"]:
        return False
    options = True
    for word in words[i + 1 :]:
        if word.startswith("+"):
            return True
        if word == "--":
            options = False
        elif options and word.startswith("--"):
            if word.startswith("--for"):
                return True
        elif options and word.startswith("-") and "f" in word[1:].partition("o")[0]:
            return True
    return False


def _is_recursive_force(words):
    recursive = force = False
    for word in words:
        if word == "--":
            break
        flag = word.partition(":")[0]
        name = flag.lstrip("-").lower()
        if not flag.startswith("-") or not name:
            continue
        if flag.startswith("--"):
            recursive |= "recursive".startswith(name)
            force |= "force".startswith(name)
        elif set(flag[1:]) <= _RM_SHORT_FLAGS:
            recursive |= "r" in name
            force |= "f" in name
        else:
            recursive |= "recurse".startswith(name)
            force |= "force".startswith(name)
    return recursive and force


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
    except Exception as e:  # noqa: BLE001
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
    proceeds. A command that holds a forbidden command
    (:func:`forbidden_command`) is refused before ``gh`` is run; otherwise every
    merge invocation in the command must pass.
    """
    tool_input = payload.get("tool_input")
    command = tool_input.get("command") if isinstance(tool_input, dict) else None
    if not isinstance(command, str):
        return None
    forbidden = forbidden_command(command)
    if forbidden:
        return forbidden
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
        description=(
            "PreToolUse hook: refuse gh pr merge unless the PR checks are green, and "
            "refuse git push --force, rm -rf and gh repo delete."
        ),
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
    except Exception as e:  # noqa: BLE001
        reason = f"the guard itself failed: {type(e).__name__}: {e}"
    if reason is None:
        return EXIT_PROCEED
    print(f"merge guard: {reason}", file=sys.stderr)
    return EXIT_REFUSE


if __name__ == "__main__":
    raise SystemExit(main())
