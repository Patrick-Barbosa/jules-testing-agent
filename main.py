# 🚨 AVISO DE SEGURANÇA 🚨
# NUNCA exponha suas chaves de API ou credenciais em código público ou versionado.
# 1. Utilize sempre um arquivo .env para armazenar suas credenciais.
# 2. Adicione o arquivo .env ao seu .gitignore para evitar o commit acidental.
# 3. Se você expôs uma chave, regenere-a IMEDIATAMENTE no painel do provedor (Supabase, OpenAI, etc.).
# 4. Para o Supabase, use a chave 'anon key' para operações do lado do cliente e mantenha a 'service_role key' estritamente no backend seguro.

"""API FastAPI que expõe o agente de análise de investimentos em formato compatível com OpenAI."""

import os
import time
import uuid
import json
import logging
from typing import List, Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv

from langchain.memory import ConversationBufferMemory
from langchain_agent import create_agent

# Importa as classes que refatoramos anteriormente
from postgresql_session_management import SessionManager
from supabase_rag_integration import VectorStoreManager

# Carrega variáveis de ambiente
load_dotenv()

# --- CONFIGURAÇÃO ---
API_KEY = os.getenv("API_KEY")
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
app = FastAPI(title="Investment Agent API")

# Cria instâncias globais dos nossos managers para serem usadas pela API
try:
    session_manager = SessionManager(
        url=os.getenv("SUPABASE_URL"),
        key=os.getenv("SUPABASE_SERVICE_KEY")
    )
    vector_store_manager = VectorStoreManager(
        supabase_url=os.getenv("SUPABASE_URL"),
        supabase_key=os.getenv("SUPABASE_SERVICE_KEY"),
        openai_key=os.getenv("OPENAI_API_KEY")
    )
except ValueError as e:
    logger.error(f"CRITICAL: Failed to initialize managers due to missing environment variables: {e}")
    session_manager = None
    vector_store_manager = None

@app.on_event("startup")
def startup_event() -> None:
    """Configurações executadas ao iniciar o servidor."""
    if vector_store_manager:
        try:
            logger.info("Preloading example documents...")
            example_docs = [
                {"content": "Relatório Focus projeta inflação de 3.9% para 2024.", "metadata": {"source": "Focus"}},
                {"content": "Ata do COPOM registra manutenção da taxa Selic em 13.75%.", "metadata": {"source": "COPOM"}},
            ]
            vector_store_manager.upsert_documents(example_docs)
            logger.info("Services initialized successfully.")
        except Exception as exc:
            logger.warning("Failure during startup document loading: %s", exc)
    else:
        logger.warning("Vector Store Manager not initialized. Skipping startup tasks.")


class ChatMessage(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: Optional[str] = "gpt-4o-mini"
    messages: List[ChatMessage]
    stream: Optional[bool] = False
    session_id: Optional[str] = None

def verify_api_key(authorization: str = Header(None)) -> None:
    if not API_KEY or authorization != f"Bearer {API_KEY}":
        raise HTTPException(status_code=401, detail="Unauthorized")

@app.get("/health")
def health_check() -> dict:
    if session_manager and vector_store_manager:
        return {"status": "ok"}
    return {"status": "error", "details": "One or more managers failed to initialize."}

@app.post("/v1/chat/completions")
def chat_completions(
    request: ChatCompletionRequest,
    _: None = Depends(verify_api_key),
):
    if not session_manager:
        raise HTTPException(status_code=503, detail="Session manager not available.")

    session_id = request.session_id or str(uuid.uuid4())
    history = session_manager.load_history(session_id)

    memory = ConversationBufferMemory(return_messages=True)
    for message in history:
        if message["role"] == "user":
            memory.chat_memory.add_user_message(message["content"])
        else:
            memory.chat_memory.add_ai_message(message["content"])

    agent = create_agent(memory)
    user_message = request.messages[-1].content

    try:
        response_text = agent.run(user_message)
    except Exception as exc:
        logger.exception("Error executing agent")
        raise HTTPException(status_code=500, detail=str(exc))

    history.append({"role": "user", "content": user_message})
    history.append({"role": "assistant", "content": response_text})
    session_manager.save_history(session_id, history)

    model_name = request.model or "gpt-4o-mini"
    
    if request.stream:
        async def event_stream():
            chunk = {
                "id": str(uuid.uuid4()), "object": "chat.completion.chunk", "created": int(time.time()),
                "model": model_name,
                "choices": [{"delta": {"content": response_text}, "index": 0, "finish_reason": "stop"}],
            }
            yield f"data: {json.dumps(chunk)}\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(event_stream(), media_type="text/event-stream")

    return {
        "id": str(uuid.uuid4()), "object": "chat.completion", "created": int(time.time()),
        "model": model_name,
        "choices": [{"message": {"role": "assistant", "content": response_text}, "finish_reason": "stop", "index": 0}],
        "session_id": session_id,
    }

if __name__ == "__main__":
    # Para rodar o servidor, utilize o comando no terminal:
    # uvicorn main:app --reload
    logger.info("To start the server, run: uvicorn <filename>:app --reload")