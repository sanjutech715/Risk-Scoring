"""Auto-generate enhanced README files for a repository.

Usage:
    python scripts/upgrade_readmes.py --root . --apply

By default this writes `README_ENHANCED.md` next to each `README*.md` found.
"""
from pathlib import Path
import argparse
import re
from datetime import datetime

HEADING_RE = re.compile(r'^(#{1,6})\s+(.*)')


def slugify(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s]+", "-", text)
    return text


def extract_headings(content: str):
    headings = []
    for line in content.splitlines():
        m = HEADING_RE.match(line)
        if m:
            level = len(m.group(1))
            title = m.group(2).strip()
            headings.append((level, title))
    return headings


def generate_toc(headings):
    lines = []
    for level, title in headings:
        if level == 1:
            continue
        indent = '  ' * (level - 2)
        link = f"#{slugify(title)}"
        lines.append(f"{indent}- [{title}]({link})")
    return "\n".join(lines)


def enhance_content(original: str, source_path: Path) -> str:
    headings = extract_headings(original)
    # try to find a title
    title = None
    for level, t in headings:
        if level == 1:
            title = t
            break
    if not title:
        title = source_path.parent.name or source_path.stem

    toc = generate_toc(headings)
    timestamp = datetime.utcnow().isoformat() + "Z"

    parts = []
    parts.append(f"# {title}")
    parts.append("")
    parts.append(f"_Enhanced README generated from `{source_path.name}` on {timestamp}_")
    parts.append("")
    if toc:
        parts.append("## Table of Contents")
        parts.append("")
        parts.append(toc)
        parts.append("")
    parts.append("---")
    parts.append("")
    parts.append(original)
    return "\n".join(parts)


def process_file(path: Path, apply: bool = True, backup: bool = True) -> Path:
    original = path.read_text(encoding='utf-8')
    enhanced = enhance_content(original, path)
    out_path = path.with_name('README_ENHANCED.md')
    if apply:
        if backup and out_path.exists():
            bak = out_path.with_suffix(out_path.suffix + f".bak.{int(datetime.utcnow().timestamp())}")
            out_path.replace(bak)
        out_path.write_text(enhanced, encoding='utf-8')
    return out_path


def find_readmes(root: Path):
    for p in root.rglob('README*.md'):
        # skip already enhanced files
        if p.name.lower().startswith('readme_enhanced'):
            continue
        yield p


def main():
    parser = argparse.ArgumentParser(description='Auto-upgrade README files to enhanced versions')
    parser.add_argument('--root', '-r', default='.', help='Root path to scan')
    parser.add_argument('--apply', action='store_true', help='Write changes (default: dry-run)')
    parser.add_argument('--backup', action='store_true', default=True, help='Backup existing enhanced files')
    args = parser.parse_args()

    root = Path(args.root).resolve()
    files = list(find_readmes(root))
    if not files:
        print('No README files found under', root)
        return

    for p in files:
        out = process_file(p, apply=args.apply, backup=args.backup)
        action = 'Wrote' if args.apply else 'Would write'
        print(f"{action}: {out}")


if __name__ == '__main__':
    main()
