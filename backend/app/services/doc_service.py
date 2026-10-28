from pathlib import Path, PurePosixPath
import shutil
import uuid
import zipfile
from fastapi import Depends, UploadFile, File, Header, HTTPException
from app.helpers.auth import  require_mentor
from app.config import UPLOAD_DIR
from app.helpers.document_loader import extract_file, SUPPORTED
from app.helpers.ollama_client import OllamaError
from app.schemas.tflrag_schemas import RepositoryRequest
from app.helpers.repository_loader import import_repository

class DocService:

    def __init__(self,store):
        self.store = store

    async def _display_name(self,filename: str | None, fallback: str = "upload") -> str:
            """Safe display name for an uploaded file.
    
            Folder imports send the browser's relative path (e.g. ``docs/guide/README.md``) so
            sources stay distinguishable. The file itself is always stored under a random UUID name,
            so this value is used for display/citations only.
            """
            raw = (filename or fallback).replace("\\", "/")
            parts = [p for p in PurePosixPath(raw).parts if p not in ("", ".", "..", "/")]
            name = "/".join(parts)[-300:]
            return name or fallback

    async def upload_document(self,file: UploadFile = File(...), _mentor: dict = Depends(require_mentor)):
            original_name = await self._display_name(file.filename)
            ext = Path(original_name).suffix.lower()
            if ext not in SUPPORTED:
                raise HTTPException(status_code=400, detail=f"Unsupported file type. Supported: {', '.join(sorted(SUPPORTED))}")
            
            saved_name = f"{uuid.uuid4().hex}{ext}"
            saved_path = UPLOAD_DIR / saved_name
            
            try:
                with saved_path.open("wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)
                extracted = await extract_file(saved_path)
                result = await self.store.add_document(original_name, saved_path, extracted)
                return {"message": "Document indexed successfully", **result}
            except OllamaError as exc:
                saved_path.unlink(missing_ok=True)
                raise HTTPException(status_code=503, detail=str(exc)) from exc
            except ValueError as exc:
                saved_path.unlink(missing_ok=True)
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            except Exception as exc:
                saved_path.unlink(missing_ok=True)
                raise HTTPException(status_code=500, detail=f"Document processing failed: {exc}") from exc
            finally:
                await file.close()

    async def list_documents(self):
            return {"documents":self.store.list_documents()}
    
    async def import_github_repository(self,request: RepositoryRequest, _mentor: dict = Depends(require_mentor)):
            try:
                return await import_repository(request.url, self.store)
            except (ValueError, RuntimeError, OllamaError) as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
    
    async def upload_repository_zip(self,file: UploadFile = File(...), _mentor: dict = Depends(require_mentor)):
            """Index Markdown files from a locally supplied GitHub source ZIP."""
            original_name = Path(file.filename or "repository.zip").name
            if Path(original_name).suffix.lower() != ".zip":
                raise HTTPException(status_code=400, detail="Please upload a .zip archive downloaded from GitHub.")
    
            temp_zip = UPLOAD_DIR / f"{uuid.uuid4().hex}.zip"
            try:
                with temp_zip.open("wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)
                try:
                    archive = zipfile.ZipFile(temp_zip)
                except zipfile.BadZipFile as exc:
                    raise HTTPException(status_code=400, detail="This file is not a valid ZIP archive.") from exc
    
                with archive:
                    candidates = []
                    total_uncompressed = 0
                    for info in archive.infolist():
                        path = Path(info.filename)
                        if info.is_dir() or path.suffix.lower() not in {".md", ".markdown"}:
                            continue
                        # Avoid unsafe paths and oversized archives/files. Files are read from the ZIP, never extracted.
                        if path.is_absolute() or ".." in path.parts:
                            continue
                        if info.file_size > 2_000_000:
                            continue
                        total_uncompressed += info.file_size
                        if total_uncompressed > 200_000_000:
                            raise HTTPException(status_code=413, detail="Markdown content in this ZIP exceeds 200 MB.")
                        candidates.append(info)
                        if len(candidates) > 5000:
                            raise HTTPException(status_code=413, detail="ZIP contains more than 5,000 Markdown files.")
    
                    if not candidates:
                        raise HTTPException(status_code=400, detail="No .md or .markdown files were found in the ZIP.")
    
                    repo_label = Path(original_name).stem
                    indexed = []
                    failures = []
                    for info in candidates:
                        relative = Path(info.filename)
                        # GitHub ZIPs include one top-level wrapper directory; omit it for cleaner source names.
                        parts = relative.parts[1:] if len(relative.parts) > 1 else relative.parts
                        display_path = "/".join(parts) or relative.name
                        display_name = f"{repo_label}/{display_path}"
                        saved_path = UPLOAD_DIR / f"{uuid.uuid4().hex}.md"
                        try:
                            with archive.open(info) as source, saved_path.open("wb") as target:
                                shutil.copyfileobj(source, target)
                            extracted = extract_file(saved_path)
                            item = await self.store.add_document(display_name, saved_path, extracted)
                            indexed.append(item)
                        except Exception as exc:
                            saved_path.unlink(missing_ok=True)
                            failures.append(f"{display_path}: {exc}")
    
                    if not indexed:
                        raise HTTPException(status_code=400, detail="Markdown files were found, but none could be indexed. " + "; ".join(failures[:3]))
                    return {
                        "repository": repo_label,
                        "markdown_files_found": len(candidates),
                        "indexed_files": len(indexed),
                        "failed_files": failures[:10],
                    }
            except HTTPException:
                raise
            except OllamaError as exc:
                raise HTTPException(status_code=503, detail=str(exc)) from exc
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            except Exception as exc:
                raise HTTPException(status_code=500, detail=f"ZIP processing failed: {exc}") from exc
            finally:
                temp_zip.unlink(missing_ok=True)
                await file.close()
    
    async def delete_document(self,document_id: str, _mentor: dict = Depends(require_mentor)):
            try:
                deleted =await self.store.delete_document(document_id)
            except OllamaError as exc:
                raise HTTPException(status_code=503, detail=str(exc)) from exc
            if not deleted:
                raise HTTPException(status_code=404, detail="Document not found")
            return {"message": "Document deleted"}
    
    
    
    