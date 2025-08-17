"""Configuração do agente de análise de investimentos usando LangChain."""

import os
from typing import Optional

from langchain_openai import ChatOpenAI
from langchain.agents import AgentType, Tool, initialize_agent
from langchain.memory import ConversationBufferMemory
from langchain.tools import tool

from supabase_rag_integration import retrieve_relevant_documents
from internet_search import internet_search
from alpha_vantage_tool import alpha_vantage_stock_price


@tool("supabase_rag")
def supabase_rag(query: str) -> str:
    """Busca informações em documentos armazenados no Supabase."""
    results = retrieve_relevant_documents(query)
    if not results:
        return "Nenhuma informação relevante encontrada."
    return "\n\n".join(r["content"] for r in results)


llm = ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"), temperature=0)

TOOLS = [
    Tool(
        name="Busca RAG Supabase",
        func=supabase_rag,
        description=(
            "Use para consultar informações de relatórios Focus e COPOM armazenados no Supabase."
        ),
    ),
    Tool(
        name="Busca na Internet",
        func=internet_search,
        description="Obtém notícias e dados atualizados da internet.",
    ),
    alpha_vantage_stock_price,
]


def create_agent(memory: Optional[ConversationBufferMemory] = None):
    """Inicializa e retorna o agente com as ferramentas configuradas."""
    return initialize_agent(
        tools=TOOLS,
        llm=llm,
        agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True,
        handle_parsing_errors=True,
        memory=memory,
    )


if __name__ == "__main__":
    agent = create_agent()
    print("Agente de Análise de Investimentos pronto.")
