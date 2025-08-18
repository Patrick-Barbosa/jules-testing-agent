# 2_postgresql_session_management.py

import os
from typing import List

from supabase import Client, create_client

# --- Configuração da Conexão com Supabase ---
# As credenciais devem ser carregadas de variáveis de ambiente para segurança.
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client | None = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    print("Variáveis SUPABASE_URL/SUPABASE_KEY não configuradas.")


def setup_database() -> None:
    """Verifica a existência da tabela de histórico no Supabase."""
    if not supabase:
        print("Cliente Supabase não configurado; impossível verificar tabela.")
        return
    try:
        supabase.table("conversation_history").select("session_id").limit(1).execute()
        print("Tabela 'conversation_history' pronta no Supabase.")
    except Exception as e:  # noqa: BLE001
        print(f"Erro ao verificar tabela 'conversation_history': {e}")


def save_conversation_history(session_id: str, history: List[dict]) -> None:
    """Salva ou atualiza o histórico de uma conversa no Supabase."""
    if not supabase:
        print("Cliente Supabase não configurado; não foi possível salvar o histórico.")
        return
    try:
        supabase.table("conversation_history").upsert(
            {"session_id": session_id, "history": history}
        ).execute()
        print(f"Histórico da sessão '{session_id}' salvo com sucesso.")
    except Exception as e:  # noqa: BLE001
        print(f"Erro ao salvar o histórico da sessão '{session_id}': {e}")


def load_conversation_history(session_id: str) -> List[dict]:
    """Carrega o histórico de uma conversa do Supabase."""
    if not supabase:
        print("Cliente Supabase não configurado; não foi possível carregar o histórico.")
        return []
    try:
        resp = (
            supabase.table("conversation_history")
            .select("history")
            .eq("session_id", session_id)
            .single()
            .execute()
        )
        data = resp.data or {}
        if "history" in data:
            print(f"Histórico da sessão '{session_id}' carregado com sucesso.")
            return data["history"]
        print(f"Nenhum histórico encontrado para a sessão '{session_id}'.")
        return []
    except Exception as e:  # noqa: BLE001
        print(f"Erro ao carregar o histórico da sessão '{session_id}': {e}")
        return []


if __name__ == "__main__":
    print("Gerenciador de Sessão com Supabase.")
    if not supabase:
        print("Configure SUPABASE_URL e SUPABASE_KEY para testar a conexão.")
    else:
        setup_database()
        session_id_exemplo = "user_12345"
        conversa_exemplo = [
            {"role": "user", "content": "Olá, qual a projeção do PIB para este ano?"},
            {
                "role": "assistant",
                "content": "Consultando os dados mais recentes... A projeção do PIB é de 2.5%.",
            },
        ]
        save_conversation_history(session_id_exemplo, conversa_exemplo)
        historico_carregado = load_conversation_history(session_id_exemplo)
        if historico_carregado:
            print("\n--- Histórico Carregado ---")
            for message in historico_carregado:
                print(f"{message['role']}: {message['content']}")
            print("---------------------------\n")
