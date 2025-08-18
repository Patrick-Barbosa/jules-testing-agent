"""Script de inicialização do banco Supabase via Admin API.

Executa comandos SQL para habilitar extensões e criar tabelas
necessárias para o agente de investimentos. Requer que as
variáveis de ambiente SUPABASE_URL e SUPABASE_KEY (service_role)
estejam configuradas.
"""

import os
import json
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()

import requests

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ACCESS_TOKEN")

print(SUPABASE_URL)

def _get_project_ref(url: str) -> str:
    """Extrai o project ref da URL do Supabase."""
    return urlparse(url).hostname.split(".")[0]


def run_sql(sql: str) -> None:
    """Executa um comando SQL usando a Admin API do Supabase."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("SUPABASE_URL ou SUPABASE_KEY não configurados.")
        return

    project_ref = _get_project_ref(SUPABASE_URL)
    endpoint = f"https://api.supabase.com/v1/projects/{project_ref}/database/query"
    headers = {
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }
    payload = {"query": sql}

    try:
        resp = requests.post(endpoint, headers=headers, json=payload, timeout=30)
        if resp.status_code == 200 or resp.status_code == 201:
            print("   - Sucesso")
        else:
            print(f"   - Falha {resp.status_code}: {resp.text}")
    except Exception as exc:  # noqa: BLE001
        print(f"   - Erro de requisição: {exc}")


if __name__ == "__main__":
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("Configure SUPABASE_URL e SUPABASE_KEY antes de executar este script.")
    else:
        print("Inicializando banco de dados no Supabase...")
        steps = [
            ("Habilitando extensão pgcrypto...", "CREATE EXTENSION IF NOT EXISTS \"pgcrypto\";"),
            ("Habilitando extensão vector...", "CREATE EXTENSION IF NOT EXISTS vector;"),
            (
                "Criando tabela 'conversation_history'...",
                """
                CREATE TABLE IF NOT EXISTS conversation_history (
                    session_id text primary key,
                    history jsonb
                );
                """.strip(),
            ),
            (
                "Criando tabela 'documents'...",
                """
                CREATE TABLE IF NOT EXISTS documents (
                    id uuid primary key default gen_random_uuid(),
                    content text,
                    embedding vector(1536),
                    metadata jsonb
                );
                """.strip(),
            ),
            (
                "Criando índice para 'documents.embedding'...",
                "CREATE INDEX IF NOT EXISTS documents_embedding_idx ON documents USING ivfflat (embedding vector_l2_ops) WITH (lists = 100);",
            ),
            (
                "Criando função 'match_documents'...",
                """
                CREATE OR REPLACE FUNCTION match_documents(
                    query_embedding vector(1536),
                    match_threshold float,
                    match_count int
                ) RETURNS TABLE (
                    id uuid,
                    content text,
                    metadata jsonb,
                    similarity float
                ) LANGUAGE sql STABLE AS $$
                SELECT
                    id,
                    content,
                    metadata,
                    1 - (embedding <=> query_embedding) AS similarity
                FROM documents
                WHERE 1 - (embedding <=> query_embedding) > match_threshold
                ORDER BY similarity DESC
                LIMIT match_count;
                $$;
                """.strip(),
            ),
        ]

        for message, sql in steps:
            print(message)
            run_sql(sql)
        print("Inicialização concluída.")
