from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

ACTIVE_PATHS = [
    ROOT / "src",
    ROOT / "scripts",
    ROOT / "app",
    ROOT / "web" / "src",
    ROOT / "README.md",
    ROOT / "docs",
]

LEGACY_TERMS = (
    "Solarium",
    "SOLARIUM",
    "solarium",
)


def iter_text_files(path: Path):
    if path.is_file():
        yield path
        return

    if not path.exists():
        return

    for candidate in path.rglob("*"):
        if (
            candidate.is_file()
            and "__pycache__" not in candidate.parts
        ):
            yield candidate


def test_active_release_surfaces_use_salarium_branding() -> None:
    violations = []

    for root in ACTIVE_PATHS:
        for path in iter_text_files(root):
            try:
                text = path.read_text(errors="ignore")
            except OSError:
                continue

            for term in LEGACY_TERMS:
                if term in text:
                    violations.append(
                        f"{path.relative_to(ROOT)} contains {term!r}"
                    )

    assert not violations, (
        "Legacy Solarium branding found in active release surfaces:\n"
        + "\n".join(violations)
    )
