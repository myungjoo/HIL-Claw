import io
import json
import subprocess
import sys
from pathlib import Path

import pytest

from hilclaw import merge_guard
from hilclaw.merge_guard import (
    checks_problem,
    evaluate,
    forbidden_command,
    main,
    merge_invocations,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
URL = "https://github.com/owner/repo/pull/17"
CHECKS = ["--json", "name,bucket"]


def checks(*buckets):
    return [{"name": f"job{i}", "bucket": b} for i, b in enumerate(buckets)]


def done(stdout="", stderr="", returncode=0):
    return subprocess.CompletedProcess(["gh"], returncode, stdout, stderr)


def green():
    return done(json.dumps(checks("pass")))


class FakeGh:
    def __init__(self, *results):
        self.results = list(results)
        self.calls = []

    def __call__(self, argv, **kwargs):
        self.calls.append((argv, kwargs))
        result = self.results.pop(0) if len(self.results) > 1 else self.results[0]
        if isinstance(result, BaseException):
            raise result
        return result


def payload(command, cwd="/work/tree"):
    return {"tool_name": "Bash", "tool_input": {"command": command}, "cwd": cwd}


def run_main(monkeypatch, capsys, stdin_text, gh=None):
    gh = gh or FakeGh(AssertionError("gh must not be called"))
    monkeypatch.setattr(merge_guard.subprocess, "run", gh)
    monkeypatch.setattr(
        sys, "stdin", io.TextIOWrapper(io.BytesIO(stdin_text.encode("utf-8")))
    )
    status = main([])
    captured = capsys.readouterr()
    return status, captured.out, captured.err, gh


NOT_A_MERGE = [
    "git status",
    "gh pr view 16",
    "gh pr checks 16",
    "gh pr list",
    "gh issue view 5",
    "gh pr merged",
    "gh merge pr 17",
    "gh issue comment 5 --body pr merge 3",
    "",
    'git commit -m "run gh pr merge later"',
    'gh pr comment 17 --body "gh pr merge 17"',
    "echo 'gh pr merge'",
    'gh pr comment 17 --body "line one\ngh pr merge 17"',
    r'gh pr comment 17 --body "say \"gh pr merge 17\" now"',
    "# gh pr merge 17",
    "git status # gh pr merge 17",
    'echo "unterminated',
    "echo 'unterminated",
]

MERGES = [
    ('gh pr merge 17 --squash --body "x"', [["17"]]),
    (f"gh pr merge {URL} --squash", [[URL]]),
    (
        "gh pr merge claude/T-0007-merge-guard-hook",
        [["claude/T-0007-merge-guard-hook"]],
    ),
    ("gh pr merge", [[]]),
    ("gh pr merge --squash --delete-branch", [[]]),
    ("gh pr merge --squash 17", [["17"]]),
    ("gh pr merge --body 5 --body-file 6 --subject 7 17", [["17"]]),
    ("gh pr merge -b 5 -F 6 -t 7 -A a@b.c --match-head-commit abc 17", [["17"]]),
    ("gh pr merge --body=5 --subject=6 17", [["17"]]),
    ("gh pr merge -s -d 17", [["17"]]),
    ("gh pr merge -sd 17", [["17"]]),
    ("gh pr merge -sdb 5 17", [["17"]]),
    ("gh pr merge -b5 -t=6 17", [["17"]]),
    ("gh pr merge -- 17", [["17"]]),
    ("gh pr merge --body", [[]]),
    ("gh -R owner/repo pr merge 17", [["17", "--repo", "owner/repo"]]),
    ("gh --repo owner/repo pr merge 17", [["17", "--repo", "owner/repo"]]),
    ("gh pr merge 17 --repo owner/repo", [["17", "--repo", "owner/repo"]]),
    ("gh pr merge --repo=owner/repo --squash", [["--repo", "owner/repo"]]),
    ("gh pr merge 17 -Rowner/repo", [["17", "--repo", "owner/repo"]]),
    ("gh pr merge 17 -R", [["17"]]),
    ("cd x && gh pr merge 17 --squash", [["17"]]),
    ("gh pr ready 17; gh pr merge 17", [["17"]]),
    ("GH_TOKEN=abc gh pr merge 17", [["17"]]),
    ("gh pr merge 1 && gh pr merge 2 --repo o/r", [["1"], ["2", "--repo", "o/r"]]),
    ("gh pr merge 17|cat", [["17"]]),
    ("gh pr checks 17\ngh pr merge 17\necho done", [["17"]]),
    ("gh pr checks 17\r\ngh pr merge 17", [["17"]]),
    ("gh pr \\\n  merge 17 \\\n  --squash", [["17"]]),
    ("if true; then gh pr merge 17; fi", [["17"]]),
    ("{ gh pr merge 17; }", [["17"]]),
    ("echo $(gh pr merge 17)", [["17"]]),
    ("echo `gh pr merge 17`", [["17"]]),
    ("env GH_TOKEN=abc gh pr merge 17", [["17"]]),
    ("gh.exe pr merge 17", [["17"]]),
    ("/usr/bin/gh pr merge 17", [["17"]]),
    ("echo a#b; gh pr merge 17", [["17"]]),
    ('gh pr merge 17 --body "one\ntwo; gh pr merge 99"', [["17"]]),
    ('gh pr merge --body ";" 17', [["17"]]),
    ('gh pr merge -t "|" 17 --squash', [["17"]]),
    ("gh pr merge --body '&& (x) `y`' 17", [["17"]]),
    (r'gh pr merge --body "a \" b; c" 17', [["17"]]),
    ("gh pr merge --squash --delete-branch 2>&1", [[]]),
    ("gh pr merge 17 --squash >merge.log 2>&1", [["17"]]),
    ("gh pr merge > merge.log 17", [["17"]]),
    ("gh pr merge>/dev/null 17", [["17"]]),
    ("gh pr merge 17 &>merge.log", [["17"]]),
    ("gh pr merge 2>$null 17", [["17"]]),
    ("gh pr merge 17 2>&1 | tee merge.log", [["17"]]),
    ("gh pr merge 17 &", [["17"]]),
    ("cat <(gh pr merge 17)", [["17"]]),
    (r'"C:\Program Files\GitHub CLI\gh.exe" pr merge 17 --squash', [["17"]]),
    (r'& "C:\Program Files\GitHub CLI\gh.exe" pr merge 17', [["17"]]),
    (r"C:\tools\gh.exe pr merge 17", [["17"]]),
    ("gh.cmd pr merge 17", [["17"]]),
    ("GH.EXE pr merge 17", [["17"]]),
    ("# don't merge before the review\ngh pr merge 17", [["17"]]),
    ("echo start # gh pr merge 1\ngh pr merge 2", [["2"]]),
    ('gh pr merge "17">merge.log', [["17"]]),
    ("gh pr merge '17'>merge.log --squash", [["17"]]),
    ("gh pr merge 17&>merge.log", [["17"]]),
    ("gh pr `\n  merge 17 `\n  --squash", [["17"]]),
    ("gh pr merge `\r\n17", [["17"]]),
    ("git log 17>log.txt; git status", []),
    ("# check with `gh pr checks`\ngh pr merge 17 --squash", [["17"]]),
    ("git status # see `x`\ngh pr merge 17", [["17"]]),
    ("# use `gh`\r\ngh pr merge 17", [["17"]]),
    ("# note \\\ngh pr merge 17 --squash", [["17"]]),
    ("git status # C:\\tmp\\\ngh pr merge 17", [["17"]]),
    ("gh pr mer\\\nge 17", [["17"]]),
    ("echo `date`\ngh pr merge 17", [["17"]]),
]


@pytest.mark.parametrize("command", NOT_A_MERGE)
def test_merge_invocations_finds_no_merge(command):
    assert merge_invocations(command) == []


@pytest.mark.parametrize("command, expected", MERGES)
def test_merge_invocations_returns_the_checks_arguments(command, expected):
    assert merge_invocations(command) == expected


@pytest.mark.parametrize(
    "command, cause",
    [
        ('gh pr merge 17 --body "unterminated', "cannot parse"),
        ("gh pr merge 17 --body 'unterminated", "cannot parse"),
        ("gh pr merge -- --web", "unsupported gh pr merge selector '--web'"),
        ("gh pr merge - 17", "unsupported gh pr merge selector '-'"),
        ("gh pr merge 17>merge.log", "ambiguous redirection after 17"),
        ("git log 17>log.txt; gh pr merge 5", "ambiguous redirection after 17"),
    ],
)
def test_merge_invocations_rejects_what_it_cannot_resolve(command, cause):
    with pytest.raises(ValueError, match=cause):
        merge_invocations(command)


@pytest.mark.parametrize(
    "buckets",
    [("pass",), ("pass", "pass"), ("pass", "skipping"), ("skipping", "pass")],
)
def test_checks_problem_allows_green_checks(buckets):
    assert checks_problem(checks(*buckets)) is None


@pytest.mark.parametrize(
    "entries, cause",
    [
        (checks("pass", "fail"), "job1 (fail)"),
        (checks("pending", "pass"), "job0 (pending)"),
        (checks("pass", "cancel"), "job1 (cancel)"),
        (checks("pass", "mystery"), "job1 (mystery)"),
        (checks("fail", "pending"), "job0 (fail), job1 (pending)"),
        ([{"name": "lint"}, {"bucket": "pass"}], "lint (?)"),
        ([{"bucket": "fail"}], "? (fail)"),
        ([{"name": "lint", "bucket": None}], "lint (None)"),
        (checks("skipping"), "no check has passed (1 reported"),
        (checks("skipping", "skipping"), "no check has passed (2 reported"),
        ([], "no check has passed (0 reported"),
    ],
)
def test_checks_problem_names_the_cause(entries, cause):
    problem = checks_problem(entries)
    assert cause in problem
    assert "\n" not in problem


def test_evaluate_lets_a_green_merge_proceed_and_asks_gh_read_only():
    gh = FakeGh(green())
    assert evaluate(payload("gh pr merge 17 --squash"), run=gh) is None
    assert len(gh.calls) == 1
    argv, kwargs = gh.calls[0]
    assert argv == ["gh", "pr", "checks", "17", *CHECKS]
    assert kwargs["cwd"] == "/work/tree"
    assert kwargs["timeout"] == merge_guard.TIMEOUT_SECONDS == 60
    assert kwargs["capture_output"] is True
    assert "shell" not in kwargs


def test_evaluate_accepts_skipped_checks_next_to_a_passed_one():
    gh = FakeGh(done(json.dumps(checks("pass", "skipping"))))
    assert evaluate(payload("gh pr merge 17"), run=gh) is None


def test_evaluate_ignores_the_exit_status_of_gh():
    gh = FakeGh(done(json.dumps(checks("pass")), returncode=8))
    assert evaluate(payload("gh pr merge 17"), run=gh) is None


@pytest.mark.parametrize("command, expected", MERGES)
def test_evaluate_hands_the_recognised_arguments_to_gh(command, expected):
    gh = FakeGh(green())
    assert evaluate(payload(command), run=gh) is None
    assert [argv for argv, _ in gh.calls] == [
        ["gh", "pr", "checks", *args, *CHECKS] for args in expected
    ]


@pytest.mark.parametrize("command", NOT_A_MERGE)
def test_evaluate_does_not_call_gh_for_other_commands(command):
    gh = FakeGh(AssertionError("gh must not be called"))
    assert evaluate(payload(command), run=gh) is None
    assert gh.calls == []


@pytest.mark.parametrize(
    "other",
    [
        {"tool_name": "Edit", "tool_input": {"file_path": "a.py"}, "cwd": "/w"},
        {"tool_name": "Bash", "tool_input": {"command": 17}},
        {"tool_name": "Bash", "tool_input": "gh pr merge 17"},
        {"tool_name": "Bash"},
        {},
    ],
)
def test_evaluate_lets_payloads_without_a_command_proceed(other):
    gh = FakeGh(AssertionError("gh must not be called"))
    assert evaluate(other, run=gh) is None
    assert gh.calls == []


def test_evaluate_applies_to_any_tool_with_a_command():
    gh = FakeGh(done(json.dumps(checks("fail"))))
    reason = evaluate(
        {"tool_name": "PowerShell", "tool_input": {"command": "gh pr merge 17"}},
        run=gh,
    )
    assert "job0 (fail)" in reason


@pytest.mark.parametrize("cwd", [None, "", 5])
def test_evaluate_without_a_usable_cwd_runs_gh_in_the_current_directory(cwd):
    gh = FakeGh(green())
    request = payload("gh pr merge 17", cwd=cwd)
    if cwd is None:
        del request["cwd"]
    assert evaluate(request, run=gh) is None
    assert gh.calls[0][1]["cwd"] is None


def test_evaluate_defaults_to_subprocess_run(monkeypatch):
    gh = FakeGh(green())
    monkeypatch.setattr(merge_guard.subprocess, "run", gh)
    assert evaluate(payload("gh pr merge 17")) is None
    assert len(gh.calls) == 1


def test_evaluate_checks_every_merge_and_refuses_on_the_second():
    gh = FakeGh(green(), done(json.dumps(checks("pass", "fail"))))
    reason = evaluate(payload("gh pr merge 1 && gh pr merge 2 --repo o/r"), run=gh)
    assert "job1 (fail)" in reason
    assert "gh pr checks 2 --repo o/r" in reason
    assert [argv[3] for argv, _ in gh.calls] == ["1", "2"]


def test_evaluate_stops_at_the_first_refused_merge():
    gh = FakeGh(done(json.dumps(checks("pending"))), green())
    reason = evaluate(payload("gh pr merge 1; gh pr merge 2"), run=gh)
    assert "job0 (pending)" in reason
    assert len(gh.calls) == 1


NO_CHECKS = "no checks reported on the 'claude/T-0004' branch"
GRAPHQL = "GraphQL: Could not resolve to a PullRequest with the number of 999."

REFUSALS = [
    (done(json.dumps(checks("pass", "fail"))), "job1 (fail)"),
    (done(json.dumps(checks("pass", "pending"))), "job1 (pending)"),
    (done(json.dumps(checks("cancel", "pass"))), "job0 (cancel)"),
    (done(json.dumps(checks("pass", "mystery"))), "job1 (mystery)"),
    (done(json.dumps(checks("skipping"))), "no check has passed"),
    (done("[]"), "no check has passed (0 reported"),
    (done("", NO_CHECKS, 1), NO_CHECKS),
    (done(NO_CHECKS + "\n", "", 1), NO_CHECKS),
    (done("", GRAPHQL, 1), GRAPHQL),
    (done("", "", 1), "did not report a list of checks: no output"),
    (done(None, None, 1), "did not report a list of checks: no output"),
    (done('{"name": "job", "bucket": "pass"}'), "did not report a list of checks"),
    (done('["pass"]'), "did not report a list of checks"),
    (done('"pass"'), "did not report a list of checks"),
    (FileNotFoundError(2, "No such file or directory", "gh"), "not found"),
    (subprocess.TimeoutExpired(["gh"], 60), "timed out after 60 s"),
    (PermissionError(13, "Permission denied"), "cannot run gh pr checks: Permission"),
    (RuntimeError("boom"), "cannot run gh pr checks: RuntimeError: boom"),
]


@pytest.mark.parametrize("result, cause", REFUSALS)
def test_evaluate_refuses_and_names_the_cause(result, cause):
    reason = evaluate(payload("gh pr merge 17 --squash"), run=FakeGh(result))
    assert cause in reason
    assert "\n" not in reason


def test_evaluate_refuses_an_untokenisable_merge_without_calling_gh():
    gh = FakeGh(AssertionError("gh must not be called"))
    reason = evaluate(payload('gh pr merge 17 --body "unterminated'), run=gh)
    assert "cannot parse a command that looks like gh pr merge" in reason
    assert gh.calls == []


def test_evaluate_refuses_a_selector_that_gh_would_read_as_a_flag():
    gh = FakeGh(AssertionError("gh must not be called"))
    assert "--web" in evaluate(payload("gh pr merge -- --web"), run=gh)
    assert gh.calls == []


def test_main_lets_a_green_merge_proceed_silently(monkeypatch, capsys):
    text = json.dumps(payload("gh pr merge 17 --squash"))
    status, out, err, gh = run_main(monkeypatch, capsys, text, FakeGh(green()))
    assert (status, out, err) == (0, "", "")
    assert gh.calls[0][0] == ["gh", "pr", "checks", "17", *CHECKS]
    assert gh.calls[0][1]["cwd"] == "/work/tree"


@pytest.mark.parametrize("command", NOT_A_MERGE)
def test_main_lets_other_commands_proceed_without_gh(monkeypatch, capsys, command):
    status, out, err, gh = run_main(monkeypatch, capsys, json.dumps(payload(command)))
    assert (status, out, err) == (0, "", "")
    assert gh.calls == []


def test_main_lets_a_non_shell_tool_proceed(monkeypatch, capsys):
    edit = {"tool_name": "Edit", "tool_input": {"file_path": "a.py"}, "cwd": "/w"}
    status, out, err, gh = run_main(monkeypatch, capsys, json.dumps(edit))
    assert (status, out, err) == (0, "", "")
    assert gh.calls == []


def test_main_reads_stdin_as_utf8_whatever_the_locale(monkeypatch, capsys):
    text = json.dumps(payload('git commit -m "병합 — ok"'), ensure_ascii=False)
    monkeypatch.setattr(
        sys, "stdin", io.TextIOWrapper(io.BytesIO(text.encode("utf-8")), "ascii")
    )
    assert main([]) == 0
    assert capsys.readouterr() == ("", "")


def test_main_accepts_a_text_only_stdin(monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload("git status"))))
    assert main([]) == 0
    assert capsys.readouterr() == ("", "")


@pytest.mark.parametrize("result, cause", REFUSALS)
def test_main_refuses_with_exit_2_and_a_reason(monkeypatch, capsys, result, cause):
    status, out, err, _ = run_main(
        monkeypatch, capsys, json.dumps(payload("gh pr merge 17")), FakeGh(result)
    )
    assert status == 2
    assert out == ""
    assert err.startswith("merge guard: ")
    assert cause in err


def test_main_refuses_an_untokenisable_merge(monkeypatch, capsys):
    text = json.dumps(payload('gh pr merge 17 --body "unterminated'))
    status, out, err, gh = run_main(monkeypatch, capsys, text)
    assert (status, out) == (2, "")
    assert err.startswith("merge guard: cannot parse")
    assert gh.calls == []


@pytest.mark.parametrize(
    "text, cause",
    [
        ("", "not JSON"),
        ("gh pr merge 17", "not JSON"),
        ('{"tool_input": ', "not JSON"),
        ("[]", "not a JSON object"),
        ('"gh pr merge 17"', "not a JSON object"),
        ("null", "not a JSON object"),
        ("17", "not a JSON object"),
    ],
)
def test_main_refuses_a_payload_that_is_not_a_json_object(
    monkeypatch, capsys, text, cause
):
    status, out, err, gh = run_main(monkeypatch, capsys, text)
    assert (status, out) == (2, "")
    assert err.startswith("merge guard: ")
    assert cause in err
    assert gh.calls == []


def test_main_refuses_stdin_that_is_not_utf8(monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(b'{"a": "\xff"}')))
    assert main([]) == 2
    out, err = capsys.readouterr()
    assert out == ""
    assert "not JSON" in err


def test_main_refuses_when_the_guard_itself_fails(monkeypatch, capsys):
    def broken(_payload):
        raise RuntimeError("bug in the guard")

    monkeypatch.setattr(merge_guard, "evaluate", broken)
    status, out, err, _ = run_main(
        monkeypatch, capsys, json.dumps(payload("git status"))
    )
    assert (status, out) == (2, "")
    assert "the guard itself failed: RuntimeError: bug in the guard" in err


def test_main_takes_no_positional_argument(capsys):
    with pytest.raises(SystemExit) as usage:
        main(["17"])
    assert usage.value.code == 2
    assert capsys.readouterr().out == ""


def test_main_help_exits_0(capsys):
    with pytest.raises(SystemExit) as helped:
        main(["--help"])
    assert helped.value.code == 0
    assert "gh pr merge" in capsys.readouterr().out


def run_module(stdin_text):
    return subprocess.run(
        [sys.executable, "-m", "hilclaw.merge_guard"],
        input=stdin_text.encode("utf-8"),
        capture_output=True,
        cwd=REPO_ROOT,
        timeout=60,
        check=False,
    )


def test_module_entry_point_lets_a_non_merge_command_proceed():
    result = run_module(json.dumps(payload("git status", cwd=str(REPO_ROOT))))
    assert (result.returncode, result.stdout, result.stderr) == (0, b"", b"")


def test_module_entry_point_refuses_a_broken_payload():
    result = run_module("not json")
    assert result.returncode == 2
    assert result.stdout == b""
    assert result.stderr.startswith(b"merge guard: ")


FORCE_PUSH, RM_RF, REPO_DELETE = "git push --force", "rm -rf", "gh repo delete"

FORBIDDEN = [
    ("git push --force", FORCE_PUSH),
    ("git push --force origin main", FORCE_PUSH),
    ("git push origin main --force", FORCE_PUSH),
    ("git push --force-with-lease", FORCE_PUSH),
    ("git push --force-with-lease=main:abc origin main", FORCE_PUSH),
    ("git push --force-if-includes origin main", FORCE_PUSH),
    ("git push --forc", FORCE_PUSH),
    ("git push -f", FORCE_PUSH),
    ("git push -fu origin x", FORCE_PUSH),
    ("git push -uf origin x", FORCE_PUSH),
    ("git push origin x -f", FORCE_PUSH),
    ("git push -o ci.skip -f", FORCE_PUSH),
    ('git push "--force"', FORCE_PUSH),
    ("git -C ../other push -f", FORCE_PUSH),
    ("git -c user.name=x push --force", FORCE_PUSH),
    ("git --git-dir .git --work-tree . push -f", FORCE_PUSH),
    ("git --no-pager push -f", FORCE_PUSH),
    ("git -C push push -f", FORCE_PUSH),
    ("git push origin +main", FORCE_PUSH),
    ("git push origin +HEAD:main", FORCE_PUSH),
    ("git push -- origin +main", FORCE_PUSH),
    ("git push --no-force --force", FORCE_PUSH),
    ("git push --force --no-force", FORCE_PUSH),
    ("git.exe push -f", FORCE_PUSH),
    ("GIT.EXE push -f", FORCE_PUSH),
    ("git.cmd push -f", FORCE_PUSH),
    ("/usr/bin/git push -f", FORCE_PUSH),
    (r'"C:\Program Files\Git\cmd\git.exe" push --force', FORCE_PUSH),
    (r'& "C:\Program Files\Git\cmd\git.exe" push --force', FORCE_PUSH),
    (r"C:\tools\git.exe push -f", FORCE_PUSH),
    ("cd x && git push -f", FORCE_PUSH),
    ("git status; git push -f", FORCE_PUSH),
    ("git fetch | git push -f", FORCE_PUSH),
    ("git status\ngit push -f\necho done", FORCE_PUSH),
    ("echo $(git push -f)", FORCE_PUSH),
    ("echo `git push -f`", FORCE_PUSH),
    ("env X=1 git push -f", FORCE_PUSH),
    ("X=1 git push -f", FORCE_PUSH),
    ("if true; then git push -f; fi", FORCE_PUSH),
    ("{ git push -f; }", FORCE_PUSH),
    ("git push \\\n  --force", FORCE_PUSH),
    ("git push `\n  --force", FORCE_PUSH),
    ("git pu\\\nsh -f", FORCE_PUSH),
    ("git push -f 2>&1 | tee push.log", FORCE_PUSH),
    ("git push -f >push.log", FORCE_PUSH),
    ("# first the rebase\ngit push -f", FORCE_PUSH),
    ("echo git push -f", FORCE_PUSH),
    ("cat <<EOF\ngit push -f\nEOF", FORCE_PUSH),
    ("rm -rf x", RM_RF),
    ("rm -rf", RM_RF),
    ("rm -rf /", RM_RF),
    ("rm -fr x", RM_RF),
    ("rm -Rf x", RM_RF),
    ("rm -r -f x", RM_RF),
    ("rm -f -r x", RM_RF),
    ("rm -rvf x", RM_RF),
    ("rm -rfP x", RM_RF),
    ("rm --recursive --force x", RM_RF),
    ("rm -r --force x", RM_RF),
    ("rm --force -R x", RM_RF),
    ("rm --rec --for x", RM_RF),
    ("rm x -rf", RM_RF),
    ("rm -r x -f", RM_RF),
    ("rm -rf -- x", RM_RF),
    ('rm "-rf" x', RM_RF),
    ("sudo rm -rf x", RM_RF),
    ("command rm -rf x", RM_RF),
    ("\\rm -rf x", RM_RF),
    ("find . -name x -exec rm -rf {} +", RM_RF),
    ("ls | xargs rm -rf", RM_RF),
    ("/bin/rm -rf x", RM_RF),
    ("rm.exe -rf x", RM_RF),
    ("RM -rf x", RM_RF),
    (r"C:\tools\rm.exe -rf x", RM_RF),
    ("Remove-Item -Recurse -Force x", RM_RF),
    ("Remove-Item x -Recurse -Force", RM_RF),
    ("remove-item -rec -fo x", RM_RF),
    ("Remove-Item -Recurse:$true -Force x", RM_RF),
    ("rm -r -fo x", RM_RF),
    ("ri -Recurse -Force x", RM_RF),
    ("rd -Recurse -Force x", RM_RF),
    ("del -Recurse -Force x", RM_RF),
    ("erase -Recurse -Force x", RM_RF),
    ("rmdir -Recurse -Force x", RM_RF),
    ("cd x && rm -rf y", RM_RF),
    ("(rm -rf x)", RM_RF),
    ("echo $(rm -rf x)", RM_RF),
    ("env X=1 rm -rf x", RM_RF),
    ("if true; then rm -rf x; fi", RM_RF),
    ("rm -rf x \\\n  y", RM_RF),
    ("rm \\\n  -rf x", RM_RF),
    ("rm -rf x >rm.log 2>&1", RM_RF),
    ("echo rm -rf x", RM_RF),
    ("git rm -r -f x", RM_RF),
    ("cat <<EOF\nrm -rf x\nEOF", RM_RF),
    ("gh repo delete", REPO_DELETE),
    ("gh repo delete owner/repo", REPO_DELETE),
    ("gh repo delete owner/repo --yes", REPO_DELETE),
    ("gh repo delete --yes", REPO_DELETE),
    ("gh repo delete --yes owner/repo", REPO_DELETE),
    ("gh -R owner/repo repo delete", REPO_DELETE),
    ("gh.exe repo delete x", REPO_DELETE),
    (r"C:\tools\gh.exe repo delete x", REPO_DELETE),
    (r'"C:\Program Files\GitHub CLI\gh.exe" repo delete x', REPO_DELETE),
    ("env GH_TOKEN=a gh repo delete x", REPO_DELETE),
    ("echo $(gh repo delete x)", REPO_DELETE),
    ("gh repo \\\n  delete x", REPO_DELETE),
    ("gh repo view; gh repo delete x", REPO_DELETE),
    ("if true; then gh repo delete x; fi", REPO_DELETE),
    ("echo gh repo delete x", REPO_DELETE),
    ("git push origin $(git branch --show-current) --force", FORCE_PUSH),
    ("git push $(git remote) +main", FORCE_PUSH),
    ("git -C $(pwd) push -f", FORCE_PUSH),
    ("git push origin `git branch --show-current` -f", FORCE_PUSH),
    ("git push origin $(echo $(git branch --show-current)) -f", FORCE_PUSH),
    ("rm $(cat list.txt) -rf", RM_RF),
    ("rm -r $(cat list.txt; cat more.txt) -f", RM_RF),
    ("rm -r $((1 + 2)) -f", RM_RF),
    ("rm -r <(ls x) -f", RM_RF),
    ("Remove-Item (Join-Path $a b) -Recurse -Force", RM_RF),
    ("gh -R $(echo owner/repo) repo delete", REPO_DELETE),
    ("echo $(ls) | (cd x; rm -rf y)", RM_RF),
    ("rm.cmd -rf x", RM_RF),
    ("git push -o +x origin main", FORCE_PUSH),
    ("if (Test-Path x) { git push } else { echo +1 }", FORCE_PUSH),
    ("cp src/rm dst -r -f", RM_RF),
    ("python -m pytest -k rm -rf", RM_RF),
    ("git rm -rf --cached .", RM_RF),
    ("high repo delete", REPO_DELETE),
    ("git -C $(git rev-parse --show-toplevel)/sub push --force", FORCE_PUSH),
    ("git -C $(pwd)/repo push -f", FORCE_PUSH),
    ("git -C x$(a)y$(b)z push -f", FORCE_PUSH),
    ("git -C $(echo $(pwd))/repo push -f", FORCE_PUSH),
    ('git -C $(pwd)"/my repo" push -f', FORCE_PUSH),
    ("git -C $(pwd)\\\n  push -f", FORCE_PUSH),
    ("git --git-dir=$(pwd)/.git push -f", FORCE_PUSH),
    ("git -C (Get-Location) push -f", FORCE_PUSH),
    ("git -C `pwd`/repo push -f", FORCE_PUSH),
    ("git -C `pwd` push -f", FORCE_PUSH),
    ("gh -R $(x)/repo repo delete", REPO_DELETE),
    ("gh --repo (x) repo delete y", REPO_DELETE),
    ("rm -r $(pwd)/x -f", RM_RF),
    (r"Remove-Item C:\my` dir -Recurse -Force", RM_RF),
    ("rm -r (x -f", RM_RF),
    ("git -C x >$(mktemp) push -f", FORCE_PUSH),
    ("git -C x >$(mktemp)/log push -f", FORCE_PUSH),
    ("git -C x<(ls)y push -f", FORCE_PUSH),
    ("rm -r x 2>`mktemp` -f", RM_RF),
    ("(case $x in a)rm -rf y;; esac)", RM_RF),
    ("x=$(case $x in a)git push -f;; esac)", FORCE_PUSH),
    ("x=`case $x in a)gh repo delete y;; esac`", REPO_DELETE),
    ("echo a >$(case $x in a)rm -rf y;; esac)", RM_RF),
    ("rm -rf(x) y", RM_RF),
    ("rm -r -f(x)", RM_RF),
    ("Remove-Item -Recurse -Force(x)", RM_RF),
    ("ls | ForEach-Object {Remove-Item $_ -Recurse -Force}", RM_RF),
    ("ls | ForEach-Object { Remove-Item $_ -Recurse -Force}", RM_RF),
    ("& {git push -f}", FORCE_PUSH),
    ("{ gh repo delete}", REPO_DELETE),
    ("git -C $(pwd)\\\n/repo push -f", FORCE_PUSH),
    ("(case $x in a)rm -r pre`pwd` -f;; esac)", RM_RF),
    ("x=$(case $x in a)git -C $(pwd) push origin x --force;; esac)", FORCE_PUSH),
    (r"Remove-Item .\build\ -Recurse -Force", RM_RF),
    (r"rm .\x\ -r -fo", RM_RF),
    (r"git -C .\sub\ push --force", FORCE_PUSH),
    ("Set-Location C:\\x\\\ngit push -f", FORCE_PUSH),
    (r"gh repo view C:\x\ ; gh repo delete y", REPO_DELETE),
    ("ls | %{Remove-Item $_ -Recurse -Force}", RM_RF),
    ("ls | ForEach-Object{Remove-Item $_ -Recurse -Force}", RM_RF),
    ("try{rm -rf x}catch{}", RM_RF),
    ("if ($x) {git push -f}else{git push}", FORCE_PUSH),
    ("if ($x) {gh repo delete y}else{ls}", REPO_DELETE),
    ("rm -r ${DIR} -f", RM_RF),
    ("rm -r build/{a,b} -f", RM_RF),
    ("git push origin {a,b} --force", FORCE_PUSH),
    ("Remove-Item (Join-Path $a My` Dir) -Recurse -Force", RM_RF),
    ("git push origin (Get-Thing a` b) --force", FORCE_PUSH),
    ("rm -r x >$(a)/$(b) -f", RM_RF),
    ("git -C x >$(a)/$(b).log push -f", FORCE_PUSH),
    (r"cd C:\x\;git push -f", FORCE_PUSH),
    (r"ls .\a\|rm -rf x", RM_RF),
    (r"git -C (Resolve-Path .\b\) push -f", FORCE_PUSH),
    (r"find . -name x -exec rm -rf {} \;", RM_RF),
    ("rm -r .\\a\\\nls -Force", RM_RF),
]

NOT_FORBIDDEN = [
    "git push",
    "git push origin HEAD:main",
    "git push --delete origin claude/T-0107",
    "git push -u origin claude/T-0107",
    "git push --no-force",
    "git push --no-force-with-lease origin main",
    "git push --follow-tags",
    "git push -ofast origin main",
    "git push -o fast origin main",
    "git push origin HEAD:refs/heads/f",
    "git push -- origin -f",
    "git fetch --force",
    "git checkout -f",
    "git checkout -f feature/rm",
    "git clean -fd",
    "git reset --hard origin/main",
    "git stash push -f",
    "git -C push status -f",
    "git log --oneline -- push -f",
    "legit push -f",
    "rm file",
    "rm -f file",
    "rm -r dir",
    "rm -i -r dir",
    "rm --force file",
    "rm --recursive dir",
    "rm -r -- -f",
    "rm -f a && rm -r b",
    "rm -f a; ls -r",
    "rmdir dir",
    "rm -Force file",
    "Remove-Item file -Force -ErrorAction SilentlyContinue",
    "Remove-Item -Recurse dir",
    "Remove-Item dir -Filter x.tmp -Confirm:$false",
    "docker run --rm -f x",
    "terraform -r -f",
    "ls -rf",
    "gh repo view",
    "gh repo clone owner/repo",
    "gh repo list",
    "gh delete repo x",
    "gh issue delete 5",
    "gh pr view --repo delete",
    'git commit -m "never use rm -rf or git push --force"',
    'gh pr create --body "do not run gh repo delete here"',
    "echo 'rm -rf x'",
    'echo "git push -f"',
    'gh issue comment 5 --body "one\nrm -rf /\ngit push -f\ngh repo delete x"',
    r'git commit -m "say \"rm -rf x\" never"',
    "git status # rm -rf x",
    "# git push --force",
    "git status # gh repo delete x",
    "",
    "rm -r $(ls -f x)",
    "rm -f `ls -r x`",
    "git push origin $(git describe --force)",
    "(cd x && rm -r y) && ls -f",
    "for f in $(ls -r); do rm -f $f; done",
    "f() { rm -r x; }; ls -f",
    "case $x in a) rm -r y ;; esac; ls -f",
    "echo `ls -r` && rm -f x",
    "rm -r x) -f",
    "git -C $(pwd)/push status -f",
    "git -C $(pwd) status; git push",
    "gh --repo $(x)/delete repo view",
    "rm -r $(pwd)/-f",
    "rm -r My` Dir; ls -f",
    "ls | ForEach-Object {Remove-Item $_ -Recurse}",
    "git push origin ${BRANCH}",
    "git push \\\n  origin main",
    r"Set-Location C:\x\ ; git push",
    r"Remove-Item .\build\ -Recurse",
    "try{rm -r x}catch{ls -f}",
    "ls | %{Remove-Item $_ -Recurse}",
    "find . -name x -exec rm -r {} +",
    "> $(a)/$(b)",
    "2>$(a)/$(b) make",
    "ls && > $(a)/$(b).log",
    "< $(a)/$(b) cat",
    "echo x >$(a)$(b)`c`/d",
    r"find . -name x -exec rm -r {} \; -print",
    r"find . \( -name a -o -name b \) -exec rm -f {} \;",
]

KNOWN_MISSES = [
    'bash -c "rm -rf x"',
    "eval 'git push -f'",
    "rm $FLAGS x",
    "rm -r{f,} x",
    "git push $FLAGS origin main",
    "git -c alias.p='push -f' p",
    "git push --mirror",
    r"C:\tools\git push -f",
    r"C:\tools\rm -rf x",
    "cmd /c rd /s /q x",
    "del /s x",
    "gh api -X DELETE repos/owner/repo",
    "echo -rf x | xargs rm",
    "git push $(echo -f)",
    "git -c remote.origin.push=+refs/heads/main push",
    'iex "rm -rf x"',
    "rm $'-rf' x",
    "rm -r $(case $y in a) echo x;; esac) -f",
    "git push origin $(x)#y -f",
    "git -C <(x) push -f",
    "rm -r(x) -f",
    'out="$(git push --force 2>&1)"',
    'echo "`rm -rf x`"',
    "Remove-Item a` b -Recurse c` d -Force",
    "echo a >$(case $x in a)rm -r $(pwd) -f;; esac)",
]

UNPARSABLE_FORBIDDEN = [
    ('git push --force "unterminated', FORCE_PUSH),
    ("git push -uf 'unterminated", FORCE_PUSH),
    ('git push origin +main "unterminated', FORCE_PUSH),
    ("rm -rf 'unterminated", RM_RF),
    ('Remove-Item -Recurse -Force "unterminated', RM_RF),
    ('gh repo delete "unterminated', REPO_DELETE),
    ("git log 17>log.txt; rm -rf x", RM_RF),
    ('git push "--force" 12>x', FORCE_PUSH),
    ('rm "-rf" x 12>log', RM_RF),
    ('gh "repo" delete x 12>log', REPO_DELETE),
]

UNPARSABLE_NOT_FORBIDDEN = [
    'git push origin "unterminated',
    "rm 'unterminated",
    'gh repo view "unterminated',
    "git log 17>log.txt; git push",
]


@pytest.mark.parametrize("command, name", FORBIDDEN)
def test_forbidden_command_names_the_command(command, name):
    reason = forbidden_command(command)
    assert reason == f"{name} is a forbidden command (PROCESS/DRIVER.md 1-5)"


@pytest.mark.parametrize("command", NOT_FORBIDDEN + NOT_A_MERGE + KNOWN_MISSES)
def test_forbidden_command_finds_none(command):
    assert forbidden_command(command) is None


@pytest.mark.parametrize("command, expected", MERGES)
def test_forbidden_command_leaves_merges_alone(command, expected):
    assert forbidden_command(command) is None


@pytest.mark.parametrize("command, name", UNPARSABLE_FORBIDDEN)
def test_forbidden_command_refuses_what_it_cannot_parse(command, name):
    reason = forbidden_command(command)
    assert reason.startswith(
        f"cannot parse a command that looks like the forbidden {name} ("
    )
    assert "\n" not in reason


@pytest.mark.parametrize("command", UNPARSABLE_NOT_FORBIDDEN)
def test_forbidden_command_lets_other_unparsable_commands_proceed(command):
    assert forbidden_command(command) is None


@pytest.mark.parametrize("command, name", FORBIDDEN + UNPARSABLE_FORBIDDEN)
def test_evaluate_refuses_a_forbidden_command_without_calling_gh(command, name):
    gh = FakeGh(AssertionError("gh must not be called"))
    assert name in evaluate(payload(command), run=gh)
    assert gh.calls == []


@pytest.mark.parametrize(
    "command", NOT_FORBIDDEN + KNOWN_MISSES + UNPARSABLE_NOT_FORBIDDEN
)
def test_evaluate_lets_commands_that_are_not_forbidden_proceed(command):
    gh = FakeGh(AssertionError("gh must not be called"))
    assert evaluate(payload(command), run=gh) is None
    assert gh.calls == []


@pytest.mark.parametrize(
    "command, name",
    [
        ("gh pr merge 17 --squash && git push --force", FORCE_PUSH),
        ("rm -rf x; gh pr merge 17 --squash", RM_RF),
        ("gh pr merge 17 --squash; gh repo delete x", REPO_DELETE),
        ('gh pr merge 17 --body "unterminated; rm -rf x', RM_RF),
    ],
)
def test_evaluate_refuses_a_forbidden_command_before_checking_a_merge(command, name):
    gh = FakeGh(green())
    assert name in evaluate(payload(command), run=gh)
    assert gh.calls == []


@pytest.mark.parametrize("tool_name", ["PowerShell", "Edit", None])
def test_evaluate_refuses_a_forbidden_command_of_any_tool(tool_name):
    request = {"tool_name": tool_name, "tool_input": {"command": "rm -rf x"}}
    assert RM_RF in evaluate(request, run=FakeGh(AssertionError("no gh")))


@pytest.mark.parametrize(
    "other",
    [
        {"tool_name": "Write", "tool_input": {"content": "rm -rf x"}},
        {"tool_name": "Bash", "tool_input": {"command": ["rm", "-rf", "x"]}},
        {"tool_name": "Bash", "tool_input": "git push --force"},
        {"tool_name": "Bash", "command": "gh repo delete x"},
    ],
)
def test_evaluate_reads_only_a_string_command(other):
    assert evaluate(other, run=FakeGh(AssertionError("no gh"))) is None


@pytest.mark.parametrize("command, name", FORBIDDEN + UNPARSABLE_FORBIDDEN)
def test_main_refuses_a_forbidden_command(monkeypatch, capsys, command, name):
    status, out, err, gh = run_main(monkeypatch, capsys, json.dumps(payload(command)))
    assert (status, out) == (2, "")
    assert err.startswith("merge guard: ")
    assert name in err
    assert err.count("\n") == 1
    assert gh.calls == []


@pytest.mark.parametrize("command", NOT_FORBIDDEN + KNOWN_MISSES)
def test_main_lets_commands_that_are_not_forbidden_proceed(
    monkeypatch, capsys, command
):
    status, out, err, gh = run_main(monkeypatch, capsys, json.dumps(payload(command)))
    assert (status, out, err) == (0, "", "")
    assert gh.calls == []


def test_main_refuses_a_forbidden_command_next_to_a_green_merge(monkeypatch, capsys):
    text = json.dumps(payload("gh pr merge 17 --squash && git push -f"))
    status, out, err, gh = run_main(monkeypatch, capsys, text, FakeGh(green()))
    assert (status, out) == (2, "")
    assert FORCE_PUSH in err
    assert gh.calls == []


def test_main_refuses_when_the_forbidden_command_check_fails(monkeypatch, capsys):
    def broken(_command):
        raise RuntimeError("bug in the check")

    monkeypatch.setattr(merge_guard, "forbidden_command", broken)
    status, out, err, gh = run_main(
        monkeypatch, capsys, json.dumps(payload("git status"))
    )
    assert (status, out) == (2, "")
    assert "the guard itself failed: RuntimeError: bug in the check" in err
    assert gh.calls == []


def test_main_help_names_the_forbidden_commands(capsys):
    with pytest.raises(SystemExit) as helped:
        main(["--help"])
    assert helped.value.code == 0
    shown = " ".join(capsys.readouterr().out.split())
    assert all(name in shown for name in (FORCE_PUSH, RM_RF, REPO_DELETE))


@pytest.mark.parametrize(
    "command, name",
    [
        ("git push --force", FORCE_PUSH),
        ("rm -rf x", RM_RF),
        ("gh repo delete x", REPO_DELETE),
    ],
)
def test_module_entry_point_refuses_a_forbidden_command(command, name):
    result = run_module(json.dumps(payload(command, cwd=str(REPO_ROOT))))
    assert result.returncode == 2
    assert result.stdout == b""
    assert result.stderr.startswith(b"merge guard: " + name.encode())


CLAUDE = "claude"
BRANCH_MERGE = "gh pr merge claude/T-0151-x --squash"

CLAUDE_STARTS = [
    "claude",
    'claude -p "x"',
    "claude --print x",
    "claude auth status",
    "claude --version",
    "claude mcp list",
    "claude -p x --mcp-config f --strict-mcp-config",
    "claude.exe -p x",
    "claude.cmd -p x",
    "claude.bat -p x",
    "claude.ps1 -p x",
    "CLAUDE -p x",
    "Claude.EXE --version",
    "/usr/local/bin/claude -p x",
    "~/.local/bin/claude -p x",
    "./claude --version",
    "C:/tools/claude.exe -p x",
    r"C:\tools\claude.exe -p x",
    r'"C:\Users\me\.local\bin\claude.exe" -p x',
    r'& "C:\Program Files\Claude\claude.exe" -p x',
    '"$HOME/.local/bin/claude" -p x',
    "'claude' -p x",
    "\\claude -p x",
    "git status; claude -p x",
    "cd x && claude -p x",
    "false || claude -p x",
    "echo x | claude -p",
    "git status\nclaude -p x\necho done",
    "git status\r\nclaude -p x",
    "echo $(claude -p x)",
    "out=$(claude -p x)",
    "echo `claude -p x`",
    "(claude -p x)",
    "cat <(claude -p x)",
    "claude \\\n  -p x",
    "claude `\n  -p x",
    "clau\\\nde -p x",
    "X=1 claude -p x",
    "X=1 Y=2 claude -p x",
    "X=$(pwd) claude -p x",
    "X=`pwd` claude -p x",
    "$(npm bin)/claude -p x",
    "$out = claude -p x",
    "claude -p x >out.log 2>&1",
    "claude -p x &",
    "# first\nclaude -p x",
    "if true; then claude -p x; fi",
    "if claude -p x; then echo ok; fi",
    "if false; then :; else claude -p x; fi",
    "for f in a b; do claude -p $f; done",
    "while claude -p x; do :; done",
    "! claude -p x",
    "{ claude -p x; }",
    "f() { claude -p x; }; f",
    "& {claude -p x}",
    "ls | %{claude -p $_}",
    "if ($x) {claude -p x}else{ls}",
    "try{claude -p x}catch{}",
    "case $x in a) claude -p x;; esac",
    "env claude -p x",
    "env X=1 claude -p x",
    "env -i X=1 claude -p x",
    "env -u X claude -p x",
    "/usr/bin/env claude -p x",
    "sudo claude -p x",
    "sudo -u root claude -p x",
    "sudo -Hu root claude -p x",
    "sudo -E env X=1 nohup claude -p x",
    "command claude -p x",
    "command -p claude -p x",
    "exec claude -p x",
    "exec -a name claude -p x",
    "nohup claude -p x &",
    "time claude -p x",
    "time -p claude -p x",
    "timeout 60 claude -p x",
    "timeout -k 5 2.5m claude -p x",
    "nice -n 5 claude -p x",
    "eval claude -p x",
    "ls | xargs claude -p",
    "ls | xargs -n 1 claude -p",
    "ls | xargs -I {} claude -p {}",
    "find . -name x -exec claude -p {} +",
    r"find . -name x -execdir claude -p {} \;",
    "npx claude -p x",
    "npx -y @anthropic-ai/claude-code -p x",
    "npx @anthropic-ai/claude-code@latest -p x",
    "npx -p @anthropic-ai/claude-code claude -p x",
    "wsl claude -p x",
    "wsl -d Ubuntu -- claude -p x",
    "wsl -e bash -lc claude",
    "bash -c claude",
    "cmd /c claude -p x",
    "cmd.exe /c start claude",
    "powershell -NoProfile -Command claude -p x",
    "pwsh -c claude",
    "Start-Process claude -ArgumentList '-p x'",
    "Start-Process -FilePath claude.exe",
    "start claude",
    "saps claude",
    "x=$(case $y in a) claude -p x;; esac)",
    "ls | xargs -I{} claude -p {}",
    "sudo -uroot claude -p x",
    "sudo -g wheel -uroot claude -p x",
    "timeout -k5 10 claude -p x",
    "bash -eo pipefail -c claude",
    "npx.cmd claude -p x",
    "winpty claude -p x",
    "$out=claude -p x",
    "Start-Process -FilePath C:/tools/claude.exe",
    "try{claude}catch{}",
    "if($x){claude}else{}",
    "%{claude}{}",
]

CLAUDE_FALSE_REFUSALS = [
    "/tmp/x/claude --version",
    "cat <<EOF\nclaude -p x\nEOF",
    "echo a{claude}",
    "myclaude.exe -p x",
    "sh claude",
    "cmd /c echo claude",
    "powershell -Command Get-Command claude",
    "Start-Process notepad -ArgumentList claude",
    "cat <<EOF\nsee (claude) and `claude` here\nEOF",
    'cat <<EOF\ncall f("claude") now\nEOF',
    "cat <<EOF\nClaude Code is the program\nEOF",
    "cmd /c dir claude",
    "powershell -Command Test-Path C:/tools/claude",
    'echo "-exec" claude',
    "sudo -l claude",
]

NOT_A_CLAUDE_START = [
    "git checkout -b claude/T-0151-x",
    "git switch claude/T-0151-x",
    "git push -u origin claude/T-0151-x",
    "git push origin --delete claude/T-0151-x",
    "git branch -d claude/T-0151-x",
    "gh pr list --head claude/T-0151-x",
    "git ls-remote origin 'claude/T-*'",
    "ls .claude/agents",
    "cat .claude/skills/dev-item-address/SKILL.md",
    "cat CLAUDE.md",
    "git add CLAUDE.md",
    "git diff origin/main -- .claude",
    "ls ~/.claude",
    "python tools/claude_stub.py",
    "pip show claude-agent-sdk",
    "cat claude.md",
    "ls /tmp/claude/x/scratchpad",
    "python -m pytest",
    "python -m pytest tests/test_merge_guard.py -k claude",
    'git commit -m "never start claude -p"',
    'gh pr create --body "the guard refuses claude auth status too"',
    "echo 'claude -p x'",
    'echo "claude"',
    "git status # claude -p",
    "# claude -p x",
    'gh issue comment 5 --body "one\nclaude -p x\ntwo"',
    r'git commit -m "say \"claude -p x\" never"',
    "grep -rn claude .",
    "git log --author claude",
    "which claude",
    "where claude",
    "where.exe claude",
    "command -v claude",
    "command -V claude",
    "command -pv claude",
    "type claude",
    "Get-Command claude",
    "echo claude",
    "gh pr list --search claude",
    "git ls-files | xargs grep -l claude",
    "find . -name x -exec grep -l claude {} +",
    "sudo grep claude x",
    "env X=1 grep claude x",
    "time grep -rn claude .",
    "timeout 60 grep claude x",
    "bash run.sh claude",
    "wsl which claude",
    "echo $(date) claude",
    "echo `date` claude",
    "git log --author=$(git config user.name) claude",
    "git diff HEAD@{1} claude",
    "for b in claude codex; do echo $b; done",
    "test $x = claude",
    "[ $name = claude ]",
    "npm install -g @anthropic-ai/claude-code",
    "npm view @anthropic-ai/claude-code version",
    "npx prettier claude.md",
    "claude/T-0151-x",
    "claude-code --version",
    "claudette -p x",
    "notclaude -p x",
    ".claude/hooks/check.sh",
    "ls /tmp/claude",
    "cd ~/.claude && ls",
    "echo ${claude}",
    "echo {claude,codex}",
    "X=claude",
    "export CLAUDE=claude",
    "git -C claude status",
    "Start-Process notepad claude.md",
    "cmd /c dir .claude",
    "start .",
    'git commit -m "fix {claude} placeholder"',
    "echo '{claude}'",
    "jq -n '{claude}'",
    "sed 's/{claude}/x/' f",
    "ls | xargs -I '{}' echo claude",
    'powershell -Command "Get-Command claude.exe"',
    'powershell -Command "Test-Path C:/tools/claude"',
    "git commit -m \"$(cat <<'EOF'\nclaude is refused (claude)\nEOF\n)\"",
    "cat <<EOF\nCo-Authored-By: Claude\nEOF",
    "sudo -u claude ls",
    "sudo -uclaude ls",
]

CLAUDE_KNOWN_MISSES = [
    'bash -c "claude -p x"',
    "sh -lc 'claude -p x'",
    'cmd /c "claude -p x"',
    'powershell -Command "claude -p x"',
    "eval 'claude -p x'",
    'iex "claude -p x"',
    "$CLAUDE -p x",
    "c=claude; $c -p x",
    "alias c=claude",
    "node /usr/lib/node_modules/@anthropic-ai/claude-code/cli.js -p x",
    "npm exec @anthropic-ai/claude-code -- -p x",
    "bunx @anthropic-ai/claude-code -p x",
    "python -c \"import subprocess; subprocess.run(['claude', '-p', 'x'])\"",
    "python tools/run_child.py",
    r"C:\tools\claude -p x",
    "sudo --chroot d claude -p x",
    "doas claude -p x",
    "echo claude | xargs -I{} {} -p x",
    'out="$(claude -p x)"',
    'echo "`claude -p x`"',
    "echo $(case $y in a) claude -p x;; esac)",
    "trap 'claude -p x' EXIT",
    "cp /usr/local/bin/claude /tmp/cc && /tmp/cc -p x",
    "case $x in (a) claude -p x;; esac",
    "$(true) claude -p x",
    "$EMPTY claude -p x",
    r"C:\Windows\System32\cmd.exe /c claude -p x",
    r'Start-Process "C:\Program Files\Claude\claude.exe"',
    ". claude -p x",
]

UNPARSABLE_CLAUDE = [
    'claude -p "unterminated',
    "claude -p 'unterminated",
    'claude.exe -p "unterminated',
    '/usr/local/bin/claude -p "unterminated',
    'git status; claude -p "unterminated',
    'cd x && X=1 claude -p "unterminated',
    'echo $(claude -p "unterminated)',
    'git status\nclaude -p "unterminated',
    'git status\r\nCLAUDE -p "unterminated',
    "git log 17>log.txt; claude -p x",
    'echo "a; claude -p x',
    "cat <<EOF\nit's (Claude Code) here\nEOF",
    r'"C:\Program Files\Claude\claude.exe" -p "unterminated',
    '$out = claude -p "unterminated',
]

UNPARSABLE_NOT_CLAUDE = [
    'git commit -m "never start claude -p',
    "echo 'claude is the program",
    'git checkout "claude/T-0151-x',
    "git log 17>log.txt; git switch claude/T-0151-x",
    "cat 'CLAUDE.md",
    'grep -rn claude "unterminated',
    'sudo claude -p "unterminated',
    "cat <<EOF\nit's Co-Authored-By: Claude\nEOF",
    'echo "notes/claude are here',
]

CLAUDE_REFUSED = CLAUDE_STARTS + CLAUDE_FALSE_REFUSALS
CLAUDE_PROCEEDS = NOT_A_CLAUDE_START + CLAUDE_KNOWN_MISSES + UNPARSABLE_NOT_CLAUDE


@pytest.mark.parametrize("command", CLAUDE_REFUSED)
def test_forbidden_command_names_a_start_of_claude(command):
    reason = forbidden_command(command)
    assert reason == "claude is a forbidden command (PROCESS/DRIVER.md 1-5)"


@pytest.mark.parametrize("command", [*CLAUDE_PROCEEDS, BRANCH_MERGE])
def test_forbidden_command_finds_no_start_of_claude(command):
    assert forbidden_command(command) is None


@pytest.mark.parametrize("command", UNPARSABLE_CLAUDE)
def test_forbidden_command_refuses_an_unparsable_start_of_claude(command):
    reason = forbidden_command(command)
    assert reason.startswith(
        "cannot parse a command that looks like the forbidden claude ("
    )
    assert "\n" not in reason


@pytest.mark.parametrize(
    "command, name",
    [
        ("claude -p x; rm -rf y", RM_RF),
        ("git push --force && claude -p x", FORCE_PUSH),
        ("claude -p $(gh repo delete x)", REPO_DELETE),
        ('claude -p "unterminated; rm -rf y', RM_RF),
    ],
)
def test_forbidden_command_names_one_of_the_three_before_claude(command, name):
    assert name in forbidden_command(command)
    assert CLAUDE not in forbidden_command(command)


@pytest.mark.parametrize("command", CLAUDE_REFUSED + UNPARSABLE_CLAUDE)
def test_evaluate_refuses_a_start_of_claude_without_calling_gh(command):
    gh = FakeGh(AssertionError("gh must not be called"))
    assert CLAUDE in evaluate(payload(command), run=gh)
    assert gh.calls == []


@pytest.mark.parametrize("command", CLAUDE_PROCEEDS)
def test_evaluate_lets_commands_that_start_no_claude_proceed(command):
    gh = FakeGh(AssertionError("gh must not be called"))
    assert evaluate(payload(command), run=gh) is None
    assert gh.calls == []


def test_evaluate_treats_a_branch_named_claude_as_a_merge_selector():
    gh = FakeGh(green())
    assert evaluate(payload(BRANCH_MERGE), run=gh) is None
    assert [argv for argv, _ in gh.calls] == [
        ["gh", "pr", "checks", "claude/T-0151-x", *CHECKS]
    ]


@pytest.mark.parametrize(
    "command",
    [
        "gh pr merge 17 --squash && claude -p x",
        "claude -p x; gh pr merge 17 --squash",
        'gh pr merge 17 --body "unterminated; claude -p x',
    ],
)
def test_evaluate_refuses_a_start_of_claude_before_checking_a_merge(command):
    gh = FakeGh(green())
    assert CLAUDE in evaluate(payload(command), run=gh)
    assert gh.calls == []


@pytest.mark.parametrize("tool_name", ["PowerShell", "Edit", None])
def test_evaluate_refuses_a_start_of_claude_of_any_tool(tool_name):
    request = {"tool_name": tool_name, "tool_input": {"command": "claude -p x"}}
    assert CLAUDE in evaluate(request, run=FakeGh(AssertionError("no gh")))


@pytest.mark.parametrize(
    "other",
    [
        {"tool_name": "Write", "tool_input": {"content": "claude -p x"}},
        {"tool_name": "Bash", "tool_input": {"command": ["claude", "-p", "x"]}},
        {"tool_name": "Bash", "tool_input": "claude -p x"},
        {"tool_name": "Bash", "command": "claude -p x"},
    ],
)
def test_evaluate_reads_a_start_of_claude_only_from_a_string_command(other):
    assert evaluate(other, run=FakeGh(AssertionError("no gh"))) is None


@pytest.mark.parametrize("command", CLAUDE_REFUSED + UNPARSABLE_CLAUDE)
def test_main_refuses_a_start_of_claude(monkeypatch, capsys, command):
    status, out, err, gh = run_main(monkeypatch, capsys, json.dumps(payload(command)))
    assert (status, out) == (2, "")
    assert err.startswith("merge guard: ")
    assert CLAUDE in err
    assert err.count("\n") == 1
    assert gh.calls == []


@pytest.mark.parametrize("command", CLAUDE_PROCEEDS)
def test_main_lets_commands_that_start_no_claude_proceed(monkeypatch, capsys, command):
    status, out, err, gh = run_main(monkeypatch, capsys, json.dumps(payload(command)))
    assert (status, out, err) == (0, "", "")
    assert gh.calls == []


def test_main_lets_a_green_merge_of_a_branch_named_claude_proceed(monkeypatch, capsys):
    text = json.dumps(payload(BRANCH_MERGE))
    status, out, err, gh = run_main(monkeypatch, capsys, text, FakeGh(green()))
    assert (status, out, err) == (0, "", "")
    assert len(gh.calls) == 1


def test_main_refuses_a_start_of_claude_next_to_a_green_merge(monkeypatch, capsys):
    text = json.dumps(payload("gh pr merge 17 --squash && claude -p x"))
    status, out, err, gh = run_main(monkeypatch, capsys, text, FakeGh(green()))
    assert (status, out) == (2, "")
    assert CLAUDE in err
    assert gh.calls == []


@pytest.mark.parametrize("text", ['"claude -p x"', '["claude", "-p", "x"]'])
def test_main_refuses_a_payload_with_claude_that_is_no_object(
    monkeypatch, capsys, text
):
    status, out, err, gh = run_main(monkeypatch, capsys, text)
    assert (status, out) == (2, "")
    assert "not a JSON object" in err
    assert gh.calls == []


def test_main_refuses_when_the_check_for_claude_fails(monkeypatch, capsys):
    def broken(_words):
        raise RuntimeError("bug in the claude check")

    monkeypatch.setattr(merge_guard, "_starts_claude", broken)
    status, out, err, gh = run_main(
        monkeypatch, capsys, json.dumps(payload("git status"))
    )
    assert (status, out) == (2, "")
    assert "the guard itself failed: RuntimeError: bug in the claude check" in err
    assert gh.calls == []


def test_main_help_names_the_start_of_claude(capsys):
    with pytest.raises(SystemExit) as helped:
        main(["--help"])
    assert helped.value.code == 0
    assert "a start of claude" in " ".join(capsys.readouterr().out.split())


def test_module_entry_point_refuses_a_start_of_claude():
    result = run_module(json.dumps(payload("claude -p x", cwd=str(REPO_ROOT))))
    assert result.returncode == 2
    assert result.stdout == b""
    assert result.stderr.startswith(b"merge guard: claude is a forbidden command")
