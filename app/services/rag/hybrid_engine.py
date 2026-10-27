"""Hybrid RAG Engine with Reciprocal Rank Fusion, Dense pgvector, and Citation Provenance.

Combines:
1. Dense Vector Similarity Search (pgvector cosine distance <=> operator)
2. Sparse Keyword Matching (BM25 token intersection + phrase exact boost)
3. Reciprocal Rank Fusion (RRF) Reranking: RRF(d) = 1/(k + rank_dense) + 1/(k + rank_sparse)
4. Exact Citation & Provenance Assembling with page numbers and source URLs
"""
import re
import logging
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.models.enterprise import KnowledgeChunk
from app.models.agents import KnowledgeDocument
from app.models.deal_room import EvidenceRecord
from app.services.rag.embedder import embed_single

logger = logging.getLogger(__name__)


STOP_WORDS = {
    "the", "and", "for", "with", "that", "this", "are", "from", "about", "tell",
    "what", "does", "how", "why", "who", "when", "where", "can", "you", "all",
    "our", "your", "its", "was", "were", "been", "have", "has", "had", "will",
    "would", "could", "should", "not", "but", "into", "also", "than", "then", "per",
}

# A follow-up that says the site was crawled should still open the company profile,
# not an application form that happens to contain the word "full".
_SITE_LOOKUP_CUES = (
    "crawled",
    "company website",
    "knowledge base",
    "company knowledge",
    "full website",
    "our website",
    "the website",
    "who are we",
    "about the company",
    "about us",
)
_JOB_TERMS = ("job", "career", "hiring", "intern", "role", "apply", "vacancy", "opening")


def _query_tokens(query: str) -> set:
    return {w for w in re.findall(r"\b[a-z0-9]{3,}\b", (query or "").lower()) if w not in STOP_WORDS}


def _host_label(url: str) -> str:
    host = (urlparse(url or "").netloc or "").lower()
    if host.startswith("www."):
        host = host[4:]
    label = host.split(":")[0].split(".")[0]
    return re.sub(r"[^a-z0-9]", "", label)


def _url_path(url: str) -> str:
    path = (urlparse(url or "").path or "/").lower()
    if len(path) > 1:
        path = path.rstrip("/")
    return path or "/"


def _is_profile_url(url: str) -> bool:
    path = _url_path(url)
    if "/career" in path or "/jobs" in path or "/blog" in path or "/privacy" in path:
        return False
    if path in {"/", "/home", "/about", "/about-us", "/company"}:
        return True
    return path.endswith("/about") or path.endswith("/about-us")


def _is_application_form(text: str) -> bool:
    lowered = (text or "").lower()
    return "full name" in lowered and ("resume" in lowered or "cover letter" in lowered)


def _query_wants_jobs(query: str) -> bool:
    lowered = (query or "").lower()
    return any(re.search(rf"\b{term}\b", lowered) for term in _JOB_TERMS)


def query_requests_company_knowledge(query: str, source_urls: Optional[List[str]] = None) -> bool:
    """True when the user is asking who the company is or to use the crawled site."""
    lowered = (query or "").lower()
    if any(cue in lowered for cue in _SITE_LOOKUP_CUES):
        return True
    identity = bool(re.search(r"\b(what|who|describe|explain)\b", lowered) or "tell me about" in lowered)
    if not identity:
        return False
    terms = {term for term in _query_tokens(query) if len(term) >= 5}
    if not terms:
        return False
    for url in source_urls or []:
        label = _host_label(url)
        matched = [term for term in terms if term in label]
        if len(matched) >= 2 or (len(matched) == 1 and matched[0] == label):
            return True
    return False


class HybridRAGEngine:
    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    def retrieve(
        self,
        query: str,
        *,
        top_k: int = 5,
        department: Optional[str] = None,
        category: Optional[str] = None,
        query_vector: Optional[List[float]] = None,
    ) -> List[Dict[str, Any]]:
        """Execute hybrid retrieval over knowledge chunks and atomic evidence."""
        query_tokens = {w for w in re.findall(r"\b[a-zA-Z0-9]{3,}\b", query.lower()) if w not in STOP_WORDS}
        
        # 1. Fetch active candidate chunks
        q = (
            self.db.query(KnowledgeChunk)
            .filter(
                KnowledgeChunk.tenant_id == self.tenant_id,
                KnowledgeChunk.is_active == True,  # noqa: E712
            )
        )
        if department and department.lower() not in ("all", "general"):
            q = q.filter(KnowledgeChunk.department.in_([department, "General", "general"]))
            
        chunks = q.limit(2000).all()

        # 2. Sparse / Keyword Scoring (BM25 token intersection approximation)
        sparse_scored = []
        for c in chunks:
            c_text = (c.content or "").lower()
            searchable = " ".join([
                c_text,
                (c.title or "").lower(),
                (c.source_url or "").lower(),
            ])
            c_tokens = set(re.findall(r"\b[a-zA-Z0-9]{3,}\b", searchable))
            
            overlap = len(query_tokens & c_tokens)
            exact_boost = 5 if query.lower() in c_text else 0
            
            # Additional hint boost if embedding_hint overlaps
            hint_tokens = set((c.embedding_hint or "").lower().split())
            hint_overlap = len(query_tokens & hint_tokens)

            score = overlap + exact_boost + (hint_overlap * 2)
            # Application forms share ordinary words such as "full" with website checks.
            if _is_application_form(c_text) and not _query_wants_jobs(query):
                score *= 0.15
            if score > 0:
                sparse_scored.append({"item": c, "score": score})

        sparse_scored.sort(key=lambda x: x["score"], reverse=True)
        sparse_ranks = {item["item"].id: idx + 1 for idx, item in enumerate(sparse_scored)}

        # 3. Dense Vector Scoring (pgvector cosine distance)
        dense_ranks = {}
        if query_vector:
            try:
                dialect = self.db.bind.dialect.name if self.db.bind else ""
                if dialect == "postgresql":
                    sql = text("""
                        SELECT id, 1 - (embedding <=> :vector) as sim
                        FROM knowledge_chunks
                        WHERE tenant_id = :tenant_id 
                          AND is_active = true 
                          AND embedding IS NOT NULL
                        ORDER BY embedding <=> :vector
                        LIMIT 30
                    """)
                    rows = self.db.execute(sql, {"tenant_id": self.tenant_id, "vector": query_vector}).fetchall()
                    dense_ranks = {r[0]: idx + 1 for idx, r in enumerate(rows)}
            except Exception as e:
                logger.debug(f"pgvector query skipped or failed: {e}")

        # 4. Reciprocal Rank Fusion (RRF, k=60)
        k_rrf = 60
        fused_scores = {}
        all_chunk_ids = set(sparse_ranks.keys()) | set(dense_ranks.keys())

        for chunk_id in all_chunk_ids:
            score = 0.0
            if chunk_id in sparse_ranks:
                score += 1.0 / (k_rrf + sparse_ranks[chunk_id])
            if chunk_id in dense_ranks:
                score += 1.0 / (k_rrf + dense_ranks[chunk_id])
            fused_scores[chunk_id] = score

        # Sort chunks by fused score
        sorted_chunk_ids = sorted(fused_scores.keys(), key=lambda cid: fused_scores[cid], reverse=True)[:top_k]
        
        # Build results with citations
        results = []
        chunk_map = {c.id: c for c in chunks}
        
        for cid in sorted_chunk_ids:
            chunk = chunk_map.get(cid)
            if chunk:
                # Format page / url citation
                page_info = f" p.{chunk.page_start}" if chunk.page_start else ""
                url_info = f" ({chunk.source_url})" if chunk.source_url and chunk.source_url.startswith("http") else ""
                citation = f"[{chunk.title or 'KB Document'}{page_info}{url_info}] (chunk:{chunk.id[:8]} v{chunk.version})"
                
                results.append(self._hit_from_chunk(chunk, round(fused_scores[cid], 4), citation))

        results = self._prefer_company_profile(query, chunks, results, top_k)
        source_urls = [chunk.source_url for chunk in chunks if chunk.source_url]
        profile_requested = query_requests_company_knowledge(query, source_urls)
        has_profile = any(_is_profile_url(hit.get("source_url") or "") for hit in results)
        if profile_requested and not has_profile:
            profiles = [
                hit for hit in self._document_fallback(query, top_k)
                if _is_profile_url(hit.get("source_url") or "")
            ]
            if profiles:
                results = (profiles + results)[:top_k]
        if not results:
            return self._document_fallback(query, top_k)
        return results

    def _hit_from_chunk(self, chunk: KnowledgeChunk, score: float, citation: Optional[str] = None) -> Dict[str, Any]:
        if citation is None:
            page_info = f" p.{chunk.page_start}" if chunk.page_start else ""
            url_info = f" ({chunk.source_url})" if chunk.source_url and str(chunk.source_url).startswith("http") else ""
            citation = f"[{chunk.title or 'KB Document'}{page_info}{url_info}] (chunk:{str(chunk.id)[:8]} v{chunk.version})"
        return {
            "chunk_id": chunk.id,
            "document_id": chunk.document_id,
            "title": chunk.title,
            "content": chunk.content,
            "citation": citation,
            "page_start": chunk.page_start,
            "page_end": chunk.page_end,
            "source_url": chunk.source_url,
            "section_title": chunk.section_title,
            "score": score,
        }

    def _prefer_company_profile(
        self,
        query: str,
        chunks: List[KnowledgeChunk],
        results: List[Dict[str, Any]],
        top_k: int,
    ) -> List[Dict[str, Any]]:
        """Put the homepage and about page ahead of unrelated crawled pages."""
        source_urls = [c.source_url for c in chunks if c.source_url]
        source_urls.extend(hit.get("source_url") for hit in results if hit.get("source_url"))
        if not query_requests_company_knowledge(query, source_urls):
            return results

        ranked_profiles = sorted(
            (chunk for chunk in chunks if _is_profile_url(chunk.source_url or "")),
            key=lambda chunk: self._profile_quality(chunk, query),
            reverse=True,
        )
        chosen = []
        seen_text = set()
        for chunk in ranked_profiles:
            if self._profile_quality(chunk, query) < 8:
                break
            identity = re.sub(r"https?://\S+", "", (chunk.content or "").lower())
            identity = re.sub(r"\s+", " ", identity).strip()[:160]
            if not identity or identity in seen_text:
                continue
            seen_text.add(identity)
            chosen.append(chunk)
            if len(chosen) == 3:
                break
        if not chosen:
            return results

        merged: List[Dict[str, Any]] = []
        used = set()
        for chunk in chosen:
            merged.append(self._hit_from_chunk(chunk, 1.0))
            used.add(chunk.id)
        for hit in results:
            if hit.get("chunk_id") in used:
                continue
            merged.append(hit)
            if len(merged) >= top_k:
                break
        return merged[:top_k]

    def _document_fallback(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """Use stored pages when chunk retrieval has no company profile."""
        docs = (
            self.db.query(KnowledgeDocument)
            .filter(
                KnowledgeDocument.tenant_id == self.tenant_id,
                KnowledgeDocument.is_active == True,  # noqa: E712
            )
            .limit(200)
            .all()
        )
        tokens = _query_tokens(query)
        urls = [doc.source_url for doc in docs if doc.source_url]
        wants_profile = query_requests_company_knowledge(query, urls)
        ranked = []
        for doc in docs:
            blob = f"{doc.doc_type or ''} {doc.source_url or ''} {doc.content or ''}".lower()
            doc_tokens = set(re.findall(r"\b[a-z0-9]{3,}\b", blob))
            score = float(len(tokens & doc_tokens))
            if wants_profile and _is_profile_url(doc.source_url or ""):
                score += 8
            if _is_application_form(doc.content or "") and not _query_wants_jobs(query):
                score *= 0.15
            if score > 0:
                ranked.append((score, doc))
        ranked.sort(key=lambda item: item[0], reverse=True)
        hits = []
        for score, doc in ranked[:top_k]:
            url = doc.source_url or ""
            citation = f"[{doc.doc_type or 'Knowledge'} ({url})]" if url else f"[{doc.doc_type or 'Knowledge'}]"
            hits.append({
                "chunk_id": doc.id,
                "document_id": doc.id,
                "title": doc.doc_type,
                "content": (doc.content or "")[:1800],
                "citation": citation,
                "page_start": None,
                "page_end": None,
                "source_url": url or None,
                "section_title": doc.department,
                "score": score,
            })
        return hits

    @staticmethod
    def _profile_quality(chunk: KnowledgeChunk, query: str) -> int:
        text = chunk.content or ""
        lowered = text.lower()
        tokens = set(re.findall(r"\b[a-z0-9]{3,}\b", lowered))
        score = len(_query_tokens(query) & tokens)
        # Prefer the company description over the repeated navigation shell.
        if "who we are" in lowered or "company overview" in lowered:
            score += 12
        if re.search(r"\bis a\b|\bwe design\b|\bwe deliver\b|\bour mission\b", lowered):
            score += 6
        link_count = lowered.count("](") + lowered.count("http")
        if link_count >= 4:
            score -= 10
        if len(re.findall(r"[a-zA-Z]{3,}", text)) < 12:
            score -= 4
        return score

    async def async_retrieve(
        self,
        query: str,
        *,
        top_k: int = 5,
        department: Optional[str] = None,
        category: Optional[str] = None,
        query_vector: Optional[List[float]] = None,
    ) -> List[Dict[str, Any]]:
        """Async retrieve that automatically computes query vector if not supplied."""
        vec = query_vector
        if vec is None:
            try:
                vec = await embed_single(self.db, self.tenant_id, query)
            except Exception as e:
                logger.debug(f"Could not compute query vector: {e}")

        return self.retrieve(query, top_k=top_k, department=department, category=category, query_vector=vec)

    def assemble_context(
        self,
        query: str,
        *,
        top_k: int = 5,
        department: Optional[str] = None,
        query_vector: Optional[List[float]] = None,
    ) -> Dict[str, Any]:
        """Assemble cited context payload for LLM consumption."""
        hits = self.retrieve(query, top_k=top_k, department=department, query_vector=query_vector)
        
        if not hits:
            # Query atomic evidence directly as fallback
            evidence = (
                self.db.query(EvidenceRecord)
                .filter(EvidenceRecord.tenant_id == self.tenant_id, EvidenceRecord.is_valid == True)
                .limit(5)
                .all()
            )
            if evidence:
                context_blocks = [f"[{e.location_reference}]: {e.claim}" for e in evidence]
                return {
                    "mode": "evidence_grounded",
                    "context": "\n\n".join(context_blocks),
                    "citations": [e.location_reference for e in evidence],
                    "hits": len(evidence),
                }

            return {
                "mode": "empty",
                "context": "",
                "citations": [],
                "hits": 0,
            }

        context_parts = []
        citations = []
        for h in hits:
            context_parts.append(f"{h['citation']}:\n{h['content']}")
            citations.append(h["citation"])

        return {
            "mode": "grounded",
            "context": "\n\n---\n\n".join(context_parts),
            "citations": citations,
            "hits": len(hits),
        }
