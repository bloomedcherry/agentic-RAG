"""Download public raw seed documents for the enterprise RAG corpus."""

from __future__ import annotations

import argparse
import json
import re
import ssl
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse
from urllib.request import Request, urlopen

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PACKAGE_ROOT / "data" / "raw"
MANIFEST_PATH = RAW_DIR / "source_manifest.json"
ATTACHMENT_RE = re.compile(r"href=[\"']([^\"']+\.(?:pdf|docx?|PDF|DOCX?)(?:\?[^\"']*)?)[\"']")


def _download(url: str, timeout: int = 60) -> bytes:
    request = Request(url, headers={"User-Agent": "agent-rag-demo/0.1"})
    context = ssl.create_default_context()
    with urlopen(request, timeout=timeout, context=context) as response:
        return response.read()


def _write_file(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def _write_metadata(path: Path, entry: dict, source_url: str) -> None:
    metadata = {
        "source_url": source_url,
        "source_name": entry.get("name", ""),
        "declared_doc_type": entry.get("doc_type", ""),
    }
    path.with_suffix(path.suffix + ".meta.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _attachment_path(raw_dir: Path, entry: dict, attachment_url: str, ordinal: int) -> Path:
    parsed = urlparse(attachment_url)
    name = Path(unquote(parsed.path)).name or f"attachment_{ordinal}.bin"
    suffix_match = re.search(r"\.(pdf|docx?|PDF|DOCX?)(?:$|[?&])", attachment_url)
    suffix = suffix_match.group(1).lower() if suffix_match else Path(name).suffix.lower().lstrip(".")
    if suffix and not name.lower().endswith(f".{suffix}"):
        name = f"{Path(name).stem or f'attachment_{ordinal}'}.{suffix}"
    suffix = suffix or "bin"
    doc_type = entry.get("doc_type", "general")
    folder = {
        "policy": "policies",
        "workflow": "workflows",
        "project": "projects",
        "meeting": "meetings",
        "contract": "contracts",
        "report": "reports",
    }.get(doc_type, "general")
    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", name)
    return raw_dir / suffix / folder / safe_name


def _download_attachments(raw_dir: Path, entry: dict, html: bytes) -> list[Path]:
    text = html.decode("utf-8", errors="ignore")
    paths = []
    seen = set()
    for ordinal, match in enumerate(ATTACHMENT_RE.finditer(text), start=1):
        attachment_url = urljoin(entry["url"], match.group(1))
        if attachment_url in seen:
            continue
        seen.add(attachment_url)
        path = _attachment_path(raw_dir, entry, attachment_url, ordinal)
        _write_file(path, _download(attachment_url))
        _write_metadata(path, entry, attachment_url)
        paths.append(path)
    return paths


def download_manifest(
    manifest_path: str | Path = MANIFEST_PATH,
    raw_dir: str | Path = RAW_DIR,
) -> dict:
    raw_root = Path(raw_dir)
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    downloaded = []
    attachments = []

    for entry in manifest:
        content = _download(entry["url"])
        path = raw_root / entry["filename"]
        _write_file(path, content)
        _write_metadata(path, entry, entry["url"])
        downloaded.append(str(path))
        if entry.get("download_attachments"):
            attachments.extend(str(item) for item in _download_attachments(raw_root, entry, content))

    return {"downloaded": downloaded, "attachments": attachments}


def main() -> None:
    parser = argparse.ArgumentParser(description="Download public raw seed documents.")
    parser.add_argument("--manifest", default=str(MANIFEST_PATH))
    parser.add_argument("--raw-dir", default=str(RAW_DIR))
    args = parser.parse_args()

    result = download_manifest(manifest_path=args.manifest, raw_dir=args.raw_dir)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
