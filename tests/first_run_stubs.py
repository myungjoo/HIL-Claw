"""The stub ``claude`` and the stub ``docker`` of the first-run end-to-end tests (PLAN P2-5; D16).

Test code, not a test file. :func:`install` writes three launchers into a
``bin`` directory that the test puts alone on ``PATH``: ``claude`` and
``docker`` start this file as a program, ``git`` hands on to the machine's
``git``. No real ``claude`` or ``docker`` is started and none is needed.

The stub ``claude`` answers ``claude auth status`` and the self-check session
as the stub of ``tests/test_turn_start.py`` does. A turn session starts the
server named in its ``--mcp-config`` file, speaks MCP to it over stdio and
replays, in order, the tool requests that ``orchestration/round-manager.md``
and the agent definitions prescribe for the run's state: a script of the
definitions, round 0 and the rounds >= 1, with no judgement beyond the
branches they state. Where a definition leaves a choice to the agent (the
techniques, the hypothesis, the pairs of a verdict), the scenario fixes it.
Before every request it runs the matching ``PreToolUse`` hooks of the
session's ``.claude/settings.json`` with the hook input a session gives, and
at the end of the session the ``Stop`` hook. Every request, hook and answer is
appended to the session log. Like a ``-p`` session it writes its last reply
to its standard output.

The stub ``docker`` answers ``version`` and the forced removals, writes the
test's kernel of the round the scratch's spec names into that scratch
without starting anything, and runs a stand-in build or process container on
this machine: the bind-mounted build directory is the container's
``/build``, ``clang`` is the host ``clang`` found before ``PATH`` was
narrowed, builds and processes run with that earlier ``PATH`` as a container
runs with its image's (clang 21 finds the linker on ``PATH``), and the waiter runs in a new user and PID namespace made by
``unshare`` where that works. Where it does not, the timing executable runs
directly and the stub writes the waiter's last line from the host's figure
for the child.
"""

import json
import os
import re
import subprocess
import sys
import uuid
from pathlib import Path

PREFIX = "mcp__hilclaw__"
CONFIG = "stubs.json"
NAMESPACE = ("--user", "--pid", "--fork", "--mount-proc", "--kill-child")
ROUND_MANAGER = "round-manager"
SELECTOR_SKIPS = (
    "verdicts_missing",
    "verdicts_invalid",
    "verdicts_unsupported",
    "bad_result",
)
WRITTEN = "written"
FIRST_STATE = {
    "schema_version": 1,
    "round": 0,
    "budget_spent": {"totals": {}, "position": 0, "open_steps": []},
}
_RUN_ID = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}")
_LEAD = "Your run id is "
_TUPLE = ("run_id", "round", "candidate", "attempt")
_EXACT = re.compile(r"[A-Za-z0-9_|]+")
_REFERENCE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def install(directory, scenario):
    """Write the launchers and the scenario into ``directory``; return the launchers' paths."""
    directory = Path(directory)
    scenario = {**scenario, "image_path": os.environ.get("PATH", os.defpath)}
    (directory / CONFIG).write_text(json.dumps(scenario), encoding="utf-8")
    me = Path(__file__).resolve()
    config = (directory / CONFIG).resolve()
    made = {}
    for name, target in (
        ("claude", f"'{sys.executable}' '{me}' claude '{config}'"),
        ("docker", f"'{sys.executable}' '{me}' docker '{config}'"),
        ("git", f"'{scenario['git']}'"),
    ):
        launcher = directory / name
        launcher.write_text(f'#!/bin/sh\nexec {target} "$@"\n', encoding="utf-8")
        launcher.chmod(0o755)
        made[name] = launcher
    return made


def read_log(path):
    """Return the entries of an ndjson log, or an empty list when there is none."""
    path = Path(path)
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _scenario():
    return json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))


def _append(path, entry):
    with open(path, "a", encoding="utf-8") as file:
        file.write(json.dumps(entry) + "\n")


# --- claude ---


def _option(argv, name):
    return argv[argv.index(name) + 1]


def _check_session(argv, scenario):
    sys.path.insert(0, scenario["repo"])
    from hilclaw import selfcheck_stream as names

    check = scenario["check"]
    config = json.loads(Path(_option(argv, "--mcp-config")).read_text("utf-8"))
    entry = config["mcpServers"][names.SERVER_NAME]
    allowed = _option(argv, "--allowedTools").split(",")
    server = _Server(entry)
    listed, reply = [], []
    server.ask("initialize", _hello())
    if check["upto"] in ("list", "call"):
        server.notify("notifications/initialized")
        for tool in server.ask("tools/list")["result"]["tools"]:
            listed.append(names.TOOL_PREFIX + tool["name"])
    if check["upto"] == "call":
        for tool in listed:
            if tool in allowed:
                name = tool[len(names.TOOL_PREFIX) :]
                answer = server.ask("tools/call", {"name": name})
                reply.extend(block["text"] for block in answer["result"]["content"])
    server.close()
    named = {
        names.SERVER_NAME_KEY: names.SERVER_NAME,
        names.SERVER_STATUS_KEY: check["status"],
    }
    for event in (
        {
            names.EVENT_KIND_KEY: names.INIT_KIND,
            names.EVENT_SUBKIND_KEY: names.INIT_SUBKIND,
            names.SERVERS_KEY: [named],
            names.TOOLS_KEY: listed,
        },
        {names.EVENT_KIND_KEY: names.RESULT_KIND, names.REPLY_KEY: " and ".join(reply)},
    ):
        sys.stdout.write(json.dumps(event) + "\n")
    sys.stdout.flush()
    return check["exit"]


def _hello():
    return {
        "protocolVersion": "2025-06-18",
        "capabilities": {},
        "clientInfo": {"name": "stub-claude", "version": "0.0.0-stub"},
    }


class _Server:
    def __init__(self, entry):
        environment = dict(os.environ)
        for name, value in entry.get("env", {}).items():
            environment[name] = _REFERENCE.sub(
                lambda found: os.environ.get(found[1], ""), value
            )
        self.process = subprocess.Popen(
            [entry["command"], *entry["args"]],
            env=environment,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
        )
        self.number = 0

    def notify(self, method):
        self._send({"jsonrpc": "2.0", "method": method})

    def ask(self, method, params=None):
        self.number += 1
        message = {"jsonrpc": "2.0", "id": self.number, "method": method}
        if params is not None:
            message["params"] = params
        self._send(message)
        return json.loads(self.process.stdout.readline())

    def _send(self, message):
        self.process.stdin.write(json.dumps(message).encode() + b"\n")
        self.process.stdin.flush()

    def close(self):
        self.process.stdin.close()
        self.process.wait()


class _Agent:
    def __init__(self, kind, message=None):
        self.kind = kind
        self.message = message
        self.agent_id = None if kind == ROUND_MANAGER else "stub-" + uuid.uuid4().hex


class _Answer:
    def __init__(self, result=None, kind=None, refused=False):
        self.result = result
        self.kind = kind
        self.refused = refused

    @property
    def ok(self):
        return self.kind is None and not self.refused


class _EndSession(Exception):
    pass


def _matches(matcher, tool):
    if matcher in ("", "*"):
        return True
    if _EXACT.fullmatch(matcher):
        return tool in matcher.split("|")
    return re.search(matcher, tool) is not None


class _Turn:
    def __init__(self, argv, scenario, number):
        self.number = number
        self.turn = scenario["turns"][min(number, len(scenario["turns"])) - 1]
        self.log = scenario["log"]
        self.cwd = os.getcwd()
        self.session_id = str(uuid.uuid4())
        self.prompt = _option(argv, "-p")
        config = json.loads(Path(_option(argv, "--mcp-config")).read_text("utf-8"))
        self.entry = config["mcpServers"]["hilclaw"]
        settings = Path(".claude", "settings.json")
        self.settings = json.loads(settings.read_text(encoding="utf-8"))["hooks"]
        self.server = None
        self.tools = ()
        self.commit_failed = False
        self.run_id = None
        self.replies = []
        self.main = _Agent(ROUND_MANAGER)
        self.choices = scenario.get("choices", {})

    def write(self, entry):
        _append(self.log, {"turn": self.number, **entry})

    def report(self, text):
        self.replies.append(text)
        self.write({"report": text})

    # The session's tool requests and hooks.

    def hook_input(self, event, agent, **members):
        given = {
            "session_id": self.session_id,
            "cwd": self.cwd,
            "permission_mode": "dontAsk",
            "hook_event_name": event,
            **members,
        }
        if agent is not None and agent.agent_id is not None:
            given["agent_id"] = agent.agent_id
            given["agent_type"] = agent.kind
        return given

    def run_hook(self, hook, given):
        environment = {**os.environ, "CLAUDE_PROJECT_DIR": self.cwd}
        try:
            done = subprocess.run(
                [hook["command"], *hook.get("args", [])],
                input=json.dumps(given).encode(),
                capture_output=True,
                cwd=self.cwd,
                env=environment,
                timeout=hook.get("timeout", 600),
                check=False,
            )
        except subprocess.TimeoutExpired:
            return {"status": None, "stderr": "timed out"}
        return {"status": done.returncode, "stderr": done.stderr.decode("utf-8")}

    def pre_tool_use(self, agent, tool, arguments):
        ran = []
        for index, entry in enumerate(self.settings.get("PreToolUse", [])):
            if not _matches(entry.get("matcher", ""), tool):
                continue
            for hook in entry["hooks"]:
                given = self.hook_input(
                    "PreToolUse",
                    agent,
                    tool_name=tool,
                    tool_input=arguments,
                    tool_use_id="toolu_stub_" + uuid.uuid4().hex,
                )
                outcome = self.run_hook(hook, given)
                blocks = outcome["status"] == 2 or (
                    outcome["status"] != 0 and hook.get("onFailure") == "block"
                )
                ran.append({"entry": index, **outcome, "blocks": blocks})
        return ran

    def call(self, agent, name, **arguments):
        tool = PREFIX + name
        hooks = self.pre_tool_use(agent, tool, arguments)
        entry = {
            "agent": agent.kind,
            "agent_id": agent.agent_id,
            "tool": tool,
            "arguments": arguments,
            "hooks": hooks,
        }
        if any(hook["blocks"] for hook in hooks):
            self.write({**entry, "refused": True})
            return _Answer(refused=True)
        if tool not in self.tools:
            self.write({**entry, "refused": False, "unlisted": True})
            return _Answer(kind="unlisted")
        answer = self.server.ask("tools/call", {"name": name, "arguments": arguments})
        text = answer["result"]["content"][0]["text"]
        value = json.loads(text)
        error = answer["result"].get("isError") is True
        self.write({**entry, "refused": False, "error": error, "answer": value})
        if error:
            return _Answer(kind=value["error"]["kind"])
        return _Answer(result=value)

    def delegate(self, kind, message, script):
        definition = Path(".claude", "agents", f"{kind}.md")
        hooks = self.pre_tool_use(self.main, "Agent", {"subagent_type": kind})
        self.write(
            {
                "agent": ROUND_MANAGER,
                "delegate": kind,
                "message": message,
                "defined": definition.is_file(),
                "hooks": hooks,
            }
        )
        agent = _Agent(kind, message)
        found = script(agent)
        self.write({"agent": kind, "agent_id": agent.agent_id, "reported": found})
        return found

    def stop(self):
        active = False
        while True:
            ran = []
            for entry in self.settings.get("Stop", []):
                for hook in entry["hooks"]:
                    given = self.hook_input(
                        "Stop",
                        None,
                        stop_hook_active=active,
                        transcript_path=os.path.join(self.cwd, "transcript.jsonl"),
                    )
                    ran.append(self.run_hook(hook, given))
            self.write({"stop": True, "stop_hook_active": active, "hooks": ran})
            if active or not any(outcome["status"] == 2 for outcome in ran):
                return
            if self.run_id is not None and not self.commit_failed:
                self.commit_once()
            active = True

    # The Round-Manager's script.

    def commit_once(self):
        answer = self.call(self.main, "run_commit", run_id=self.run_id)
        if not answer.ok:
            self.commit_failed = True
            self.report(f"run.commit failed: {answer.kind or 'refused'}")

    def end(self, text=None):
        if text is not None:
            self.report(text)
        if self.run_id is not None and not self.commit_failed:
            self.commit_once()
        raise _EndSession

    def session(self):
        found = self.prompt.rpartition(_LEAD)
        run_id = found[2][:-1] if found[1] and found[2].endswith(".") else ""
        if not _RUN_ID.fullmatch(run_id) or self.prompt.count(_LEAD) != 1:
            self.report("the prompt holds no valid run id")
            return
        self.server = _Server(self.entry)
        self.server.ask("initialize", _hello())
        self.server.notify("notifications/initialized")
        listed = self.server.ask("tools/list")["result"]["tools"]
        self.tools = {PREFIX + tool["name"] for tool in listed}
        answer = self.call(self.main, "run_commit", run_id=run_id)
        if not answer.ok:
            self.report(f"run.commit failed: {answer.kind}")
            return
        self.run_id = run_id
        try:
            self.entry_steps()
        except _EndSession:
            pass

    def entry_steps(self):
        run_id = self.run_id
        read = self.call(self.main, "state_read", run_id=run_id)
        if read.kind == "run_file_missing":
            fresh = self.call(self.main, "run_fresh", run_id=run_id)
            if not fresh.ok:
                self.end(f"run.fresh failed: {fresh.kind}")
            if fresh.result["fresh"] is not True:
                self.end("the run directory is not fresh and holds no STATE.json")
            written = self.call(
                self.main, "state_write", run_id=run_id, state=FIRST_STATE
            )
            if not written.ok:
                self.end(f"state.write failed: {written.kind}")
            self.round_steps(0)
            return
        if not read.ok:
            self.end(f"state.read failed: {read.kind}")
        state = read.result["state"]
        if "run_status" in state:
            if state["run_status"] == "over":
                self.end()
            self.end(f"unknown run_status: {state['run_status']!r}")
        stated = self.call(self.main, "instance_read", run_id=run_id)
        if not stated.ok:
            self.end(f"instance.read failed: {stated.kind}")
        budget = stated.result["instance"].get("round_budget")
        if budget is None:
            self.end("the instance states no round_budget")
        if state["round"] >= budget:
            if set(state) - {"schema_version", "round", "budget_spent"}:
                self.end("the state holds another top-level member")
            over = {name: state[name] for name in ("schema_version", "round")}
            over["budget_spent"] = state["budget_spent"]
            over["run_status"] = "over"
            written = self.call(self.main, "state_write", run_id=run_id, state=over)
            if not written.ok:
                self.end(f"state.write failed: {written.kind}")
            self.end()
        self.round_steps(state["round"])

    def round_steps(self, round_):
        run_id = self.run_id
        stored = self.call(self.main, "key_store", run_id=run_id)
        if not stored.ok:
            self.report(f"key.store failed: {stored.kind}")
        tuple_ = {"run_id": run_id, "round": round_, "candidate": 1, "attempt": 1}
        rogue = self.turn.get("rogue")
        if rogue:
            self.call(self.main, rogue, **tuple_)
        if round_ == 0:
            self.round_zero(tuple_)
        else:
            self.later_round(tuple_)
        self.closing_steps(round_)

    def round_zero(self, tuple_):
        coded = self.delegate("coder-driver", tuple_, self.coder_driver)
        self.report(f"coder-driver: {coded}")
        if not (coded.get("tool") == "coder_run" and coded.get("taken")):
            self.end()
        if not self.checks_stand(tuple_):
            self.end()
        measured = self.delegate("experiment-runner", tuple_, self.experiment_runner)
        self.report(f"experiment-runner: {measured}")
        if measured.get("outcome") not in ("converged", "not_converged"):
            self.end()

    def checks_stand(self, tuple_):
        for point in ("sim", "board"):
            checked = self.delegate(
                "evaluator", {**tuple_, "point": point}, self.evaluator_check
            )
            self.report(f"evaluator at {point}: {checked}")
            if checked.get("standing") != "verified":
                return False
        return True

    def later_round(self, tuple_):
        given = {name: tuple_[name] for name in ("run_id", "round")}
        selected = self.delegate("technique-selector", given, self.technique_selector)
        self.report(f"technique-selector: {selected}")
        read = self.call(self.main, "hypotheses_read", **given)
        if not read.ok:
            self.end(f"hypotheses.read failed: {read.kind or 'refused'}")
        if "techniques" not in selected:
            self.end("no choice was given")
        message = {**tuple_, "techniques": selected["techniques"]}
        coded = self.delegate("coder-driver", message, self.coder_driver)
        self.report(f"coder-driver: {coded}")
        if coded.get("tool") != "coder_run":
            self.end()
        if coded.get("taken") and self.checks_stand(tuple_):
            measured = self.delegate(
                "experiment-runner", tuple_, self.experiment_runner
            )
            self.report(f"experiment-runner: {measured}")
        judged = self.delegate("evaluator", given, self.evaluator_verdicts)
        self.report(f"evaluator for the verdicts: {judged}")
        if not (judged.get(WRITTEN) or judged.get("kind") == "verdicts_exist"):
            self.end()

    def closing_steps(self, round_):
        run_id = self.run_id
        if round_ != 0:
            cased = self.call(self.main, "case_write", run_id=run_id, round=round_)
            if not cased.ok:
                self.report(f"case.write failed: {cased.kind or 'refused'}")
        ended = self.call(self.main, "round_end", run_id=run_id, round=round_)
        if not ended.ok:
            self.end(f"round.end failed: {ended.kind}")
        if ended.result["reported_lines"]:
            self.report(f"reported lines: {ended.result['reported_lines']}")
        self.end()

    # The sub-agents' scripts.

    def coder_driver(self, agent):
        spec = self.call(agent, "spec_write", **agent.message)
        tuple_ = {name: agent.message[name] for name in _TUPLE}
        if not spec.ok:
            return {"tool": "spec_write", "kind": spec.kind or "refused"}
        coded = self.call(agent, "coder_run", **tuple_)
        if not coded.ok:
            return {"tool": "coder_run", "kind": coded.kind or "refused"}
        return {"tool": "coder_run", **coded.result}

    def evaluator_check(self, agent):
        given = agent.message
        checked = self.call(agent, "correctness_check", **given, execution=1)
        found = {}
        if checked.ok:
            found["outcome"] = checked.result.get("outcome")
        else:
            found["kind"] = checked.kind or "refused"
        read = self.call(agent, "checks_read", **given)
        if read.ok:
            found["standing"] = read.result["attempts"][0]["standing"]
        else:
            found["checks_read_kind"] = read.kind or "refused"
        return found

    def experiment_runner(self, agent):
        measured = self.call(agent, "board_run", **agent.message, execution=1)
        if not measured.ok:
            return {"kind": measured.kind or "refused"}
        found = {"outcome": measured.result.get("outcome")}
        if found["outcome"] == "broken":
            found["condition"] = measured.result.get("condition")
        return found

    def technique_selector(self, agent):
        run_id, round_ = agent.message["run_id"], agent.message["round"]
        found = {}
        rogue = self.turn.get("selector_rogue")
        if rogue:
            refused = self.call(agent, rogue, run_id=run_id, record={})
            found["rogue"] = "refused" if refused.refused else refused.kind
        lookup = self.call(agent, "cases_lookup", run_id=run_id)
        if not lookup.ok:
            return {**found, "cases_lookup": lookup.kind or "refused"}
        found["cases"] = len(lookup.result["cases"])
        found["verdicts_read"] = []
        for earlier in range(1, round_):
            read = self.call(agent, "verdicts_read", run_id=run_id, round=earlier)
            if read.ok:
                counted = len(read.result["record"]["verdicts"])
                found["verdicts_read"].append([earlier, counted])
            elif read.kind in SELECTOR_SKIPS:
                found["verdicts_read"].append([earlier, read.kind])
            else:
                return {**found, "verdicts_read_kind": read.kind or "refused"}
        catalog = self.call(agent, "catalog_read", run_id=run_id)
        entries = set()
        if catalog.ok:
            entries = {entry["id"] for entry in catalog.result["entries"]}
        before = self.call(
            agent,
            "checks_read",
            run_id=run_id,
            round=round_ - 1,
            candidate=1,
            attempt=1,
            point="board",
        )
        standing = before.result["attempts"][0]["standing"] if before.ok else None
        chosen = self.choices.get(str(round_), self.choices.get("default"))
        record = self.hypothesis_record(agent.message, chosen, standing, lookup.result)
        written = self.call(agent, "hypotheses_write", run_id=run_id, record=record)
        found["hypotheses_write"] = written.kind or (
            "refused" if written.refused else "ok"
        )
        if written.ok:
            found["tested_by"] = {h["id"]: h["tested_by"] for h in record["hypotheses"]}
        exists = written.ok or written.kind == "hypotheses_exist"
        if exists and (catalog.ok or catalog.kind == "catalog_unusable"):
            found["techniques"] = [t for t in chosen["techniques"] if t in entries]
        return found

    def hypothesis_record(self, given, chosen, standing, looked):
        round_ = given["round"]
        basis = [
            {
                "kind": "attempt",
                "ref": {"round": 0, "candidate": 1, "attempt": 1},
                "text": "the bring-up kernel of round 0, the baseline of the run",
            }
        ]
        if round_ > 1:
            basis.append(
                {
                    "kind": "attempt",
                    "ref": {"round": round_ - 1, "candidate": 1, "attempt": 1},
                    "text": f"the attempt of the round before, {standing} at board",
                }
            )
        if chosen.get("cite_case") and looked["cases"]:
            case = looked["cases"][0]
            hypothesis = case["hypothesis_record"]["hypotheses"][0]["id"]
            basis.append(
                {
                    "kind": "case",
                    "case": {
                        "run_id": case["run_id"],
                        "round": case["round"],
                        "hypothesis": hypothesis,
                    },
                    "text": "a case of the same key: a hint, not a target",
                }
            )
        expected = {"metric": "latency_minimisation", "direction": chosen["direction"]}
        return {
            "schema_version": 1,
            "run_id": given["run_id"],
            "round": round_,
            "candidates": 1,
            "cases_read": looked["cases_read"],
            "hypotheses": [
                {
                    "id": f"h{round_}",
                    "statement": chosen["statement"],
                    "basis": basis,
                    "expected": [expected],
                    "origin": "system",
                    "tested_by": [1],
                }
            ],
        }

    def evaluator_verdicts(self, agent):
        run_id, round_ = agent.message["run_id"], agent.message["round"]
        read = self.call(agent, "hypotheses_read", run_id=run_id, round=round_)
        if not read.ok:
            return {"hypotheses_read": read.kind or "refused"}
        if self.turn.get("verdicts") == "unreadable":
            return {}
        seen = {}
        for at, point in (
            ((round_, 1), "sim"),
            ((round_, 1), "board"),
            ((0, 1), "board"),
        ):
            checked = self.call(
                agent,
                "checks_read",
                run_id=run_id,
                round=at[0],
                candidate=at[1],
                point=point,
            )
            for attempt in checked.result["attempts"] if checked.ok else []:
                outcomes = [
                    check["result"]["outcome"]
                    for check in attempt["checks"]
                    if check["state"] == "ended" and "result" in check
                ]
                seen[(*at, attempt["attempt"], point)] = (attempt["standing"], outcomes)
        verdicts = [
            self.verdict(agent, round_, hypothesis, seen)
            for hypothesis in read.result["record"]["hypotheses"]
        ]
        document = {
            "schema_version": 1,
            "run_id": run_id,
            "round": round_,
            "verdicts": verdicts,
        }
        written = self.call(agent, "verdicts_write", run_id=run_id, record=document)
        if not written.ok:
            return {"kind": written.kind or "refused"}
        return {
            WRITTEN: True,
            "verdicts": {v["hypothesis"]: v["verdict"] for v in verdicts},
        }

    def verdict(self, agent, round_, hypothesis, seen):
        evidence, causes, counted = [], [], []
        against = {"round": 0, "candidate": 1, "attempt": 1}
        for candidate in hypothesis["tested_by"]:
            for point in ("sim", "board"):
                ref = {"round": round_, "candidate": candidate, "attempt": 1}
                outcome = _outcome(seen, ref, point)
                if outcome is not None:
                    evidence.append(_check(round_, candidate, point, outcome))
        for wanted in hypothesis["expected"]:
            for candidate in hypothesis["tested_by"]:
                measured = {"round": round_, "candidate": candidate, "attempt": 1}
                stood = [
                    seen.get((ref["round"], ref["candidate"], 1, "board"), ("",))[0]
                    for ref in (measured, against)
                ]
                if stood != ["verified", "verified"]:
                    causes.append(f"no pair: standing at board {stood}")
                    continue
                pair = {"measured": measured, "against": against}
                compared = self.call(
                    agent,
                    "timings_compare",
                    run_id=agent.message["run_id"],
                    metric=wanted["metric"],
                    point="board",
                    **pair,
                )
                if not compared.ok:
                    causes.append(f"timings.compare: {compared.kind or 'refused'}")
                    continue
                difference = compared.result["difference"]
                evidence.append(
                    {
                        "kind": "comparison",
                        "metric": wanted["metric"],
                        "point": "board",
                        **pair,
                        "difference": difference,
                    }
                )
                evidence.append(_check(0, 1, "board", _outcome(seen, against)))
                counted.append((wanted["direction"], difference))
                causes.append(f"board latency against round 0: {difference}")
        expected = [want for want, difference in counted if difference == want]
        contrary = [
            want
            for want, difference in counted
            if difference in ("lower", "higher") and difference != want
        ]
        if counted and len(expected) == len(counted):
            value = "supported"
        elif contrary and not expected:
            value = "refuted"
        else:
            value = "inconclusive"
        return {
            "hypothesis": hypothesis["id"],
            "verdict": value,
            "cause": "; ".join(causes) or "no ended check and no comparison",
            "evidence": evidence,
        }


def _outcome(seen, ref, point="board"):
    _, outcomes = seen.get(
        (ref["round"], ref["candidate"], ref["attempt"], point), (None, [])
    )
    if not outcomes:
        return None
    failed = [outcome for outcome in outcomes if outcome != "pass"]
    return failed[0] if failed else "pass"


def _check(round_, candidate, point, outcome):
    return {
        "kind": "check",
        "ref": {"round": round_, "candidate": candidate, "attempt": 1},
        "point": point,
        "outcome": outcome,
    }


def _turn_session(argv, scenario):
    counter = Path(scenario["log"]).with_suffix(".turns")
    number = len(counter.read_text(encoding="utf-8")) + 1 if counter.exists() else 1
    counter.write_text("x" * number, encoding="utf-8")
    turn = _Turn(argv, scenario, number)
    turn.write({"started": True, "argv": argv})
    early = turn.turn.get("exit_first")
    if early is not None:
        turn.write({"exit": early})
        return early
    try:
        turn.session()
    finally:
        if turn.server is not None:
            turn.server.close()
    turn.stop()
    turn.write({"exit": 0})
    sys.stdout.write((turn.replies[-1] if turn.replies else "") + "\n")
    sys.stdout.flush()
    return 0


def claude(argv):
    scenario = _scenario()
    if argv == ["auth", "status"]:
        sys.stdout.write(scenario["check"]["auth_output"])
        return scenario["check"]["auth_exit"]
    if "--no-session-persistence" in argv:
        return _check_session(argv, scenario)
    return _turn_session(argv, scenario)


# --- docker ---


FORCED_REMOVAL = ["container", "rm", "--force"]
_VALUED = {
    "--name",
    "--mount",
    "--workdir",
    "--network",
    "--pull",
    "--user",
    "--cap-drop",
    "--security-opt",
    "--env",
}


def _parsed_run(argv):
    options, index = {}, 0
    while index < len(argv):
        item = argv[index]
        if item in _VALUED:
            options.setdefault(item, []).append(argv[index + 1])
            index += 2
        elif item.startswith("--"):
            options.setdefault(item, []).append(None)
            index += 1
        else:
            break
    image, program, arguments = argv[index], argv[index + 1], argv[index + 2 :]
    mount = dict(part.split("=", 1) for part in options["--mount"][0].split(","))
    return image, program, arguments, mount


def _coder(scenario, mount, program, entry):
    entry["container"] = "coder"
    entry["program"] = program
    entry["token_passed"] = bool(os.environ.get("CLAUDE_CODE_OAUTH_TOKEN"))
    spec = json.loads(Path(mount["source"], "spec.json").read_text(encoding="utf-8"))
    entry["round"] = spec["id"]["round"]
    files = scenario["kernels"].get(str(entry["round"]), scenario["kernel"])
    if files is None:
        return 0
    output = Path(mount["source"], "output")
    output.mkdir()
    for name, text in files.items():
        (output / name).write_text(text, encoding="utf-8")
    return 0


def _host(path, source):
    if path == "/build" or path.startswith("/build/"):
        return source + path[len("/build") :]
    return path


def _standin(scenario, mount, program, arguments, entry):
    source = mount["source"]
    mapped = [_host(argument, source) for argument in arguments]
    if program == "clang":
        entry["container"] = "build"
        command = [scenario["clang"], *mapped]
    elif program == "/build/waiter":
        entry["container"] = "timing"
        return _timing(scenario, source, mapped, entry)
    else:
        entry["container"] = "process"
        command = [_host(program, source), *mapped]
    done = subprocess.run(
        command, cwd=source, env=_image_env(scenario), capture_output=True, check=False
    )
    sys.stdout.buffer.write(done.stdout)
    sys.stderr.buffer.write(done.stderr)
    return done.returncode


def _image_env(scenario):
    return {**os.environ, "PATH": scenario["image_path"]}


def _timing(scenario, source, mapped, entry):
    unshare = scenario["unshare"]
    if unshare is not None:
        entry["waiter"] = "unshare"
        command = [unshare, *NAMESPACE, source + "/waiter", *mapped]
        done = subprocess.run(command, cwd=source, capture_output=True, check=False)
        sys.stdout.buffer.write(done.stdout)
        sys.stderr.buffer.write(done.stderr)
        return done.returncode
    import resource

    entry["waiter"] = "host_figure"
    done = subprocess.run(mapped, cwd=source, capture_output=True, check=False)
    figure = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    sys.stdout.buffer.write(done.stdout + b"\nwaiter_max_rss_kib %d\n" % figure)
    sys.stderr.buffer.write(done.stderr)
    return 0 if done.returncode == 0 else 1


def docker(argv):
    scenario = _scenario()
    entry = {"argv0": argv[:1]}
    status = None
    try:
        if argv[:1] == ["version"]:
            sys.stdout.write("0.0.0-stub\n")
            status = 0
        elif argv[:2] == ["rm", "--force"] or argv[:3] == FORCED_REMOVAL:
            status = 0
        elif argv[:1] == ["run"]:
            image, program, arguments, mount = _parsed_run(argv[1:])
            entry["image"] = image
            if mount["target"] == "/scratch":
                status = _coder(scenario, mount, program, entry)
            else:
                status = _standin(scenario, mount, program, arguments, entry)
        else:
            status = 125
    finally:
        entry["status"] = status
        _append(scenario["docker_log"], entry)
    return status


if __name__ == "__main__":
    which, rest = sys.argv[1], sys.argv[3:]
    sys.exit(claude(rest) if which == "claude" else docker(rest))
