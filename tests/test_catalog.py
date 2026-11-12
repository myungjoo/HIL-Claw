import copy
import json
import os
import re
from pathlib import Path

import pytest

from hilclaw import catalog, contract_table, spec
from hilclaw.catalog import (
    SOURCE,
    AppliesTo,
    Entry,
    InvalidCatalogError,
    applies,
    check,
    criteria,
    entries,
    mismatch,
    technique,
)

ROOT = Path(__file__).resolve().parent.parent
EXAMPLE = ROOT / "examples" / "spec" / "gemm-485b9bc494d477eb.json"
COMMITTED = (
    "cache_blocking",
    "loop_order_ikj",
    "register_blocking",
    "simd_baseline_intrinsics",
)
GEMM_BF16 = ("gemm_bf16_row_accumulators", "gemm_bf16_widened_b_panel")
ALL_COMMITTED = tuple(sorted(COMMITTED + GEMM_BF16))
FORBIDDEN = re.compile(
    r"\bomp\b|openmp|pthread|\bthreads?\b|(?<![\w-])-[fD]\w|__attribute__|avx|nntrainer",
    re.IGNORECASE,
)
FP32_LINES = ("- kind: gemm", "- dtype: fp32", "- layout: row_major", "- language: c")
APPLIES = "\n".join(FP32_LINES)
FP32 = AppliesTo("gemm", "fp32", "row_major", "c")
BF16_GEMM = AppliesTo("gemm", "bf16", "row_major", "c")


def lines_of(key):
    return "\n".join(
        f"- {name}: {value}" for name, value in zip(AppliesTo._fields, key)
    )


def body(
    entry_id,
    *,
    applies=APPLIES,
    when="Worth trying when n is above 1.",
    guidance="Do it.",
):
    return (
        f"# {entry_id}\n\n## Applies to\n\n{applies}\n\n## When\n\n{when}\n\n"
        f"## Guidance\n\n{guidance}\n"
    )


@pytest.fixture
def root(tmp_path):
    directory = tmp_path / "catalog"
    (directory / "cpu_standin").mkdir(parents=True)
    return directory


def put(root, name, content, accelerator="cpu_standin"):
    path = root / accelerator / name
    path.write_bytes(content if isinstance(content, bytes) else content.encode("utf-8"))
    return path


def refused(root, text=None, accelerator="cpu_standin"):
    with pytest.raises(InvalidCatalogError) as caught:
        check(accelerator, source=root)
    if text is not None:
        assert str(caught.value) == text
    return caught.value


def symlink(link, target, *, directory=False):
    try:
        os.symlink(target, link, target_is_directory=directory)
    except (OSError, NotImplementedError):
        pytest.skip("symbolic links cannot be created here")


def junction(link, target):
    try:
        import _winapi
    except ImportError:
        pytest.skip("junctions exist only on Windows")
    _winapi.CreateJunction(str(target), str(link))


def test_public_names():
    assert catalog.__doc__
    assert SOURCE == Path(catalog.__file__).resolve().parent.parent / "catalog"
    assert AppliesTo._fields == ("kind", "dtype", "layout", "language")
    assert Entry._fields == ("applies_to", "when", "text")
    assert not hasattr(catalog, "APPLIES_TO")
    assert issubclass(InvalidCatalogError, ValueError)
    assert check.__doc__ and technique.__doc__ and criteria.__doc__
    assert entries.__doc__ and applies.__doc__ and mismatch.__doc__


def test_committed_catalog_holds_the_four_entries():
    assert sorted(os.listdir(SOURCE)) == ["cpu_standin"]
    assert check("cpu_standin") == ALL_COMMITTED
    assert sorted(os.listdir(SOURCE / "cpu_standin")) == [
        f"{i}.md" for i in ALL_COMMITTED
    ]


def test_committed_entries_state_their_contracts():
    found = entries("cpu_standin")
    assert {i: e.applies_to for i, e in found.items()} == {
        i: FP32 if i in COMMITTED else BF16_GEMM for i in ALL_COMMITTED
    }
    assert all(e.applies_to in contract_table.TABLE for e in found.values())


@pytest.mark.parametrize("entry_id", GEMM_BF16)
def test_committed_gemm_bf16_entry_keeps_its_contract(entry_id):
    given = technique("cpu_standin", entry_id)
    document = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    document["guidance"]["techniques"] = [given]
    spec.validate(document)
    content = (SOURCE / "cpu_standin" / f"{entry_id}.md").read_text(encoding="utf-8")
    assert not FORBIDDEN.search(content)
    text = given["text"]
    assert text == content.split("## Guidance\n", 1)[1].strip("\n")
    assert (
        "`void hilclaw_gemm_bf16(size_t m, size_t k, size_t n, "
        "const uint16_t *restrict a, const uint16_t *restrict b, "
        "uint16_t *restrict c);`"
    ) in text
    for words in (
        "round to nearest, ties to even",
        "`uint16_t`",
        "do not accumulate in `double`",
        "not a measured or tuned value",
        "`m`, `k` and `n` of at least 1",
        "never read",
    ):
        assert words in text
    assert "hilclaw_gemm(" not in text


@pytest.mark.parametrize("entry_id", COMMITTED)
def test_committed_entry_is_a_valid_spec_member(entry_id):
    given = technique("cpu_standin", entry_id)
    assert set(given) == {"id", "text"}
    assert given["id"] == entry_id
    document = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    composed = copy.deepcopy(document)
    composed["guidance"]["techniques"] = [given]
    spec.validate(composed)
    content = (SOURCE / "cpu_standin" / f"{entry_id}.md").read_text(encoding="utf-8")
    assert given["text"] == content.split("## Guidance\n", 1)[1].strip("\n")


@pytest.mark.parametrize("entry_id", COMMITTED)
def test_committed_entry_offers_nothing_outside_the_rules(entry_id):
    content = (SOURCE / "cpu_standin" / f"{entry_id}.md").read_text(encoding="utf-8")
    assert not FORBIDDEN.search(content)
    assert (
        "hilclaw_gemm(size_t m, size_t k, size_t n"
        in technique("cpu_standin", entry_id)["text"]
    )


def test_committed_simd_entry_names_both_paths():
    text = technique("cpu_standin", "simd_baseline_intrinsics")["text"]
    for word in (
        "__x86_64__",
        "__aarch64__",
        "_mm_loadu_ps",
        "vld1q_f32",
        "<immintrin.h>",
    ):
        assert word in text
    assert "<arm_neon.h>" in text and "#else" in text


def test_one_entry(root):
    put(root, "alpha.md", body("alpha"))
    assert check("cpu_standin", source=root) == ("alpha",)
    assert technique("cpu_standin", "alpha", source=root) == {
        "id": "alpha",
        "text": "Do it.",
    }


def test_several_entries_sorted_and_source_as_str(root):
    for name in ("zeta", "alpha", "m_2"):
        put(root, f"{name}.md", body(name, guidance=f"Guide {name}."))
    assert check("cpu_standin", source=str(root)) == ("alpha", "m_2", "zeta")
    assert technique("cpu_standin", "m_2", source=str(root))["text"] == "Guide m_2."


def test_another_accelerator_directory(root):
    (root / "other").mkdir()
    put(root, "x.md", body("x"), accelerator="other")
    assert check("other", source=root) == ("x",)
    assert check("cpu_standin", source=root) == ()


def test_empty_directory_gives_no_entry(root):
    assert check("cpu_standin", source=root) == ()
    with pytest.raises(KeyError):
        technique("cpu_standin", "alpha", source=root)


def test_level_three_heading_and_inner_text_are_kept(root):
    guidance = (
        "First.\n\n### Detail\n\nMore.\n\n```c\n#define X 1\n```\n\n"
        "> quoted `#x` and `<h3>`\n\n- `##x`\n\nLast line  "
    )
    put(root, "alpha.md", body("alpha", guidance=guidance))
    assert technique("cpu_standin", "alpha", source=root)["text"] == guidance


def test_text_keeps_inner_content_and_strips_line_feeds(root):
    content = (
        "# alpha\n## Applies to\n" + APPLIES + "\n## When\nNow.\n## Guidance\n\n\n"
        "  Indented.\n\n\nTabs\there.\n\n\n\n"
    )
    put(root, "alpha.md", content)
    text = technique("cpu_standin", "alpha", source=root)["text"]
    assert text == "  Indented.\n\n\nTabs\there."


def test_text_without_trailing_line_feed(root):
    put(root, "alpha.md", body("alpha").rstrip("\n"))
    assert technique("cpu_standin", "alpha", source=root)["text"] == "Do it."


def test_technique_returns_a_new_dict(root):
    put(root, "alpha.md", body("alpha"))
    first = technique("cpu_standin", "alpha", source=root)
    first["text"] = "changed"
    assert technique("cpu_standin", "alpha", source=root)["text"] == "Do it."


@pytest.mark.parametrize(
    "accelerator", ["", "CPU", "1cpu", "a" * 33, "cpu-standin", "../x"]
)
def test_accelerator_not_a_name(root, accelerator):
    with pytest.raises(InvalidCatalogError):
        check(accelerator, source=root)
    with pytest.raises(InvalidCatalogError):
        technique(accelerator, "alpha", source=root)


@pytest.mark.parametrize("accelerator", [None, b"cpu_standin", Path("cpu_standin"), 1])
def test_accelerator_not_a_str(root, accelerator):
    with pytest.raises(TypeError):
        check(accelerator, source=root)
    with pytest.raises(TypeError):
        technique(accelerator, "alpha", source=root)


@pytest.mark.parametrize("source", [1, b"catalog"])
def test_source_not_a_path(source):
    with pytest.raises(TypeError):
        check("cpu_standin", source=source)


def test_missing_directory(root, tmp_path):
    with pytest.raises(FileNotFoundError):
        check("mock", source=root)
    with pytest.raises(FileNotFoundError):
        check("cpu_standin", source=tmp_path / "absent")


def test_file_where_directory_expected(root):
    (root / "mock").write_bytes(b"")
    refused(
        root, "the accelerator's catalog is not a plain directory", accelerator="mock"
    )


def test_directory_is_a_symbolic_link(root, tmp_path):
    target = tmp_path / "elsewhere"
    target.mkdir()
    symlink(root / "linked", target, directory=True)
    refused(
        root, "the accelerator's catalog is not a plain directory", accelerator="linked"
    )


def test_directory_is_a_junction(root, tmp_path):
    target = tmp_path / "elsewhere"
    target.mkdir()
    junction(root / "joined", target)
    refused(
        root, "the accelerator's catalog is not a plain directory", accelerator="joined"
    )


def test_subdirectory(root):
    put(root, "alpha.md", body("alpha"))
    (root / "cpu_standin" / "nested").mkdir()
    refused(root, "the catalog holds an entry that is not a file")


def test_entry_that_is_neither_file_nor_directory(root):
    try:
        os.mkfifo(root / "cpu_standin" / "beta.md")
    except (AttributeError, OSError):
        pytest.skip("named pipes cannot be made here")
    refused(root, "the catalog holds an entry that is not a file")


def test_subdirectory_named_like_an_entry(root):
    (root / "cpu_standin" / "beta.md").mkdir()
    refused(root, "the catalog holds an entry that is not a file")


def test_file_symbolic_link(root, tmp_path):
    target = tmp_path / "beta.md"
    target.write_bytes(body("beta").encode())
    symlink(root / "cpu_standin" / "beta.md", target)
    refused(root, "the catalog holds a symbolic link or a junction")


def test_junction_inside(root, tmp_path):
    target = tmp_path / "elsewhere"
    target.mkdir()
    junction(root / "cpu_standin" / "beta.md", target)
    refused(root, "the catalog holds a symbolic link or a junction")


@pytest.mark.parametrize(
    "name",
    [
        "README",
        "notes.txt",
        "Alpha.md",
        "ALPHA.MD",
        "alpha.MD",
        "1alpha.md",
        ".md",
        "a-b.md",
        "alpha.md.bak",
        "a" * 33 + ".md",
        ".hidden.md",
        "alpha .md",
    ],
)
def test_file_not_named_as_an_entry(root, name):
    put(root, name, body("alpha"))
    refused(root, "the catalog holds a file not named '<name>.md'")


def test_longest_name_accepted(root):
    name = "a" * 32
    put(root, f"{name}.md", body(name))
    assert check("cpu_standin", source=root) == (name,)


def test_not_utf8(root):
    put(root, "alpha.md", body("alpha").encode() + b"\xff\xfe")
    refused(root, "an entry file is not UTF-8")


def test_surrogate_bytes_not_utf8(root):
    put(root, "alpha.md", body("alpha", guidance="x").encode() + b"\xed\xa0\x80")
    refused(root, "an entry file is not UTF-8")


def test_byte_order_mark(root):
    put(root, "alpha.md", b"\xef\xbb\xbf" + body("alpha").encode())
    refused(root, "an entry file starts with a byte order mark")


@pytest.mark.parametrize(
    "content", [body("alpha").replace("\n", "\r\n"), body("alpha") + "x\ry"]
)
def test_carriage_return(root, content):
    put(root, "alpha.md", content)
    refused(root, "an entry file holds a carriage return")


@pytest.mark.parametrize(
    "first",
    ["", "#alpha", "# alpha ", "## alpha", " # alpha", "# Alpha", "# beta", "text"],
)
def test_wrong_first_line(root, first):
    put(root, "alpha.md", first + "\n" + body("alpha").split("\n", 1)[1])
    refused(root, "an entry file does not start with '# ' and its id")


def test_empty_file(root):
    put(root, "alpha.md", b"")
    refused(root, "an entry file does not start with '# ' and its id")


def test_id_differs_from_stem(root):
    put(root, "alpha.md", body("beta"))
    refused(root, "an entry file does not start with '# ' and its id")


HEADINGS = "an entry file has other headings than ADR-0150's"


@pytest.mark.parametrize(
    "content",
    [
        "# alpha\n\n## Applies to\n\n" + APPLIES + "\n\n## Guidance\n\nDo it.\n",
        "# alpha\n\n## Applies to\n\n" + APPLIES + "\n\n## When\n\nNow.\n",
        "# alpha\n\n## When\n\nNow.\n\n## Applies to\n\n"
        + APPLIES
        + "\n\n## Guidance\n\nDo.\n",
        "# alpha\n\n## Applies to\n\n"
        + APPLIES
        + "\n\n## Guidance\n\nDo.\n\n## When\n\nNow.\n",
        body("alpha", guidance="Do.\n\n## Notes\n\nMore."),
        body("alpha", guidance="Do.\n\n# alpha\n\nMore."),
        body("alpha", when="Now.\n\n# Other"),
        body("alpha", guidance="Do.\n\n##\n\nMore."),
        body("alpha", guidance="Do.\n\n   ## Indented"),
        body("alpha", guidance="Do.\n\n> ## Quoted"),
        body("alpha", guidance="Do.\n\n- ## Listed"),
        body("alpha", guidance="Do.\n\n1. ## Numbered"),
        body("alpha").replace("## When\n", "## When ##\n"),
        body("alpha").replace("## When\n", "##  When\n"),
        body("alpha").replace("## Guidance\n", "## guidance\n"),
        body("alpha").replace("## Applies to\n", "## Applies to:\n"),
        body("alpha", guidance="```c\n# define X 1\n```"),
        body("alpha", guidance="~~~\n## Extra\n~~~"),
        body("alpha", guidance="Do.\n\n- a\n  ~~~\n## Extra\n  ~~~"),
        body("alpha", guidance="Do.\n\n<div>\n~~~\n</div>\n\n## Extra\n\n~~~"),
        body("alpha", guidance="Do.\n\n<!--\n~~~\n-->\n## Extra\n~~~"),
        body("alpha", guidance="Do. text <h2>x</h2>"),
        body("alpha", guidance="Do.\n\n<div><h1>x</h1></div>"),
        body("alpha", guidance="Do.\n\n    ```\n## Extra\n    ```"),
        body("alpha", guidance="Do.\n\n- ```\n## Extra\n- ```"),
        body("alpha", guidance="Do.\n\n> ```\n## Extra\n> ```"),
        body("alpha", guidance="Do.\n\n```a`b\n## Extra\n```"),
        body("alpha", guidance="Do.\n\n<h2>Extra</h2>"),
        body("alpha", guidance="Do.\n\n> <H1 class=x>Extra</H1>"),
        body("alpha", guidance="Do.\n\n<h1>"),
    ],
)
def test_wrong_headings(root, content):
    put(root, "alpha.md", content)
    refused(root, HEADINGS)


@pytest.mark.parametrize(
    "underline", ["===", "---", "-", "= ", "- ", "-\t", "> ---", "  =="]
)
def test_setext_underline(root, underline):
    put(root, "alpha.md", body("alpha", guidance=f"Do.\nTitle\n{underline}\nMore."))
    refused(root, "an entry file underlines a line as a heading")


def test_setext_underline_inside_a_fence(root):
    put(root, "alpha.md", body("alpha", guidance="```\ntext\n---\n```"))
    refused(root, "an entry file underlines a line as a heading")


def test_thematic_break_after_blank_line(root):
    guidance = "Do.\n\n---\n\nMore.\n\n***\n\n- a\n\n---"
    put(root, "alpha.md", body("alpha", guidance=guidance))
    assert technique("cpu_standin", "alpha", source=root)["text"] == guidance


APPLIES_WRONG = "Applies to is not the four lines kind, dtype, layout and language"


@pytest.mark.parametrize(
    "applies",
    [
        "",
        "\n".join(FP32_LINES[:3]),
        APPLIES + "\n- ext: x",
        APPLIES + "\n- language: c",
        "\n".join(reversed(FP32_LINES)),
        "\n".join(FP32_LINES[1:2] + FP32_LINES[:1] + FP32_LINES[2:]),
        APPLIES.replace("- kind", "* kind"),
        APPLIES.replace("- kind: ", "- kind:"),
        APPLIES.replace("- kind", "-  kind"),
        APPLIES.replace("- dtype", "- Dtype"),
        APPLIES.replace("- dtype", "\n- dtype"),
        APPLIES + "\nNote.",
    ],
)
def test_wrong_applies_to(root, applies):
    put(root, "alpha.md", body("alpha", applies=applies))
    refused(root, APPLIES_WRONG)


@pytest.mark.parametrize(
    ("member", "applies"),
    [
        ("language", APPLIES.replace("- language: c", "- language: c ")),
        ("dtype", APPLIES.replace("fp32", "FP32")),
        ("kind", APPLIES.replace("gemm", "")),
        ("layout", APPLIES.replace("row_major", "row-major")),
        ("kind", APPLIES.replace("gemm", "g" * 33)),
    ],
)
def test_applies_to_value_not_a_name(root, member, applies):
    put(root, "alpha.md", body("alpha", applies=applies))
    refused(
        root, f"Applies to: the {member} must be a name matching [a-z][a-z0-9_]{{0,31}}"
    )


@pytest.mark.parametrize(
    "key",
    [
        ("gemm", "fp16", "row_major", "c"),
        ("gemm", "fp32", "column_major", "c"),
        ("gemm", "bf16", "row_major", "cpp"),
        ("rmsnorm", "fp32", "row_major", "c"),
        ("matmul", "bf16", "row_major", "c"),
    ],
)
def test_applies_to_naming_no_contract(root, key):
    put(root, "alpha.md", body("alpha", applies=lines_of(key)))
    refused(root, "Applies to names no contract of the contract table")


@pytest.mark.parametrize("key", list(contract_table.TABLE), ids="-".join)
def test_an_entry_for_each_contract_of_the_table(root, key):
    put(root, "alpha.md", body("alpha", applies=lines_of(key)))
    assert check("cpu_standin", source=root) == ("alpha",)
    assert entries("cpu_standin", source=root)["alpha"].applies_to == AppliesTo(*key)


def test_applies_to_without_blank_lines(root):
    content = (
        "# alpha\n## Applies to\n" + APPLIES + "\n## When\nNow.\n## Guidance\nDo.\n"
    )
    put(root, "alpha.md", content)
    assert technique("cpu_standin", "alpha", source=root)["text"] == "Do."


@pytest.mark.parametrize("when", ["", " ", "\n\n\t"])
def test_empty_when(root, when):
    put(root, "alpha.md", body("alpha", when=when))
    refused(root, "the When section is empty")


@pytest.mark.parametrize("guidance", ["", "  ", "\n\n", "\t \n"])
def test_empty_guidance(root, guidance):
    put(root, "alpha.md", body("alpha", guidance=guidance))
    refused(root, "the Guidance section is empty")


def test_unknown_id(root):
    put(root, "alpha.md", body("alpha"))
    with pytest.raises(KeyError):
        technique("cpu_standin", "beta", source=root)


@pytest.mark.parametrize("entry_id", ["", "Alpha", "alpha.md", "1a", "a" * 33, "a b"])
def test_id_not_a_name(root, entry_id):
    put(root, "alpha.md", body("alpha"))
    with pytest.raises(InvalidCatalogError):
        technique("cpu_standin", entry_id, source=root)


@pytest.mark.parametrize("entry_id", [None, b"alpha", 1])
def test_id_not_a_str(root, entry_id):
    put(root, "alpha.md", body("alpha"))
    with pytest.raises(TypeError):
        technique("cpu_standin", entry_id, source=root)


def test_technique_checks_the_whole_directory(root):
    put(root, "alpha.md", body("alpha"))
    put(root, "beta.md", body("beta", when=""))
    with pytest.raises(InvalidCatalogError):
        technique("cpu_standin", "alpha", source=root)


def test_technique_missing_directory(root):
    with pytest.raises(FileNotFoundError):
        technique("mock", "alpha", source=root)


def test_criteria_of_every_entry_sorted(root):
    for name in ("zeta", "alpha"):
        put(root, f"{name}.md", body(name, when=f"When {name}.\n\n### Sub\n\nMore."))
    assert criteria("cpu_standin", source=str(root)) == {
        "alpha": "When alpha.\n\n### Sub\n\nMore.",
        "zeta": "When zeta.\n\n### Sub\n\nMore.",
    }
    assert list(criteria("cpu_standin", source=root)) == ["alpha", "zeta"]


def test_criteria_strip_line_feeds_only(root):
    content = (
        "# alpha\n## Applies to\n" + APPLIES + "\n## When\n\n\n  Now.\t\n\n\n"
        "## Guidance\nDo it.\n"
    )
    put(root, "alpha.md", content)
    assert criteria("cpu_standin", source=root) == {"alpha": "  Now.\t"}


def test_criteria_of_an_empty_directory(root):
    assert criteria("cpu_standin", source=root) == {}


def test_criteria_returns_a_new_dict(root):
    put(root, "alpha.md", body("alpha"))
    first = criteria("cpu_standin", source=root)
    first["alpha"] = "changed"
    assert criteria("cpu_standin", source=root) == {
        "alpha": "Worth trying when n is above 1."
    }


def test_criteria_of_the_committed_catalog():
    found = criteria("cpu_standin")
    assert sorted(found) == list(ALL_COMMITTED)
    assert all(text.strip() and "## " not in text for text in found.values())


def test_criteria_refuse_as_check_does(root, tmp_path):
    with pytest.raises(FileNotFoundError):
        criteria("cpu_standin", source=tmp_path / "absent")
    with pytest.raises(InvalidCatalogError):
        criteria("CPU", source=root)
    with pytest.raises(TypeError):
        criteria(3, source=root)
    put(root, "alpha.md", body("alpha", when=" "))
    with pytest.raises(InvalidCatalogError, match="the When section is empty"):
        criteria("cpu_standin", source=root)


def test_entries_of_every_entry_sorted(root):
    put(root, "beta.md", body("beta", applies=lines_of(BF16_GEMM), guidance="B."))
    put(root, "alpha.md", body("alpha", when="Now."))
    found = entries("cpu_standin", source=str(root))
    assert list(found) == ["alpha", "beta"]
    assert found["alpha"] == Entry(FP32, "Now.", "Do it.")
    assert found["beta"] == Entry(BF16_GEMM, "Worth trying when n is above 1.", "B.")
    assert found["alpha"].applies_to.dtype == "fp32"


def test_entries_of_an_empty_directory_and_a_new_dict(root):
    assert entries("cpu_standin", source=root) == {}
    put(root, "alpha.md", body("alpha"))
    first = entries("cpu_standin", source=root)
    first.clear()
    assert list(entries("cpu_standin", source=root)) == ["alpha"]


def test_entries_refuse_as_check_does(root, tmp_path):
    with pytest.raises(FileNotFoundError):
        entries("cpu_standin", source=tmp_path / "missing")
    with pytest.raises(InvalidCatalogError):
        entries("CPU", source=root)
    with pytest.raises(TypeError):
        entries(3, source=root)
    with pytest.raises(TypeError):
        entries("cpu_standin", source=3)
    fp16 = lines_of(("gemm", "fp16", "row_major", "c"))
    put(root, "alpha.md", body("alpha", applies=fp16))
    with pytest.raises(InvalidCatalogError, match="names no contract"):
        entries("cpu_standin", source=root)


MATCHING = {"kind": "gemm", "dtype": "fp32", "layout": "row_major", "language": "c"}


def test_the_values_of_applies_to_match():
    assert applies(FP32, **MATCHING) is True
    assert mismatch(FP32, **MATCHING) is None


@pytest.mark.parametrize(
    ("member", "other"),
    [
        ("kind", "rmsnorm"),
        ("dtype", "bf16"),
        ("layout", "column_major"),
        ("language", "cpp"),
        ("kind", ""),
        ("dtype", "FP32"),
        ("layout", "row_major "),
    ],
)
def test_each_differing_member_does_not_apply(member, other):
    given = MATCHING | {member: other}
    assert applies(FP32, **given) is False
    assert mismatch(FP32, **given) == (member, MATCHING[member])


def test_the_first_difference_in_the_order_of_applies_to_is_named():
    given = {"kind": "rope", "dtype": "bf16", "layout": "x", "language": "y"}
    assert mismatch(FP32, **given) == ("kind", "gemm")
    assert mismatch(FP32, **(given | {"kind": "gemm"})) == ("dtype", "fp32")


@pytest.mark.parametrize("member", sorted(MATCHING))
@pytest.mark.parametrize("value", [None, 3, b"gemm", ["gemm"]])
def test_a_value_that_is_not_a_str_is_refused(member, value):
    given = MATCHING | {member: value}
    with pytest.raises(TypeError, match=f"{member} must be a str"):
        applies(FP32, **given)
    with pytest.raises(TypeError, match=f"{member} must be a str"):
        mismatch(FP32, **given)


@pytest.mark.parametrize(
    "applies_to", [None, tuple(FP32), list(FP32), "gemm", MATCHING]
)
def test_applies_to_that_is_not_an_applies_to_is_refused(applies_to):
    with pytest.raises(TypeError, match="applies_to must be an AppliesTo"):
        applies(applies_to, **MATCHING)
    with pytest.raises(TypeError, match="applies_to must be an AppliesTo"):
        mismatch(applies_to, **MATCHING)


def test_the_comparison_is_made_against_each_entry_s_own_values():
    bf16 = MATCHING | {"dtype": "bf16"}
    assert applies(BF16_GEMM, **MATCHING) is False
    assert mismatch(BF16_GEMM, **MATCHING) == ("dtype", "bf16")
    assert applies(BF16_GEMM, **bf16) is True
    assert mismatch(FP32, **bf16) == ("dtype", "fp32")
    rope = AppliesTo("rope", "bf16", "row_major", "c")
    assert applies(rope, **(bf16 | {"kind": "rope"})) is True
    assert mismatch(rope, **bf16) == ("kind", "rope")
