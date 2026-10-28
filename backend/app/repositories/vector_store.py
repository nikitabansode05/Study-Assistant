import json
import uuid
from pathlib import Path
import faiss
import numpy as np
from ..config import INDEX_PATH, RECORDS_PATH, DOCUMENTS_PATH, UPLOAD_DIR
from ..helpers.ollama_client import embed_texts
from ..helpers.chunking import split_text

class TFLKnowledgeCore:
    def __init__(self):
        self.index = None
        self.records = []
        self.documents = []
        self._load()

    def _load(self):
        if INDEX_PATH.exists() and RECORDS_PATH.exists():
            self.index = faiss.read_index(str(INDEX_PATH))
            self.records = json.loads(RECORDS_PATH.read_text(encoding="utf-8"))
        if DOCUMENTS_PATH.exists():
            self.documents = json.loads(DOCUMENTS_PATH.read_text(encoding="utf-8"))

    def _save(self):
        if self.index is not None:
            faiss.write_index(self.index, str(INDEX_PATH))
        RECORDS_PATH.write_text(json.dumps(self.records, ensure_ascii=False, indent=2), encoding="utf-8")
        DOCUMENTS_PATH.write_text(json.dumps(self.documents, ensure_ascii=False, indent=2), encoding="utf-8")

    def list_documents(self):
        return self.documents

    async def add_document(self, filename: str, saved_path: Path, page_texts: list[dict]):
        doc_id = str(uuid.uuid4())
        chunk_records = []
        for item in page_texts:
            for j, chunk in enumerate(await split_text(item["text"])):
                chunk_records.append({
                    "document_id": doc_id,
                    "document": filename,
                    "page": item.get("page"),
                    "chunk_id": f"{doc_id[:8]}-{len(chunk_records)+1}",
                    "text": chunk,
                })
        if not chunk_records:
            raise ValueError("No text chunks were created from this document.")
        
        vectors = np.asarray(await embed_texts([r["text"] for r in chunk_records]), dtype="float32")
        faiss.normalize_L2(vectors)
        if self.index is None:
            self.index = faiss.IndexFlatIP(vectors.shape[1])
        elif self.index.d != vectors.shape[1]:
            raise ValueError("Embedding dimensions changed. Keep the same embedding model for this index.")
        self.index.add(vectors)
        self.records.extend(chunk_records)
        self.documents.append({
            "id": doc_id,
            "filename": filename,
            "chunks": len(chunk_records),
            "stored_as": saved_path.name,
        })
        self._save()
        return {"id": doc_id, "filename": filename, "chunks": len(chunk_records)}

    async def search(self, question: str, top_k: int = 4):
        if self.index is None or not self.records or self.index.ntotal == 0:
            return []
        query_vector = np.asarray(await embed_texts([question]), dtype="float32")
        faiss.normalize_L2(query_vector)
        scores, indices = self.index.search(query_vector, min(top_k, len(self.records)))
        results = []
        for score, idx in zip(scores[0].tolist(), indices[0].tolist()):
            if idx < 0 or idx >= len(self.records):
                continue
            item = dict(self.records[idx])
            item["score"] = float(score)
            results.append(item)
        return results

    async def delete_document(self, document_id: str):
        doc = next((d for d in self.documents if d["id"] == document_id), None)
        if not doc:
            return False
        # Rebuild the index to keep vector rows aligned with the records after deletion.
        keep_indices = [i for i, r in enumerate(self.records) if r["document_id"] != document_id]
        kept_records = [self.records[i] for i in keep_indices]
        if kept_records:
            matrix = None
            # Reuse the stored vectors (IndexFlatIP keeps them) so deletion does not need Ollama
            # and does not re-embed the whole knowledge base. Fall back to re-embedding if the
            # index and records are out of sync.
            if self.index is not None and self.index.ntotal == len(self.records):
                try:
                    all_vectors = self.index.reconstruct_n(0, self.index.ntotal)
                    matrix = np.ascontiguousarray(all_vectors[keep_indices], dtype="float32")
                except RuntimeError:
                    matrix = None
            if matrix is None:
                vectors = await embed_texts([r["text"] for r in kept_records])
                matrix = np.asarray(vectors, dtype="float32")
                faiss.normalize_L2(matrix)
            self.index = faiss.IndexFlatIP(matrix.shape[1])
            self.index.add(matrix)
        else:
            self.index = None
            if INDEX_PATH.exists():
                INDEX_PATH.unlink()
        self.records = kept_records
        self.documents = [d for d in self.documents if d["id"] != document_id]
        stored = UPLOAD_DIR / doc["stored_as"]
        if stored.exists():
            stored.unlink()
        self._save()
        return True
