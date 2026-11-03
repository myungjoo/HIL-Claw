"""Reader, checks and call plan of the internal model graph file (ADR-0193 decision 5).

``ARCHITECTURE/decisions/ADR-0193-od32-generalization-design.md`` decision 5
is the rule. :func:`read` and :func:`read_text` read a graph file into a
:class:`Graph` and check it against :data:`hilclaw.contract_table.TABLE`;
:func:`resolve` turns a graph into the :class:`Plan` of a generation.
:data:`LLAMA_GRAPH` is the Llama file, the structure of ``run_pass`` of
``model_forward.c``.

**Format 1.** One JSON object, decoded as ``hilclaw.new_run`` applies
ADR-0155 decision 3 (strict UTF-8, no byte order mark, no member name twice,
no ``NaN`` or ``Infinity``) and with no ``-0`` (:mod:`hilclaw.json_text`),
with exactly the members ``graph_format`` (the integer 1); ``dimensions``
(names the caller gives values for); ``weights`` (``{"name", "shape",
"per"}``, ``per`` ``null`` or a dimension: one entry per index of it);
``tables`` (``{"name", "shape", "source"}``, ``source`` one of
:data:`TABLE_SOURCES`); ``scalars`` (names of non-array arguments);
``state`` (``{"name", "shape", "per"}``, kept between passes); ``buffers``
(``{"name", "shape"}``, of one pass); ``nodes`` (ordered, below); and
``output`` (``{"buffer", "rows"}``, a buffer and an expression).

A ``shape`` is a non-empty array of expressions. An expression is a string
of 1 to :data:`MAX_EXPRESSION_LENGTH` characters over decimal integers,
names, ``+``, ``-``, ``*`` (binding tighter) and parentheses. The always
available names (:data:`ALWAYS_AVAILABLE`) are ``T`` and ``P``, the rows and
start position of a pass, ``R``, the rows reported (``T`` for
``lm_head_rows`` ``"all"``, 1 for ``"last"``), and **``C`` = S + G - 1, the
positions of a generation: an extension of format 1 by this module**, since
the cache and the RoPE table of ADR-0166 decision 4 have C rows, which
``T``, ``P`` and ``R`` cannot express. A weight shape names dimensions only;
a table or state shape also ``C``; a buffer shape also ``T``, ``R`` and
``C``, evaluated at the prefill (the largest T, ADR-0153 decision 4); a node
and ``output.rows`` all four. A name is ``[A-Za-z_][A-Za-z0-9_]{0,63}``,
declared once across dimensions, weights, tables, scalars, state and buffers
and none of the always available names. The nodes, run in array order:

* ``{"op": "kernel", "site", "kind", "shape", "operands", "scalars"}``:
  ``kind`` is that of a bf16 entry of the contract table; ``shape`` maps
  exactly the parameters of its ``op_signature_record`` to expressions,
  ``operands`` exactly the operands of its ``task_contract`` to references,
  and ``scalars`` exactly the other arguments of its ``PROTOTYPE`` to
  scalars (``{}`` when there is none). ``site``, a call-site name, is used once.
  A reference is a name or ``{"of": name, "start": expression}``, that many
  elements in. An operand's array has the operand's dtype (bf16, or for a
  table its source's), and an ``output`` or ``inout`` operand's is a buffer
  or state;
* ``{"op": "embed", "weight", "out"}``: row i of ``out``, for i < T, gets the
  row of the two-dimensional weight for the pass's token id P + i; the last
  shape members of ``out`` and the weight are equal;
* ``{"op": "copy", "from", "from_stride", "from_start", "to", "to_stride",
  "columns"}``: for i < T, ``columns`` elements from element ``from_start +
  i * from_stride`` of ``from`` to element ``i * to_stride`` of ``to``, two
  arrays, with no two target rows overlapping;
* ``{"op": "repeat", "count", "index", "nodes"}``: its nodes once per index
  below the dimension ``count``; ``name{index}`` selects the entry of a
  ``per`` weight or state whose ``per`` is ``count``, and an entry of a
  ``per`` declaration is named in no other way.

A connection is a buffer name: no scheduler, no fusion. ``embed`` and
``copy`` take buffers or state, and only kernel operands take ``start``.

What this module does not do: it starts no process, writes nothing and reads
no file but the one named; it knows no external model format (OD-9) and no
tensor name, reads no weight and builds no table; no data-plane record names
a graph and ``graph_format`` is no data-plane version (ADR-0193 decision 5);
it checks no binding, encodes no plan for a program and runs none.

Every :class:`TypeError` or :class:`ValueError` raised for an argument
carries the attribute ``parameter``; every refusal of a graph is a
:class:`GraphFileError`.
"""

import collections
import contextlib
import inspect
import json
import math
import os
import re
from collections.abc import Mapping
from pathlib import Path

from hilclaw import contract_table, json_text, keys

LLAMA_GRAPH = Path(__file__).parent / "graphs" / "llama.json"
GRAPH_FORMAT = 1
ALWAYS_AVAILABLE = ("T", "P", "R", "C")
TABLE_SOURCES = ("rope",)
MAX_EXPRESSION_LENGTH = 256
LM_HEAD_ROWS = ("all", "last")
REASONS = (
    ("unreadable", "malformed", "not_object", "missing_member", "unknown_member")
    + ("wrong_type", "bad_format", "bad_expression", "duplicate_name")
    + ("undeclared_name", "unknown_op", "duplicate_site", "bad_index")
    + ("bad_repeat_count", "unknown_source", "bad_output", "unknown_kind")
    + ("contract_mismatch", "operand_mismatch", "bad_value", "out_of_range", "overlap")
)

_DTYPE = "bf16"
_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,63}")
_REFERENCE = re.compile(rf"({_NAME.pattern})(?:\{{({_NAME.pattern})\}})?")
_TOKEN = re.compile(r"[0-9]+|[A-Za-z_][A-Za-z0-9_]*|\S")
_TOP = "graph_format dimensions weights tables scalars state buffers nodes output"
_DECLARED = {
    "weights": ("weight", ("name", "shape", "per")),
    "tables": ("table", ("name", "shape", "source")),
    "state": ("state", ("name", "shape", "per")),
    "buffers": ("buffer", ("name", "shape")),
}
_FORMS = {
    "kernel": ("op site kind shape operands scalars", ()),
    "embed": ("op weight out", ()),
    "copy": ("op from from_stride from_start to to_stride columns", ()),
    "repeat": ("op count index nodes", ()),
}
_COPY = ("from_stride", "from_start", "to_stride", "columns")
_WRITABLE = ("buffer", "state")
_ARRAYS = ("weight", "table", "state", "buffer")


def _record(name, fields, doc):
    made = collections.namedtuple(name, fields)
    made.__doc__ = doc
    return made


class GraphFileError(Exception):
    """A graph refused; ``reason`` is one of :data:`REASONS` and ``path`` a JSON path such as ``$.nodes[1]``."""

    def __init__(self, reason, path, message):
        super().__init__(f"{path}: {message}")
        self.reason = reason
        self.path = path


Expression = _record("Expression", "text tree", "An expression and its parse.")
Declaration = _record(
    "Declaration",
    "name shape per source",
    "A weight, table, state or buffer; ``shape`` holds expressions.",
)
Reference = _record(
    "Reference", "name index start", "A name, a repeat index or None, a start or None."
)
Kernel = _record(
    "Kernel",
    "site kind shape operands scalars",
    "A kernel node; shape, operands and scalars are pairs in the contract's order.",
)
Embed = _record("Embed", "weight out", "An embed node of two references.")
Copy = _record(
    "Copy",
    "source from_stride from_start target to_stride columns",
    "A copy node: references ``source`` and ``target`` and four expressions.",
)
Repeat = _record("Repeat", "count index nodes", "A repeat node.")
Graph = _record(
    "Graph",
    "dimensions weights tables scalars state buffers nodes output",
    "A graph read by :func:`read_text`; ``output`` is ``(buffer, rows)``.",
)
Array = _record(
    "Array",
    "name kind base index elements dtype source",
    "An array of a plan: ``name`` is ``base[index]`` for an entry of a ``per``"
    " declaration; ``kind`` is weight, table, state or buffer.",
)
Operand = _record(
    "Operand", "name array offset", "A contract operand, its array and offset."
)
KernelStep = _record(
    "KernelStep",
    "site kind shape operands scalars",
    "A kernel call: ``shape`` in the contract's member order, ``operands`` of"
    " :class:`Operand` in its operand order, ``scalars`` of (argument, name).",
)
EmbedStep = _record(
    "EmbedStep",
    "weight out rows columns first_token",
    "Row i < ``rows`` of ``out`` gets row ``token[first_token + i]`` of ``weight``.",
)
CopyStep = _record(
    "CopyStep",
    "source from_stride from_start target to_stride columns rows",
    "Row i < ``rows``: ``columns`` elements from ``from_start + i * from_stride``"
    " of ``source`` to ``i * to_stride`` of ``target``.",
)
Pass = _record(
    "Pass", "rows position output_rows steps", "A pass: T, P, its output rows, steps."
)
Plan = _record(
    "Plan",
    "arrays scalars output passes",
    "A resolved generation: arrays, scalar names, output buffer, passes (0 the prefill).",
)


def read(path):
    """Read the graph file at ``path`` (``str`` or :class:`os.PathLike`); return a :class:`Graph`.

    Raises :class:`GraphFileError` ``"unreadable"`` when the file cannot be
    read, then as :func:`read_text`; :class:`TypeError` with ``parameter``
    ``"path"`` for another type.
    """
    with _parameter("path"):
        if not isinstance(path, (str, os.PathLike)):
            raise TypeError(f"must be a str or os.PathLike, got {type(path).__name__}")
    try:
        content = Path(path).read_bytes()
    except (OSError, ValueError) as error:
        raise GraphFileError("unreadable", "$", str(error)) from None
    return read_text(content)


def read_text(text):
    """Read a graph from ``text``, a ``str`` or UTF-8 ``bytes``; return a :class:`Graph`.

    Raises :class:`GraphFileError` with a reason of :data:`REASONS` and the
    first fault found, and :class:`TypeError` with ``parameter`` ``"text"``
    for another type.
    """
    with _parameter("text"):
        if not isinstance(text, (str, bytes)):
            raise TypeError(f"must be a str or bytes, got {type(text).__name__}")
    try:
        if isinstance(text, bytes):
            text = text.decode("utf-8")
        value = json.loads(
            text,
            object_pairs_hook=json_text.distinct_members,
            parse_constant=json_text.no_constant,
        )
        marked = json.loads(text, parse_int=json_text.mark_minus_zero)
        json_text.refuse_minus_zero("$", marked, ValueError)
    except (ValueError, RecursionError) as error:
        raise GraphFileError("malformed", "$", str(error)) from None
    if type(value) is not dict:
        raise GraphFileError("not_object", "$", "the JSON text is no object")
    try:
        return _Reader().graph(value)
    except RecursionError:
        raise GraphFileError("malformed", "$", "nests too deeply") from None


def resolve(graph, dimensions, *, prompt_length, generation_length, lm_head_rows):
    """Resolve ``graph`` for one generation; return a :class:`Plan`.

    ``dimensions`` maps each name of ``graph.dimensions`` to an ``int`` from 1
    to 2**53 - 1; so are ``prompt_length`` S and ``generation_length`` G;
    ``lm_head_rows`` is ``"all"`` or ``"last"``. Pass 0 has T = S and P = 0,
    decode pass k (1 ... G - 1) T = 1 and P = S + k - 1, as
    ``model_forward.c``. Argument errors are :class:`TypeError` or
    :class:`ValueError` with the argument's name as ``parameter``. A graph
    that fails at these values raises :class:`GraphFileError` before any plan
    is returned: ``"bad_value"`` for a shape member, element count, stride or
    column count not from 1 to 2**53 - 1, a shape its contract refuses or an
    embed whose ``out`` row width is not the weight's,
    ``"out_of_range"`` for a range outside its array (a negative start
    included), ``"overlap"`` for overlapping operands of one kernel step or a
    copy within one array or onto overlapping target rows.
    """
    with _parameter("graph"):
        if not isinstance(graph, Graph):
            raise TypeError(f"must be a Graph, got {type(graph).__name__}")
    with _parameter("dimensions"):
        if not isinstance(dimensions, Mapping):
            raise TypeError(f"must be a mapping, got {type(dimensions).__name__}")
        if set(dimensions) != set(graph.dimensions):
            raise ValueError(f"must give exactly {graph.dimensions}")
        for name in graph.dimensions:
            _argument(dimensions[name], name)
    for name, value in (
        ("prompt_length", prompt_length),
        ("generation_length", generation_length),
    ):
        with _parameter(name):
            _argument(value, name)
    with _parameter("lm_head_rows"):
        if lm_head_rows not in LM_HEAD_ROWS:
            raise ValueError(f"must be one of {LM_HEAD_ROWS}, got {lm_head_rows!r}")
    S, last = prompt_length, lm_head_rows == "last"
    base = dict(dimensions, C=S + generation_length - 1)
    first = dict(base, T=S, P=0, R=1 if last else S)
    arrays, widths = {}, {}
    for member, (kind, _) in _DECLARED.items():
        for i, d in enumerate(getattr(graph, member)):
            path = f"$.{member}[{i}].shape"
            sizes = [_positive(_value(e.tree, first), path) for e in d.shape]
            elements = _positive(math.prod(sizes), path)
            widths[d.name] = sizes[-1]
            dtype = _dtype(d.source)
            for index in range(base[d.per]) if d.per else (None,):
                name = d.name if index is None else f"{d.name}[{index}]"
                arrays[name] = Array(
                    name, kind, d.name, index, elements, dtype, d.source
                )

    def walk(nodes, path, env, indices, steps):
        def array(reference):
            if reference.index is None:
                return arrays[reference.name]
            return arrays[f"{reference.name}[{indices[reference.index]}]"]

        for i, node in enumerate(nodes):
            where = f"{path}[{i}]"
            if isinstance(node, Repeat):
                for index in range(env[node.count]):
                    walk(
                        node.nodes,
                        f"{where}.nodes",
                        env,
                        {**indices, node.index: index},
                        steps,
                    )
                continue
            where += f" (pass {k}{''.join(f', {n} {v}' for n, v in indices.items())})"
            T = env["T"]
            if isinstance(node, Embed):
                weight, out = array(node.weight), array(node.out)
                if widths[out.base] != widths[weight.base]:
                    raise GraphFileError("bad_value", where, "row widths differ")
                _within(0, T * widths[weight.base], out, where)
                steps.append(
                    EmbedStep(weight.name, out.name, T, widths[weight.base], env["P"])
                )
            elif isinstance(node, Copy):
                v = {m: _value(getattr(node, m).tree, env) for m in _COPY}
                for m in ("from_stride", "to_stride", "columns"):
                    _positive(v[m], f"{where}.{m}")
                source, target = array(node.source), array(node.target)
                if source is target or (T > 1 and v["to_stride"] < v["columns"]):
                    raise GraphFileError("overlap", where, "copies onto itself")
                _within(
                    v["from_start"],
                    (T - 1) * v["from_stride"] + v["columns"],
                    source,
                    where,
                )
                _within(0, (T - 1) * v["to_stride"] + v["columns"], target, where)
                steps.append(
                    CopyStep(
                        source.name,
                        *(v[m] for m in _COPY[:2]),
                        target.name,
                        *(v[m] for m in _COPY[2:]),
                        T,
                    )
                )
            else:
                steps.append(_kernel_step(node, where, env, array))

    passes = []
    for k in range(generation_length):
        T = S if k == 0 else 1
        env = dict(base, T=T, P=0 if k == 0 else S + k - 1, R=1 if last else T)
        steps = []
        walk(graph.nodes, "$.nodes", env, {}, steps)
        rows = _positive(_value(graph.output[1].tree, env), "$.output.rows")
        passes.append(Pass(T, env["P"], rows, tuple(steps)))
    return Plan(tuple(arrays.values()), graph.scalars, graph.output[0], tuple(passes))


class _Reader:
    def __init__(self):
        self.names = {}
        self.sites = set()

    def graph(self, value):
        _members(value, "$", _TOP.split())
        if (
            type(value["graph_format"]) is not int
            or value["graph_format"] != GRAPH_FORMAT
        ):
            raise GraphFileError("bad_format", "$.graph_format", "must be 1")
        dimensions = self._names(value["dimensions"], "$.dimensions", "dimension")
        scalars = self._names(value["scalars"], "$.scalars", "scalar")
        scopes = {"weights": dimensions, "buffers": dimensions + ("T", "R", "C")}
        declared = {
            member: self._declarations(
                value[member], member, scopes.get(member, dimensions + ("C",))
            )
            for member in _DECLARED
        }
        self.scope = dimensions + ALWAYS_AVAILABLE
        nodes = self._nodes(value["nodes"], "$.nodes", {})
        output = value["output"]
        _members(output, "$.output", ("buffer", "rows"))
        if not self._is(output["buffer"], ("buffer",)):
            raise GraphFileError("bad_output", "$.output.buffer", "is not a buffer")
        rows = _expression(output["rows"], "$.output.rows", self.scope)
        return Graph(
            dimensions=dimensions,
            scalars=scalars,
            nodes=nodes,
            output=(output["buffer"], rows),
            **declared,
        )

    def _is(self, name, categories):
        return type(name) is str and self.names.get(name, ("",))[0] in categories

    def _declare(self, name, path, category, entry=None):
        _name(name, path)
        if name in self.names or name in ALWAYS_AVAILABLE:
            raise GraphFileError("duplicate_name", path, f"{name!r} is declared twice")
        self.names[name] = (category, entry)
        return name

    def _names(self, value, path, category):
        items = _array(value, path)
        return tuple(
            self._declare(x, f"{path}[{i}]", category) for i, x in enumerate(items)
        )

    def _declarations(self, value, member, scope):
        category, members = _DECLARED[member]
        result = []
        for i, item in enumerate(_array(value, f"$.{member}")):
            path = f"$.{member}[{i}]"
            _members(item, path, members)
            shape = _array(item["shape"], f"{path}.shape")
            if not shape:
                raise GraphFileError("wrong_type", f"{path}.shape", "is empty")
            shape = tuple(
                _expression(e, f"{path}.shape[{j}]", scope) for j, e in enumerate(shape)
            )
            per, source = item.get("per"), item.get("source")
            if per is not None and not self._is(per, ("dimension",)):
                raise GraphFileError(
                    "undeclared_name", f"{path}.per", "is no dimension"
                )
            if "source" in members and source not in TABLE_SOURCES:
                raise GraphFileError("unknown_source", f"{path}.source", f"{source!r}")
            entry = Declaration(item["name"], shape, per, source)
            result.append(entry)
            self._declare(item["name"], f"{path}.name", category, entry)
        return tuple(result)

    def _nodes(self, value, path, indices):
        items = _array(value, path)
        if not items:
            raise GraphFileError("wrong_type", path, "is empty")
        return tuple(
            self._node(x, f"{path}[{i}]", indices) for i, x in enumerate(items)
        )

    def _node(self, value, path, indices):
        if type(value) is not dict:
            raise GraphFileError("wrong_type", path, "must be an object")
        if "op" not in value:
            raise GraphFileError("missing_member", path, "lacks the member 'op'")
        op = value["op"]
        if type(op) is not str or op not in _FORMS:
            raise GraphFileError("unknown_op", f"{path}.op", f"{op!r}")
        _members(value, path, _FORMS[op][0].split(), _FORMS[op][1])
        if op == "kernel":
            return self._kernel(value, path, indices)
        if op == "repeat":
            count, index = value["count"], value["index"]
            if not self._is(count, ("dimension",)):
                raise GraphFileError(
                    "bad_repeat_count", f"{path}.count", "is no dimension"
                )
            _name(index, f"{path}.index")
            if index in self.names or index in indices or index in ALWAYS_AVAILABLE:
                raise GraphFileError("duplicate_name", f"{path}.index", f"{index!r}")
            inner = {**indices, index: count}
            return Repeat(
                count, index, self._nodes(value["nodes"], f"{path}.nodes", inner)
            )
        if op == "embed":
            weight = self._reference(
                value["weight"], f"{path}.weight", indices, ("weight",)
            )
            if len(self.names[weight.name][1].shape) != 2:
                raise GraphFileError("operand_mismatch", f"{path}.weight", "is not 2-D")
            return Embed(
                weight, self._reference(value["out"], f"{path}.out", indices, _WRITABLE)
            )
        source = self._reference(value["from"], f"{path}.from", indices, _WRITABLE)
        target = self._reference(value["to"], f"{path}.to", indices, _WRITABLE)
        e = [_expression(value[m], f"{path}.{m}", self.scope) for m in _COPY]
        return Copy(source, e[0], e[1], target, e[2], e[3])

    def _kernel(self, value, path, indices):
        site, kind = value["site"], value["kind"]
        _name(site, f"{path}.site")
        if site in self.sites:
            raise GraphFileError("duplicate_site", f"{path}.site", f"{site!r}")
        self.sites.add(site)
        if type(kind) is not str or _contract(kind) is None:
            raise GraphFileError("unknown_kind", f"{path}.kind", f"{kind!r}")
        members, operands, scalars = _signature(kind)
        given = _exact(value["shape"], f"{path}.shape", members)
        shape = tuple(
            (m, _expression(given[m], f"{path}.shape.{m}", self.scope)) for m in members
        )
        given = _exact(value["operands"], f"{path}.operands", [o[0] for o in operands])
        bound = []
        for name, role, dtype in operands:
            where = f"{path}.operands.{name}"
            reference = self._reference(given[name], where, indices, _ARRAYS)
            category, entry = self.names[reference.name]
            if _dtype(entry.source) != dtype:
                raise GraphFileError("operand_mismatch", where, f"is not {dtype}")
            if role != "input" and category not in _WRITABLE:
                raise GraphFileError("operand_mismatch", where, f"is a {category}")
            bound.append((name, reference))
        given = _exact(value["scalars"], f"{path}.scalars", scalars)
        for argument in scalars:
            if not self._is(given[argument], ("scalar",)):
                raise GraphFileError(
                    "undeclared_name", f"{path}.scalars.{argument}", "is no scalar"
                )
        return Kernel(
            site, kind, shape, tuple(bound), tuple((a, given[a]) for a in scalars)
        )

    def _reference(self, value, path, indices, categories):
        start = None
        if type(value) is dict and categories is _ARRAYS:
            _members(value, path, ("of", "start"))
            start = _expression(value["start"], f"{path}.start", self.scope)
            value, path = value["of"], f"{path}.of"
        found = _REFERENCE.fullmatch(value) if type(value) is str else None
        if found is None:
            raise GraphFileError("wrong_type", path, "is not a reference")
        name, index = found.groups()
        if not self._is(name, categories):
            raise GraphFileError(
                "undeclared_name", path, f"{name!r} is no {categories}"
            )
        per = self.names[name][1].per
        if (index is None) != (per is None):
            raise GraphFileError("bad_index", path, f"per {per!r} with index {index!r}")
        if index is not None and indices.get(index) != per:
            raise GraphFileError(
                "bad_index", path, f"{index!r} is no repeat over {per!r}"
            )
        return Reference(name, index, start)


def _kernel_step(node, where, env, array):
    shape = tuple(
        _positive(_value(e.tree, env), f"{where}.shape.{m}") for m, e in node.shape
    )
    try:
        operands = _contract(node.kind).task_contract(*shape)["operands"]
    except ValueError as error:
        raise GraphFileError("bad_value", where, f"shape {shape}: {error}") from None
    ranges, made = [], []
    for (name, reference), operand in zip(node.operands, operands):
        offset = 0 if reference.start is None else _value(reference.start.tree, env)
        end = offset + math.prod(operand["shape"])
        target = array(reference)
        _within(offset, end - offset, target, f"{where}.operands.{name}")
        for other, array_name, start, stop in ranges:
            if array_name == target.name and offset < stop and start < end:
                raise GraphFileError("overlap", where, f"{name} overlaps {other}")
        ranges.append((name, target.name, offset, end))
        made.append(Operand(name, target.name, offset))
    return KernelStep(node.site, node.kind, shape, tuple(made), node.scalars)


def _within(offset, length, array, where):
    if offset < 0 or offset + length > array.elements:
        raise GraphFileError(
            "out_of_range",
            where,
            f"{offset}+{length} runs past {array.name} ({array.elements})",
        )


def _contract(kind):
    for key, entry in contract_table.TABLE.items():
        if key[0] == kind and key[1] == _DTYPE:
            return entry.contract
    return None


def _dtype(source):
    return _DTYPE if source is None else _contract(source).TABLE_DTYPE


def _signature(kind):
    contract = _contract(kind)
    members = tuple(inspect.signature(contract.op_signature_record).parameters)
    operands = contract.task_contract(*(2,) * len(members))["operands"]
    text = contract.PROTOTYPE
    parameters = text[text.index("(") + 1 : text.rindex(")")].split(",")
    scalars = tuple(
        p.split()[-1]
        for p in parameters
        if "*" not in p and p.split()[-1] not in members
    )
    return members, tuple((o["name"], o["role"], o["dtype"]) for o in operands), scalars


def _expression(value, path, scope):
    if type(value) is not str:
        raise GraphFileError("wrong_type", path, "must be an expression string")
    if not 1 <= len(value) <= MAX_EXPRESSION_LENGTH:
        raise GraphFileError("bad_expression", path, "is empty or too long")
    tokens = _TOKEN.findall(value)
    at = 0

    def fail(message):
        raise GraphFileError("bad_expression", path, message)

    def atom():
        nonlocal at
        if at == len(tokens):
            fail("ends early")
        token = tokens[at]
        at += 1
        if token == "(":
            tree = chain(product, "+-")
            if at == len(tokens) or tokens[at] != ")":
                fail("a parenthesis is not closed")
            at += 1
            return tree
        if re.fullmatch("[0-9]+", token):
            return ("int", int(token))
        if token not in scope:
            fail(f"{token!r} is no operand here")
        return ("name", token)

    def chain(operand, operators):
        nonlocal at
        tree = operand()
        while at < len(tokens) and tokens[at] in operators:
            at += 1
            tree = (tokens[at - 1], tree, operand())
        return tree

    def product():
        return chain(atom, "*")

    tree = chain(product, "+-")
    if at != len(tokens):
        fail(f"{tokens[at]!r} is not expected")
    return Expression(value, tree)


def _value(tree, env):
    if tree[0] == "int":
        return tree[1]
    if tree[0] == "name":
        return env[tree[1]]
    left, right = _value(tree[1], env), _value(tree[2], env)
    return (
        left + right
        if tree[0] == "+"
        else left - right
        if tree[0] == "-"
        else left * right
    )


def _members(value, path, required, optional=()):
    if type(value) is not dict:
        raise GraphFileError("wrong_type", path, "must be an object")
    for name in required:
        if name not in value:
            raise GraphFileError("missing_member", path, f"lacks the member {name!r}")
    for name in value:
        if name not in required and name not in optional:
            raise GraphFileError("unknown_member", f"{path}.{name}", "is no member")


def _exact(value, path, names):
    if type(value) is not dict:
        raise GraphFileError("wrong_type", path, "must be an object")
    if set(value) != set(names):
        raise GraphFileError(
            "contract_mismatch", path, f"{sorted(value)}, not {sorted(names)}"
        )
    return value


def _array(value, path):
    if type(value) is not list:
        raise GraphFileError("wrong_type", path, "must be an array")
    return value


def _name(value, path):
    if type(value) is not str or not _NAME.fullmatch(value):
        raise GraphFileError("wrong_type", path, "is not a name")


def _positive(value, path):
    if not 1 <= value <= keys.MAX_INTEGER:
        raise GraphFileError("bad_value", path, f"is {value}, not from 1 to 2**53 - 1")
    return value


def _argument(value, name):
    if type(value) is not int:
        raise TypeError(f"{name}: must be an int, got {type(value).__name__}")
    if not 1 <= value <= keys.MAX_INTEGER:
        raise ValueError(f"{name}: must be from 1 to 2**53 - 1, got {value}")


@contextlib.contextmanager
def _parameter(name):
    try:
        yield
    except (TypeError, ValueError) as error:
        error.parameter = name
        raise
