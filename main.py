# main.py (A Versão Que Vai Funcionar)

import os
import time
import uuid
import json
import logging
import asyncio
from typing import List, Optional, AsyncGenerator
from functools import lru_cache
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferWindowMemory 

from langchain_agent import create_agent 
from postgresql_session_management import SessionManager
from supabase_rag_integration import VectorStoreManager

# --- CONFIGURAÇÃO INICIAL ---

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- GERENCIAMENTO DO CICLO DE VIDA DA APLICAÇÃO ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Server starting up...")
    vector_store_manager = get_vector_store_manager()
    try:
        logger.info("Preloading example documents for RAG context...")
        example_docs = [
            {"content": "Relatório Focus projeta inflação de 3.9% para 2024.", "metadata": {"source": "Focus"}},
            {"content": "Ata do COPOM registra manutenção da taxa Selic em 13.75%.", "metadata": {"source": "COPOM"}},
        ]
        vector_store_manager.upsert_documents(example_docs)
        logger.info("Services initialized successfully.")
    except Exception as exc:
        logger.error(f"CRITICAL: Failure during startup document loading: {exc}")
    yield
    logger.info("Server shutting down...")

app = FastAPI(
    title="Investment Agent API - The Final Version",
    description="Serves a LangChain agent compliant with the OpenAI Chat Completions protocol.",
    version="4.0.0",
    lifespan=lifespan
)

# --- INJEÇÃO DE DEPENDÊNCIA ---

@lru_cache(maxsize=1)
def get_session_manager() -> SessionManager:
    logger.info("Initializing SessionManager singleton...")
    return SessionManager(url=os.getenv("SUPABASE_URL"), key=os.getenv("SUPABASE_SERVICE_KEY"))

@lru_cache(maxsize=1)
def get_vector_store_manager() -> VectorStoreManager:
    logger.info("Initializing VectorStoreManager singleton...")
    return VectorStoreManager(
        supabase_url=os.getenv("SUPABASE_URL"),
        supabase_key=os.getenv("SUPABASE_SERVICE_KEY"),
        openai_key=os.getenv("OPENAI_API_KEY")
    )

API_KEY = os.getenv("API_KEY")
def verify_api_key(authorization: str = Header(..., description="Bearer Token for authorization")):
    if not API_KEY or authorization != f"Bearer {API_KEY}":
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid API Key")

# --- MODELOS DE DADOS (CONTRATO DA API) ---

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: Optional[str] = "investment-agent-v4"
    messages: List[ChatMessage]
    stream: Optional[bool] = False
    session_id: Optional[str] = Field(None, description="Unique identifier for the conversation session.")

class ModelCard(BaseModel):
    id: str
    object: str = "model"
    created: int = Field(default_factory=lambda: int(time.time()))
    owned_by: str = "user"

class ModelList(BaseModel):
    object: str = "list"
    data: List[ModelCard]

# --- ENDPOINTS DA API ---

@app.get("/health", summary="Health Check")
def health_check() -> dict:
    try:
        get_session_manager(); get_vector_store_manager()
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service Unavailable: One or more managers failed to initialize.")

@app.get("/models", response_model=ModelList, summary="List Available Models")
async def list_models():
    model_id = "investment-agent-v4"
    return ModelList(data=[ModelCard(id=model_id)])

@app.post(
    "/chat/completions", 
    summary="Main endpoint for agent interaction",
    dependencies=[Depends(verify_api_key)]
)
async def chat_completions(
    request: ChatCompletionRequest,
    session_manager: SessionManager = Depends(get_session_manager),
    vector_store_manager: VectorStoreManager = Depends(get_vector_store_manager) 
):
    # <<< A CORREÇÃO DEFINITIVA ESTÁ AQUI >>>
    # Forçamos o stream para False, não importa o que o cliente peça.
    # Isso garante que a chamada para a OpenAI nunca tentará o streaming.
    request.stream = False

    session_id = request.session_id or str(uuid.uuid4())
    user_message = request.messages[-1].content
    
    history = await asyncio.to_thread(session_manager.load_history, session_id)

    memory = ConversationBufferWindowMemory(k=10, return_messages=True, memory_key="chat_history")
    for msg in history:
        if msg["role"] == "user":
            memory.chat_memory.add_user_message(msg["content"])
        else:
            memory.chat_memory.add_ai_message(msg["content"])

    llm = ChatOpenAI(
        model="gpt-4o-mini", 
        temperature=0.4,
        openai_api_key=os.getenv("OPENAI_API_KEY"),
    )

    agent_executor = create_agent(llm, vector_store_manager)

    try:
        response = await asyncio.to_thread(
            agent_executor.invoke,
            {
                "input": user_message,
                "chat_history": memory.chat_memory.messages
            }
        )
        response_text = response.get("output", "Desculpe, não consegui processar sua solicitação.")

    except Exception as e:
        logger.exception("Error during agent execution.")
        raise HTTPException(status_code=500, detail=str(e))
    
    new_history = history + [
        {"role": "user", "content": user_message},
        {"role": "assistant", "content": response_text}
    ]
    await asyncio.to_thread(session_manager.save_history, session_id, new_history)

    # Agora este `if` nunca será verdadeiro, e o código sempre seguirá para o `else`.
    if request.stream:
        # Este bloco de código nunca será executado enquanto a correção estiver ativa.
        async def stream_generator() -> AsyncGenerator[str, None]:
            # ...
            yield "" # Placeholder
        
        return StreamingResponse(stream_generator(), media_type="text/event-stream")
    
    else:
        # O código sempre retornará por aqui, que é o modo não-streaming.
        return {
            "id": f"chatcmpl-{uuid.uuid4()}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": request.model,
            "choices": [{"message": {"role": "assistant", "content": response_text}, "finish_reason": "stop", "index": 0}],
            "session_id": session_id,
        }

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting server with Uvicorn. Access at http://127.0.0.1:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)