"""Integração com Supabase para armazenamento e recuperação de embeddings."""

import os
import logging
from typing import Any, Dict, List

from supabase import Client, create_client
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from PyPDF2 import PdfReader

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client | None = None
embeddings_model: OpenAIEmbeddings | None = None

if SUPABASE_URL and SUPABASE_KEY and os.getenv("OPENAI_API_KEY"):
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    embeddings_model = OpenAIEmbeddings(model="text-embedding-ada-002")


# ---------------------------------------------------------------------------
# Inicialização e utilidades
# ---------------------------------------------------------------------------

def initialize_supabase() -> None:
    """Cria a tabela de documentos e habilita a extensão vetorial."""
    if not supabase:
        logger.warning("Cliente Supabase não configurado; pulando inicialização.")
        return
    try:
        supabase.postgrest.rpc(
            "exec_sql",
            {
                "sql": (
                    "CREATE EXTENSION IF NOT EXISTS vector;"
                    "CREATE TABLE IF NOT EXISTS documents ("
                    "id uuid PRIMARY KEY DEFAULT gen_random_uuid(),"
                    "content text,"
                    "embedding vector(1536),"
                    "metadata jsonb"
                    ");"
                )
            },
        ).execute()
        logger.info("Tabela documents verificada/criada.")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Falha ao preparar tabela no Supabase: %s", exc)


def preprocess_document(file_path: str) -> str:
    """Extrai texto de um arquivo PDF ou texto simples."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")

    if file_path.lower().endswith(".pdf"):
        text = ""
        with open(file_path, "rb") as fp:
            reader = PdfReader(fp)
            for page in reader.pages:
                text += page.extract_text() or ""
        return text

    with open(file_path, "r", encoding="utf-8") as fp:
        return fp.read()


def upsert_documents(chunks: List[Dict[str, Any]]) -> None:
    """Insere ou atualiza documentos chunkados no Supabase com embeddings."""
    if not supabase or not embeddings_model:
        logger.warning("Supabase ou modelo de embeddings não inicializado.")
        return

    texts = [c["content"] for c in chunks]
    embeddings = embeddings_model.embed_documents(texts)
    rows = []
    for chunk, emb in zip(chunks, embeddings):
        rows.append(
            {
                "id": chunk.get("id"),
                "content": chunk["content"],
                "embedding": emb,
                "metadata": chunk.get("metadata", {}),
            }
        )
    try:
        supabase.table("documents").upsert(rows).execute()
        logger.info("Chunks inseridos no Supabase.")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Erro ao inserir chunks: %s", exc)


def retrieve_relevant_documents(
    query: str, match_threshold: float = 0.78, top_k: int = 5
) -> List[Dict[str, Any]]:
    """Busca vetorial no Supabase para recuperar os chunks mais relevantes."""
    if not supabase or not embeddings_model:
        logger.warning("Supabase ou modelo de embeddings não inicializado.")
        return []

    query_embedding = embeddings_model.embed_query(query)
    try:
        response = supabase.rpc(
            "match_documents",
            {
                "query_embedding": query_embedding,
                "match_count": top_k,
                "match_threshold": match_threshold,
            },
        ).execute()
        return response.data or []
    except Exception as exc:  # noqa: BLE001
        logger.warning("Erro ao executar busca vetorial: %s", exc)
        return []


def preload_example_documents() -> None:
    """Carrega documentos de exemplo no Supabase para testes iniciais."""
    example_docs = [
        {
            "content": "Relatório Focus projeta inflação de 3.9% para 2024.",
            "metadata": {"source": "Focus"},
        },
        {
            "content": "Ata do COPOM registra manutenção da taxa Selic em 13.75%.",
            "metadata": {"source": "COPOM"},
        },
    ]
    upsert_documents(example_docs)


# ---------------------------------------------------------------------------
# Ingestão utilitária de arquivos (opcional)
# ---------------------------------------------------------------------------

def ingest_pdf(file_path: str, source: str) -> None:
    """Exemplo de ingestão de um PDF para o Supabase."""
    text = preprocess_document(file_path)
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = [{"content": c, "metadata": {"source": source}} for c in splitter.split_text(text)]
    upsert_documents(chunks)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    initialize_supabase()
    preload_example_documents()
    print(retrieve_relevant_documents("inflação"))
