"""Regression tests for public English-only documentation."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from check_public_english import violations  # noqa: E402


def test_public_text_contains_no_chinese_or_legacy_cn_docs():
    assert violations(ROOT) == []


def test_readme_links_to_english_operational_guides():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    for name in ("INSTALL.md", "P8_2D_PUBLIC_LAUNCH.md",
                 "P8_2E_FIRST_RECEIPT_ACCEPTANCE.md",
                 "P8_2F_LOCAL_PUBLIC_RECEIPT_BRIDGE.md"):
        assert f"]({name})" in text
        assert (ROOT / name).is_file()


def test_all_legacy_docs_have_english_replacements():
    from finish_english_only_migration import OLD_DOCUMENTS
    for name in OLD_DOCUMENTS:
        assert not (ROOT / name).exists()
        assert (ROOT / name.replace("_CN.md", ".md")).exists()


def test_local_markdown_links_remain_valid():
    import re
    documents = list(ROOT.glob("*.md")) + list((ROOT / "docs").glob("*.md"))
    for document in documents:
        content = document.read_text(encoding="utf-8")
        for target in re.findall(r"\]\(([^)]+)\)", content):
            base = target.split("#", 1)[0]
            if not base or base.startswith(("https:", "http:", "mailto:")):
                continue
            assert (document.parent / base).exists(), (document.name, target)
