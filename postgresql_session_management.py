# 2_postgresql_session_management_refactored.py

import os
import logging
from typing import List, Dict, Any

from supabase import Client, create_client
from postgrest.exceptions import APIError  # Importa o erro específico da API
from dotenv import load_dotenv

load_dotenv()

# --- Configuração do Logging ---
# É uma prática melhor usar logging em vez de print para mensagens de status/erro.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class SessionManager:
    """Gerencia o histórico de conversas em uma tabela do Supabase."""

    def __init__(self, url: str, key: str):
        """
        Inicializa o cliente Supabase.
        Lança um ValueError se as credenciais não forem fornecidas.
        """
        if not url or not key:
            raise ValueError("As variáveis SUPABASE_URL e SUPABASE_KEY são necessárias.")
        
        try:
            self.client: Client = create_client(url, key)
            logging.info("Cliente Supabase inicializado com sucesso.")
            self._verify_table_connection()
        except Exception as e:
            logging.error(f"Falha ao inicializar o cliente Supabase: {e}")
            raise

    def _verify_table_connection(self) -> None:
        """
        Verifica se a conexão com a tabela 'conversation_history' é possível.
        Lança uma exceção em caso de falha.
        """
        try:
            self.client.table("conversation_history").select("session_id").limit(1).execute()
            logging.info("Conexão com a tabela 'conversation_history' verificada com sucesso.")
        except APIError as e:
            logging.error(f"Erro ao acessar a tabela 'conversation_history': {e.message}")
            logging.error("Verifique se a tabela existe e se as permissões (RLS) estão corretas.")
            raise

    def save_history(self, session_id: str, history: List[Dict[str, Any]]) -> None:
        """Salva ou atualiza o histórico de uma conversa no Supabase."""
        try:
            self.client.table("conversation_history").upsert(
                {"session_id": session_id, "history": history}
            ).execute()
            logging.info(f"Histórico da sessão '{session_id}' salvo com sucesso.")
        except APIError as e:
            logging.error(f"Erro ao salvar o histórico da sessão '{session_id}': {e.message}")

    def load_history(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Carrega o histórico de uma conversa do Supabase.
        Retorna uma lista vazia se não houver histórico.
        """
        try:
            resp = (
                self.client.table("conversation_history")
                .select("history")
                .eq("session_id", session_id)
                .execute()
            )
            # Verifica se a lista 'data' não está vazia antes de acessar o índice 0
            if resp.data:
                logging.info(f"Histórico da sessão '{session_id}' carregado com sucesso.")
                return resp.data[0].get("history", [])
            
            logging.info(f"Nenhum histórico encontrado para a sessão '{session_id}'.")
            return []
        except APIError as e:
            logging.error(f"Erro ao carregar o histórico da sessão '{session_id}': {e.message}")
            return []

def main():
    """Função principal para demonstrar o uso do SessionManager."""
    logging.info("Iniciando o Gerenciador de Sessão com Supabase.")
    
    try:
        # As credenciais são carregadas de variáveis de ambiente
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        
        manager = SessionManager(url=supabase_url, key=supabase_key)
        
        # Exemplo de uso
        session_id_exemplo = "user_12345_refactored"
        conversa_exemplo = [
            {"role": "user", "content": "Olá, qual a projeção do PIB para este ano?"},
            {"role": "assistant", "content": "A projeção do PIB é de 2.5%."},
        ]
        
        manager.save_history(session_id_exemplo, conversa_exemplo)
        
        historico_carregado = manager.load_history(session_id_exemplo)
        
        if historico_carregado:
            print("\n--- Histórico Carregado ---")
            for message in historico_carregado:
                print(f"{message['role']}: {message['content']}")
            print("---------------------------\n")
            
    except ValueError as e:
        logging.error(e)
    except Exception as e:
        logging.error(f"Um erro inesperado ocorreu durante a execução: {e}")

if __name__ == "__main__":
    main()