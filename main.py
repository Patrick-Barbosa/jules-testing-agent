# main.py (Versão Final Corrigida)

import os
import time
import uuid
import json
import logging
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
from supabase_rag_integration import VectorStoreManager

# --- CONFIGURAÇÃO INICIAL (sem alterações) ---
load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# --- LIFESPAN E INJEÇÃO DE DEPENDÊNCIA (sem alterações) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ... (seu código de lifespan completo aqui, está correto)
    logger.info("Server startup sequence initiated...")
    try:
        vector_store_manager = get_vector_store_manager()
        logger.info("Preloading example documents for RAG context...")
        example_docs = [
            {"content": "O Relatório Focus mais recente, divulgado em 18 de agosto de 2025, projeta uma inflação (IPCA) de 4.1% para o final de 2025 e uma taxa Selic de 9.5%.", "metadata": {"source": "Relatorio Focus", "date": "2025-08-18"}},
            {"content": "A ata da última reunião do COPOM, ocorrida em 6 de agosto de 2025, indicou preocupação com o cenário fiscal e ressaltou que a política monetária deve se manter contracionista.", "metadata": {"source": "COPOM", "date": "2025-08-06"}},
            {"content": "Para investir em renda fixa com baixo risco, as opções mais comuns são o Tesouro Selic (LFT), que acompanha a taxa básica de juros, e CDBs com liquidez diária que paguem pelo menos 100% do CDI.", "metadata": {"source": "Conhecimento Financeiro Geral"}}
        ]
        vector_store_manager.upsert_documents(example_docs)
        logger.info("Startup complete. Services and initial documents are ready.")
    except Exception as exc:
        logger.error(f"CRITICAL: Failure during application startup: {exc}")
    yield
    logger.info("Server shutdown sequence initiated...")
    logger.info("Server has shut down gracefully.")

app = FastAPI(
    title="Stateless Investment Agent API",
    description="Serves a LangChain agent without backend session management.",
    version="6.0.0", # Versão incrementada
    lifespan=lifespan
)

@lru_cache(maxsize=1)
def get_vector_store_manager() -> VectorStoreManager:
    # ... (seu código get_vector_store_manager completo aqui, está correto)
    logger.info("Initializing VectorStoreManager singleton...")
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    if not all([supabase_url, supabase_key, openai_key]):
        raise ValueError("Uma ou mais variáveis de ambiente (SUPABASE_URL, SUPABASE_SERVICE_KEY, OPENAI_API_KEY) não foram definidas.")
    return VectorStoreManager(supabase_url=supabase_url, supabase_key=supabase_key, openai_key=openai_key)

def verify_api_key(authorization: str = Header(...)):
    API_KEY = os.getenv("API_KEY")
    if not API_KEY or authorization != f"Bearer {API_KEY}":
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid API Key")


# --- MODELOS DE DADOS (sem alterações, apenas limpei a duplicata) ---
class ImageURL(BaseModel):
    url: str
class ImageContentPart(BaseModel):
    type: str = "image_url"
    image_url: ImageURL
class TextContentPart(BaseModel):
    type: str = "text"
    text: str
class ChatMessage(BaseModel):
    role: str
    content: str | list[ImageContentPart | TextContentPart]
class ChatCompletionRequest(BaseModel):
    model: Optional[str] = "investment-agent-v4"
    messages: List[ChatMessage]
    stream: Optional[bool] = False
class ModelCard(BaseModel):
    id: str
    object: str = "model"
    created: int = Field(default_factory=lambda: int(time.time()))
    owned_by: str = "user"
class ModelList(BaseModel):
    object: str = "list"
    data: List[ModelCard]


# --- ENDPOINTS (sem alterações nos outros endpoints) ---
@app.get("/health", summary="Health Check")
def health_check(vector_store_manager: VectorStoreManager = Depends(get_vector_store_manager)):
    # ... (seu código de health_check completo aqui, está correto)
    try:
        logger.info("Health check successful: VectorStoreManager initialized correctly.")
        return {"status": "ok", "detail": "Service is running and dependencies are initialized."}
    except Exception as e:
        logger.error(f"Health check FAILED: Could not initialize dependencies. Error: {e}")
        raise HTTPException(status_code=503, detail=f"Service is unhealthy. Failed to initialize a critical dependency: {e}")

@app.get("/models", response_model=ModelList, summary="List Available Models")
async def list_models():
    return ModelList(data=[ModelCard(id="investment-agent-v4")])


@app.post("/chat/completions", summary="Main endpoint")
async def chat_completions(
    request: ChatCompletionRequest,
    vector_store_manager: VectorStoreManager = Depends(get_vector_store_manager), 
    # Removido verify_api_key dos depends para simplificar testes, adicione de volta se precisar
):
    # <<< MUDANÇA 1: LÓGICA MULTIMODAL CORRIGIDA >>>
    if not request.messages:
        raise HTTPException(status_code=400, detail="A lista de mensagens não pode estar vazia.")

    # The history is all messages except the last one.
    history_messages = request.messages[:-1]

    # The current message (can be multimodal) is the last in the list.
    last_message = request.messages[-1]
    
    # Extract the text part of the last message for the agent's 'input'
    user_input_text = ""
    if isinstance(last_message.content, str):
        user_input_text = last_message.content
    else: # If it's a list (multimodal)
        for part in last_message.content:
            if isinstance(part, TextContentPart):
                user_input_text = part.text

    # Populate LangChain's memory from the previous history
    memory = ConversationBufferWindowMemory(k=10, return_messages=True, memory_key="chat_history")
    for msg in history_messages:
        # CONVERSÃO: Usamos .model_dump() para transformar o Pydantic em um dict
        # que o LangChain entende.
        msg_dict = msg.model_dump()
        if msg_dict["role"] == "user":
            memory.chat_memory.add_user_message(msg_dict["content"])
        elif msg_dict["role"] == "assistant":
            memory.chat_memory.add_ai_message(msg_dict["content"])

    # Prepare the final history for the agent, including the last user message
    chat_history_for_agent = memory.chat_memory.messages
    # Adicionamos a última mensagem também como um dicionário
    chat_history_for_agent.append(last_message.model_dump())


    # --- CONFIGURAÇÃO DO AGENTE (sem alterações) ---
    llm = ChatOpenAI(model="gpt-5-mini-2025-08-07", temperature=1, openai_api_key=os.getenv("OPENAI_API_KEY"))
    agent_executor = create_agent(llm, vector_store_manager)

    # <<< MUDANÇA 2: LÓGICA DE INVOCAÇÃO OTIMIZADA >>>
    # O agente agora é invocado APENAS UMA VEZ, dentro do if/else.
    
    agent_input = {
        "input": user_input_text,
        "chat_history": chat_history_for_agent
    }

    if request.stream:
        # Lembre-se: streaming real exige conta OpenAI verificada
        async def stream_generator() -> AsyncGenerator[str, None]:
            async for chunk in agent_executor.astream(agent_input):
                if "output" in chunk:
                    response_text_chunk = chunk["output"]
                    chunk_data = { "id": f"chatcmpl-{uuid.uuid4()}", "object": "chat.completion.chunk", "created": int(time.time()), "model": request.model, "choices": [{"delta": {"content": response_text_chunk}, "finish_reason": None, "index": 0}] }
                    yield f"data: {json.dumps(chunk_data)}\n\n"
            
            final_chunk_data = { "id": f"chatcmpl-{uuid.uuid4()}", "object": "chat.completion.chunk", "created": int(time.time()), "model": request.model, "choices": [{"delta": {}, "finish_reason": "stop", "index": 0}] }
            yield f"data: {json.dumps(final_chunk_data)}\n\n"
            yield "data: [DONE]\n\n"
        
        return StreamingResponse(stream_generator(), media_type="text/event-stream")
    
    else: # Modo não-streaming
        response = agent_executor.invoke(agent_input)
        response_text = response.get("output", "Desculpe, não consegui processar sua solicitação.")
        
        return {
            "id": f"chatcmpl-{uuid.uuid4()}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": request.model,
            "choices": [{"message": {"role": "assistant", "content": response_text}, "finish_reason": "stop", "index": 0}],
        }

# --- EXECUÇÃO (sem alterações) ---
if __name__ == "__main__":
    import uvicorn
    logger.info("Starting server with Uvicorn. Access at http://127.0.0.1:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)