# 2_postgresql_session_management.py

import os
import psycopg2
import json
from psycopg2 import sql

# --- Configuração da Conexão com PostgreSQL ---
# As credenciais devem ser carregadas de variáveis de ambiente para segurança.
# Exemplo de DATABASE_URL: "postgresql://user:password@host:port/dbname"
DATABASE_URL = os.getenv('DATABASE_URL')

def get_db_connection():
    """Estabelece e retorna uma conexão com o banco de dados PostgreSQL."""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except psycopg2.OperationalError as e:
        print(f"Erro ao conectar ao PostgreSQL: {e}")
        # Em uma aplicação real, você poderia ter um tratamento de erro mais robusto,
        # como tentativas de reconexão ou logging.
        raise

def setup_database():
    """
    Cria a tabela para armazenar o histórico de conversas, se ela não existir.
    Esta função deve ser executada uma vez na inicialização da aplicação.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # A tabela armazena um ID de sessão e o histórico da conversa como JSONB
            cur.execute("""
                CREATE TABLE IF NOT EXISTS conversation_history (
                    session_id VARCHAR(255) PRIMARY KEY,
                    history JSONB NOT NULL,
                    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.commit()
            print("Tabela 'conversation_history' verificada/criada com sucesso.")
    finally:
        conn.close()

def save_conversation_history(session_id: str, history: list):
    """
    Salva ou atualiza o histórico de uma conversa no banco de dados.
    Utiliza 'ON CONFLICT' para simplificar a lógica de inserção/atualização (UPSERT).
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Converte a lista de mensagens para uma string JSON
            history_json = json.dumps(history)

            # SQL para inserir ou atualizar o registro
            query = sql.SQL("""
                INSERT INTO conversation_history (session_id, history)
                VALUES (%s, %s)
                ON CONFLICT (session_id) DO UPDATE SET
                    history = EXCLUDED.history,
                    last_updated = CURRENT_TIMESTAMP;
            """)
            cur.execute(query, (session_id, history_json))
            conn.commit()
            print(f"Histórico da sessão '{session_id}' salvo com sucesso.")
    except Exception as e:
        print(f"Erro ao salvar o histórico da sessão '{session_id}': {e}")
        conn.rollback() # Desfaz a transação em caso de erro
    finally:
        conn.close()

def load_conversation_history(session_id: str) -> list:
    """
    Carrega o histórico de uma conversa do banco de dados.
    Retorna uma lista vazia se a sessão não for encontrada.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            query = sql.SQL("SELECT history FROM conversation_history WHERE session_id = %s;")
            cur.execute(query, (session_id,))
            result = cur.fetchone()

            if result:
                print(f"Histórico da sessão '{session_id}' carregado com sucesso.")
                # O resultado (result[0]) já é um dict/list se o tipo da coluna for JSONB
                return result[0]
            else:
                print(f"Nenhum histórico encontrado para a sessão '{session_id}'.")
                return []
    except Exception as e:
        print(f"Erro ao carregar o histórico da sessão '{session_id}': {e}")
        return []
    finally:
        conn.close()

# --- Exemplo de Uso ---
if __name__ == '__main__':
    print("Gerenciador de Sessão com PostgreSQL.")
    # É necessário ter um servidor PostgreSQL rodando e a variável DATABASE_URL configurada.
    # Ex: export DATABASE_URL="postgresql://postgres:mysecretpassword@localhost:5432/agent_db"

    if not DATABASE_URL:
        print("\nA variável de ambiente DATABASE_URL não está configurada.")
        print("Por favor, configure-a para testar a conexão. Ex:")
        print("export DATABASE_URL=\"postgresql://user:password@host:port/dbname\"")
    else:
        # 1. Garante que a tabela existe
        setup_database()

        # 2. Simula uma conversa e salva
        session_id_exemplo = "user_12345"
        conversa_exemplo = [
            {"role": "user", "content": "Olá, qual a projeção do PIB para este ano?"},
            {"role": "assistant", "content": "Consultando os dados mais recentes... A projeção do PIB é de 2.5%."}
        ]
        save_conversation_history(session_id_exemplo, conversa_exemplo)

        # 3. Carrega a conversa do banco
        historico_carregado = load_conversation_history(session_id_exemplo)

        if historico_carregado:
            print("\n--- Histórico Carregado ---")
            for message in historico_carregado:
                print(f"{message['role']}: {message['content']}")
            print("---------------------------\n")

        # 4. Simula uma continuação da conversa
        historico_carregado.append(
            {"role": "user", "content": "E a inflação?"}
        )
        save_conversation_history(session_id_exemplo, historico_carregado)

        historico_atualizado = load_conversation_history(session_id_exemplo)
        if historico_atualizado:
            print("\n--- Histórico Atualizado ---")
            for message in historico_atualizado:
                print(f"{message['role']}: {message['content']}")
            print("----------------------------\n")
