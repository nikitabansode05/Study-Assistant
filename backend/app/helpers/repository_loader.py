from pathlib import Path
import re
import os
import shutil
import subprocess
import uuid
from ..config import REPOSITORIES_DIR, UPLOAD_DIR
from .document_loader import extract_file

SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "dist", "build", "__pycache__", ".next"}
MAX_MARKDOWN_FILES = 5000
MAX_FILE_BYTES = 2_000_000

async def normalize_github_url(url: str) -> str:
    url = url.strip()
    if url.endswith(".git"):
        url = url[:-4]
    if not re.fullmatch(r"https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/?", url):
        raise ValueError("Please enter a public GitHub repository URL like https://github.com/owner/repository")
    return url.rstrip("/")

async def import_repository(url: str, store):
    repo_url = await normalize_github_url(url)
    owner_repo = repo_url.rsplit("/", 2)[-2:]
    repo_label = "/".join(owner_repo)
    repo_key = uuid.uuid4().hex[:10]
    checkout_dir = REPOSITORIES_DIR / repo_key
    command = ["git", "clone", "--depth", "1", repo_url + ".git", str(checkout_dir)]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=180, check=False)
    except FileNotFoundError as exc:
        raise RuntimeError("Git was not found. Install Git for Windows, then restart VS Code.") from exc
    except subprocess.TimeoutExpired as exc:
        shutil.rmtree(checkout_dir, ignore_errors=True)
        raise RuntimeError("Repository download timed out. Try a smaller repository or check your connection.") from exc
    if result.returncode != 0:
        shutil.rmtree(checkout_dir, ignore_errors=True)
        detail = (result.stderr or result.stdout or "git clone failed").strip()
        raise RuntimeError(f"Could not clone repository: {detail[-900:]}")

    md_files = []
    for root, dirs, filenames in await os_walk_without_skips(checkout_dir):
        for filename in filenames:
            if Path(filename).suffix.lower() in {".md", ".markdown"}:
                full = Path(root) / filename
                try:
                    if full.stat().st_size <= MAX_FILE_BYTES:
                        md_files.append(full)
                except OSError:
                    pass
        if len(md_files) > MAX_MARKDOWN_FILES:
            shutil.rmtree(checkout_dir, ignore_errors=True)
            raise RuntimeError(f"Repository contains more than {MAX_MARKDOWN_FILES} Markdown files; import a smaller repository.")
    if not md_files:
        shutil.rmtree(checkout_dir, ignore_errors=True)
        raise RuntimeError("No .md or .markdown files were found in this repository.")

    indexed = []
    failures = []
    for md_path in md_files:
        relative = md_path.relative_to(checkout_dir).as_posix()
        display_name = f"{repo_label}/{relative}"
        saved_path = UPLOAD_DIR / f"{uuid.uuid4().hex}.md"
        try:
            shutil.copy2(md_path, saved_path)
            page_texts = extract_file(saved_path)
            item = store.add_document(display_name, saved_path, page_texts)
            item["repository"] = repo_label
            indexed.append(item)
        except Exception as exc:
            saved_path.unlink(missing_ok=True)
            failures.append(f"{relative}: {exc}")
    if not indexed:
        shutil.rmtree(checkout_dir, ignore_errors=True)
        raise RuntimeError("Markdown files were found, but none could be indexed. " + "; ".join(failures[:3]))
    return {
        "repository": repo_label,
        "url": repo_url,
        "markdown_files_found": len(md_files),
        "indexed_files": len(indexed),
        "failed_files": failures[:10],
        "documents": indexed,
    }

async def os_walk_without_skips(root: Path):
    import os
    for current, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        yield current, dirs, files
