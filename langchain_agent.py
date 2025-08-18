"""Configuração do agente de análise de investimentos usando LangChain."""

import os
from typing import Optional

from langchain_openai import ChatOpenAI
from langchain.agents import AgentType, Tool, initialize_agent
from langchain.memory import ConversationBufferMemory

# --- MODIFIED IMPORTS ---
# We now import the VectorStoreManager class
from supabase_rag_integration import VectorStoreManager
from internet_search import internet_search
from alpha_vantage_tool import alpha_vantage_stock_price

# --- MODIFIED FUNCTION ---
# The function now accepts the vector_store_manager as a required argument.
def create_agent(
    memory: ConversationBufferMemory, vector_store_manager: VectorStoreManager
):
    """Inicializa e retorna o agente com as ferramentas configuradas."""

    # This helper function uses the manager instance that is passed into create_agent
    def supabase_rag_retriever(query: str) -> str:
        """Busca informações em documentos e formata a saída para o agente."""
        results = vector_store_manager.retrieve_relevant_documents(query)
        if not results:
            return "Nenhuma informação relevante encontrada nos documentos internos."
        # Formats the list of documents into a single string for the agent
        return "\n\n".join(r["content"] for r in results)

    # The LLM and Tools are now defined inside the function. This is better because
    # the tool's definition depends on the vector_store_manager.
    llm = ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"), temperature=0)

    tools = [
        Tool(
            name="Busca RAG Supabase",
            func=supabase_rag_retriever, # Uses our new helper function
            description=(
                "Use para consultar informações de relatórios Focus e COPOM armazenados internamente."
            ),
        ),
        Tool(
            name="Busca na Internet",
            func=internet_search,
            description="Obtém notícias e dados atualizados da internet em tempo real.",
        ),
        alpha_vantage_stock_price,
    ]

    return initialize_agent(
        tools=tools,
        llm=llm,
        agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True,
        handle_parsing_errors=True,
        memory=memory,
    )


if __name__ == "__main__":
    # This block cannot be run directly anymore because it requires an instance
    # of VectorStoreManager and ConversationBufferMemory to be created first.
    # The agent is now created and run from your main.py file.
    print("O agente agora é criado e executado a partir do arquivo principal (main.py).")