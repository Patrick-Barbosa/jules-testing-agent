"""Configuração do agente de análise de investimentos usando LangChain."""

import os
from typing import Optional

from langchain_openai import ChatOpenAI
from langchain.agents import AgentType, Tool, initialize_agent
from langchain.memory import ConversationBufferMemory

# We now import the VectorStoreManager class
from supabase_rag_integration import VectorStoreManager
from internet_search import internet_search
from alpha_vantage_tool import alpha_vantage_stock_price
from report_focus import buscar_serie_temporal_expectativas_focus


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
            func=supabase_rag_retriever,
            description=(
                "Não use por enquanto pois o banco vetorial não contém absolutamente nada"
            ),
        ),
        Tool(
            name="Busca na Internet",
            func=internet_search,
            description="Obtém notícias e dados atualizados da internet em tempo real.",
        ),
        Tool(
            name="Expectativas Focus",
            func=buscar_serie_temporal_expectativas_focus,
            description=(
                "Busca a série temporal de expectativas do relatório Focus do Banco Central."
            ),
        ),
        Tool(
            name="Preço de Ações Alpha Vantage",
            func=alpha_vantage_stock_price,
            description=(
                "Obtém o preço atual de ações usando a API Alpha Vantage."
                "Use o símbolo da ação como parâmetro."
            ),
        )
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
    # The agent is now created and run from your main.py file.
    print("O agente agora é criado e executado a partir do arquivo principal (main.py).")