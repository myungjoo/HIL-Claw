"""The Docker runtime of a first-case coder call (ADR-0137 decisions 2 to 7, code slice 1).

``ARCHITECTURE/decisions/ADR-0137-od23-first-case-coder-process-start.md``
decides how the container and the coder's ``claude -p`` of one first-case
coder call are started. :class:`DockerRuntime` implements the seam of
:mod:`hilclaw.coder_call`: ``available()`` (decision 2) and
``run(scratch_root, coder_model=...)`` (decisions 3 to 7).
:func:`hilclaw.tools.default_registry` binds ``coder.run`` to it with its
defaults, and :mod:`hilclaw.turn_loop` passes the two variables to the MCP
front (ADR-0137 code slice 2).

The user names the image in :data:`ENV_IMAGE` and gives the token of
``claude setup-token`` in :data:`ENV_TOKEN` (decisions 4 and 5). Both are read
at each ``run``, never by ``available()``. The token's value goes only into
the environment of the ``docker run`` child, under :data:`TOKEN_NAME`, which
``--env`` passes by name; it is in no argument, exception text, note or
returned value.

Choices ADR-0137 leaves to this slice, with their values:

- the time limit of ``docker version`` is :data:`VERSION_TIMEOUT_S` and that
  of ``docker container rm --force`` is :data:`REMOVAL_TIMEOUT_S` seconds;
- the container counts as gone when the removal exits 0, or exits non-zero
  with ``No such container`` in its standard error; any other status, a
  timeout or an exception of the removal means not gone. The premise of this
  rule is runtime acceptance item (lxxiii), not verified;
- a container not shown gone makes ``run`` return :data:`NOT_GONE_STATUS`;
- the standard input, output and error of ``docker run`` (so the coder's
  output) are :data:`subprocess.DEVNULL`; those of the calling process are the
  MCP front's protocol;
- the wording of the prompt is :data:`PROMPT`;
- a platform without ``os.getuid`` or ``os.getgid`` (native Windows) has no
  numeric user to pass, so ``run`` raises
  :class:`hilclaw.coder_call.CoderNotStartedError` there before any process.

What this module does not do: no time limit on the call (OD-14); no image
pulled, built or named (``--pull never``; no default image); no token
created, stored or logged; no ``DOCKER_HOST`` or ``DOCKER_CONTEXT`` read or
set; no Podman; nothing about leftovers of a dead process (OD-8 ㉝ (나)); no
output stream kept (OD-23 ① (라)); no data-plane file written.
"""

import os
import secrets
import shutil
import subprocess
from collections.abc import Mapping

from hilclaw import bring_in, local_run, standin_container
from hilclaw.coder_call import CoderNotStartedError

ENV_IMAGE = "HILCLAW_CODER_IMAGE"
ENV_TOKEN = "HILCLAW_CODER_OAUTH_TOKEN"
TOKEN_NAME = "CLAUDE_CODE_OAUTH_TOKEN"
NAME_PREFIX = "hilclaw-coder-"
CONTAINER_SCRATCH = "/scratch"
VERSION_TIMEOUT_S = 15
REMOVAL_TIMEOUT_S = 60
NOT_GONE_STATUS = 255
NOT_STARTED_STATUSES = frozenset({125, 126, 127})
ALLOWED_TOOLS = "Bash,Read,Edit,Write"

PROMPT = (
    "Your working directory holds spec.json, the specification of one compute "
    "kernel. Read it, then write the complete source of that kernel as files "
    "directly in the directory output of your working directory, creating that "
    "directory. Each file name is 3 to 64 characters long: lower-case ASCII "
    "letters, digits, underscores and hyphens, starting with a letter or a "
    "digit, then one dot and the suffix c or h, with no other dot. The part "
    "before the dot must not be con, prn, aux, nul, com1 to com9 or lpt1 to "
    "lpt9. Put the files flat in output, with no subdirectories. Write every "
    "file whole, never a diff or a patch. Write at most "
    f"{bring_in.MAX_FILES} files, each of at most {bring_in.MAX_FILE_BYTES} "
    "bytes; if more files qualify, none is kept. You may build and try your "
    "code with the tools of this environment inside your working directory. "
    "Nothing outside output is kept, and a file in output that breaks these "
    "rules is lost."
)

_UNEXPANDED_TOKEN = "${" + ENV_TOKEN + "}"
_MOUNT_UNSAFE = (",", '"', "\n", "\r", "\0")


class DockerRuntime:
    """The runtime of ADR-0137 behind the seam of :mod:`hilclaw.coder_call`.

    ``environ`` is the mapping the two variables are read from and the
    ``docker`` children get their environment from; ``None`` means
    :data:`os.environ`, read at each call. ``client`` is the program looked
    up on ``PATH``. Raises :class:`TypeError` for an ``environ`` that is not
    a mapping or a ``client`` that is not ``str``, and :class:`ValueError`
    for an empty ``client`` or one holding NUL.
    """

    def __init__(self, *, environ=None, client="docker"):
        if environ is not None and not isinstance(environ, Mapping):
            raise TypeError(f"environ must be a mapping, not {type(environ).__name__}")
        if not isinstance(client, str):
            raise TypeError(f"client must be str, not {type(client).__name__}")
        if not client or "\0" in client:
            raise ValueError("client must be non-empty and hold no NUL character")
        self._environ = environ
        self._client = client

    def available(self):
        """Return whether the client reaches a container server (decision 2).

        ``True`` exactly when ``<client> version --format '{{.Server.Version}}'``
        exits 0 within :data:`VERSION_TIMEOUT_S` with a non-empty line on its
        standard output. Every other outcome, an exception of the start
        included, is ``False``. Reads neither :data:`ENV_IMAGE` nor
        :data:`ENV_TOKEN`.
        """
        command = [self._client, "version", "--format", "{{.Server.Version}}"]
        try:
            ran = local_run.run(
                command, timeout_s=VERSION_TIMEOUT_S, env=self._client_env()
            )
        except Exception:  # noqa: BLE001
            return False
        return ran.returncode == 0 and bool(ran.stdout.strip())

    def run(self, scratch_root, *, coder_model):
        """Run the coder in one container on ``scratch_root``; return its status.

        ``scratch_root`` is the absolute host path of the scratch, mounted at
        :data:`CONTAINER_SCRATCH`; ``coder_model`` is passed to ``--model``.
        :class:`TypeError` or :class:`ValueError` naming the argument is
        raised for a ``scratch_root`` that is not a ``str`` path, not
        absolute or holds ``,``, ``"``, a newline, a carriage return or NUL,
        and for a ``coder_model`` that is not a non-empty ``str``, begins
        with ``-`` or holds whitespace or NUL.

        :class:`hilclaw.coder_call.CoderNotStartedError`, naming a variable
        and never its value, before any process: :data:`ENV_IMAGE` unset,
        empty or refused by :func:`hilclaw.standin_container.check_image`;
        :data:`ENV_TOKEN` unset, empty, holding NUL or the unexpanded text
        ``${HILCLAW_CODER_OAUTH_TOKEN}``; no numeric ids; the client not on
        ``PATH``. Also raised when the start fails with an :class:`OSError`
        and, after the removal, when ``docker run`` exits 125, 126 or 127.

        Otherwise the container is removed by name and the status of
        ``docker run`` is returned, or :data:`NOT_GONE_STATUS` when the
        container is not shown gone. No time limit is applied. When the wait
        is cut off by any exception, the container is removed by name and the
        client killed and reaped before the exception goes on; a failed
        removal is added to it as a note.
        """
        source = _check_scratch_root(scratch_root)
        _check_model(coder_model)
        environ = os.environ if self._environ is None else self._environ
        image = _read_image(environ)
        token = _read_token(environ)
        user = _numeric_user()
        client = shutil.which(self._client)
        if client is None:
            raise CoderNotStartedError(f"the client {self._client!r} is not on PATH")
        name = NAME_PREFIX + secrets.token_hex(16)
        child_env = dict(environ)
        child_env[TOKEN_NAME] = token
        try:
            process = subprocess.Popen(
                _command(client, name, source, user, image, coder_model),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env=child_env,
            )
        except OSError as error:
            raise CoderNotStartedError(
                f"docker run could not be started ({type(error).__name__})"
            ) from error
        try:
            status = process.wait()
        except BaseException as error:
            try:
                if not self._remove(client, name):
                    error.add_note(f"the container {name} was not shown gone")
            except BaseException as failed:  # noqa: BLE001
                error.add_note(f"the removal of {name} raised {type(failed).__name__}")
            finally:
                _reap(process)
            raise
        gone = self._remove_quietly(client, name)
        if status in NOT_STARTED_STATUSES:
            failed = CoderNotStartedError(f"docker run exited with status {status}")
            if not gone:
                failed.add_note(f"the container {name} was not shown gone")
            raise failed
        return status if gone else NOT_GONE_STATUS

    def _client_env(self):
        return None if self._environ is None else dict(self._environ)

    def _remove(self, client, name):
        removed = local_run.run(
            [client, "container", "rm", "--force", name],
            timeout_s=REMOVAL_TIMEOUT_S,
            env=self._client_env(),
        )
        if removed.timed_out:
            return False
        return removed.returncode == 0 or b"No such container" in removed.stderr

    def _remove_quietly(self, client, name):
        try:
            return self._remove(client, name)
        except Exception:  # noqa: BLE001
            return False


def _command(client, name, source, user, image, coder_model):
    return [
        client,
        "run",
        "--name",
        name,
        "--rm",
        "--pull",
        "never",
        "--mount",
        f"type=bind,source={source},target={CONTAINER_SCRATCH}",
        "--workdir",
        CONTAINER_SCRATCH,
        "--user",
        user,
        "--entrypoint=",
        "--env",
        "HOME=/tmp",
        "--env",
        TOKEN_NAME,
        "--env",
        "DISABLE_UPDATES=1",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges=true",
        image,
        "claude",
        "-p",
        PROMPT,
        "--model",
        coder_model,
        "--permission-mode",
        "dontAsk",
        "--allowedTools",
        ALLOWED_TOOLS,
        "--setting-sources",
        "project",
        "--no-session-persistence",
    ]


def _check_scratch_root(scratch_root):
    if not isinstance(scratch_root, (str, os.PathLike)):
        raise TypeError(
            f"scratch_root must be str or os.PathLike, not {type(scratch_root).__name__}"
        )
    source = os.fspath(scratch_root)
    if not isinstance(source, str):
        raise TypeError("scratch_root must be a str path, not bytes")
    if any(character in source for character in _MOUNT_UNSAFE):
        raise ValueError("scratch_root contains a character a mount cannot carry")
    if not os.path.isabs(source):
        raise ValueError("scratch_root must be absolute")
    return source


def _check_model(coder_model):
    if not isinstance(coder_model, str):
        raise TypeError(f"coder_model must be str, not {type(coder_model).__name__}")
    if not coder_model or coder_model.startswith("-"):
        raise ValueError("coder_model must be non-empty and not begin with '-'")
    if "\0" in coder_model or any(c.isspace() for c in coder_model):
        raise ValueError("coder_model contains whitespace or a NUL character")


def _read_image(environ):
    image = environ.get(ENV_IMAGE)
    if image is None or image == "":
        raise CoderNotStartedError(f"{ENV_IMAGE} is not set")
    try:
        standin_container.check_image(image)
    except (TypeError, ValueError):
        refused = True
    else:
        refused = False
    if refused:
        raise CoderNotStartedError(
            f"{ENV_IMAGE} must be a str that does not begin with '-' and holds "
            "no whitespace or NUL character"
        )
    return image


def _read_token(environ):
    token = environ.get(ENV_TOKEN)
    if token is None or token == "" or token == _UNEXPANDED_TOKEN:
        raise CoderNotStartedError(f"{ENV_TOKEN} is not set")
    if not isinstance(token, str) or "\0" in token:
        raise CoderNotStartedError(f"{ENV_TOKEN} must be a str with no NUL character")
    return token


def _numeric_user():
    getuid = getattr(os, "getuid", None)
    getgid = getattr(os, "getgid", None)
    if getuid is None or getgid is None:
        raise CoderNotStartedError(
            "this platform has no os.getuid or os.getgid; a POSIX host is required"
        )
    return f"{getuid()}:{getgid()}"


def _reap(process):
    try:
        process.kill()
    except OSError:
        pass
    process.wait()
