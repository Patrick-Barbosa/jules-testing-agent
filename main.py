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
from fastapi.testclient import TestClient

from langchain.memory import ConversationBufferMemory

from langchain_agent import create_agent
from postgresql_session_management import (
    load_conversation_history,
    save_conversation_history,
    setup_database,
)
from supabase_rag_integration import preload_example_documents

# Carrega variáveis de ambiente
load_dotenv()
API_KEY = os.getenv("API_KEY")

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Investment Agent API")


@app.on_event("startup")
def startup_event() -> None:
    """Configurações executadas ao iniciar o servidor."""
    try:
        setup_database()
        preload_example_documents()
        logger.info("Serviços inicializados.")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Falha na inicialização: %s", exc)


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: Optional[str] = "gpt-4o-mini"
    messages: List[ChatMessage]
    stream: Optional[bool] = False
    session_id: Optional[str] = None


def verify_api_key(authorization: str = Header(None)) -> None:
    if API_KEY is None or authorization != f"Bearer {API_KEY}":
        raise HTTPException(status_code=401, detail="Unauthorized")


@app.get("/health")
def health_check() -> dict:
    return {"status": "ok"}


@app.post("/v1/chat/completions")
def chat_completions(
    request: ChatCompletionRequest,
    _: None = Depends(verify_api_key),
):
    session_id = request.session_id or str(uuid.uuid4())
    history = load_conversation_history(session_id)

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
    except Exception as exc:  # noqa: BLE001
        logger.exception("Erro ao executar o agente")
        raise HTTPException(status_code=500, detail=str(exc))

    history.append({"role": "user", "content": user_message})
    history.append({"role": "assistant", "content": response_text})
    save_conversation_history(session_id, history)

    model_name = request.model or "gpt-4o-mini"

    if request.stream:
        async def event_stream():
            chunk = {
                "id": str(uuid.uuid4()),
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": model_name,
                "choices": [
                    {
                        "delta": {"content": response_text},
                        "index": 0,
                        "finish_reason": "stop",
                    }
                ],
            }
            yield f"data: {json.dumps(chunk)}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(event_stream(), media_type="text/event-stream")

    return {
        "id": str(uuid.uuid4()),
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model_name,
        "choices": [
            {
                "message": {"role": "assistant", "content": response_text},
                "finish_reason": "stop",
                "index": 0,
            }
        ],
        "session_id": session_id,
    }


def run_tests() -> None:
    """Executa testes básicos do endpoint e das integrações."""
    if API_KEY is None:
        logger.warning("API_KEY não definida; testes da API serão pulados.")
        return

    client = TestClient(app)
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "user", "content": "Qual é o preço atual da ação BBAS3?"}
        ],
    }
    headers = {"Authorization": f"Bearer {API_KEY}"}
    resp = client.post("/v1/chat/completions", json=payload, headers=headers)
    logger.info("Resultado do teste /v1/chat/completions: %s", resp.json())

    if os.getenv("ALPHA_VANTAGE") or os.getenv("ALPHA_VANTAGE_API_KEY"):
        content = resp.json()["choices"][0]["message"]["content"]
        assert "Preço" in content, "Resposta não contém dados de preço."
    else:
        logger.warning(
            "ALPHA_VANTAGE/ALPHA_VANTAGE_API_KEY não configurada; não foi possível validar preço."
        )


    from supabase_rag_integration import retrieve_relevant_documents

    docs = retrieve_relevant_documents("inflação")
    logger.info("Resultado da busca RAG: %s", docs)


if __name__ == "__main__":
    run_tests()
    # Para rodar o servidor, utilize:
    # import uvicorn
    # uvicorn.run("main:app", host="0.0.0.0", port=8000)
