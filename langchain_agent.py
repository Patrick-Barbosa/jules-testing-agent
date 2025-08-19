# langchain_agent.py (Versão Final com Agente de Ferramentas)

import os
from typing import List

from langchain import hub
from langchain_openai import ChatOpenAI
# <<< MUDANÇA 1: Importamos o construtor de agente correto >>>
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.tools import tool

from supabase_rag_integration import VectorStoreManager
from internet_search import internet_search
from alpha_vantage_tool import alpha_vantage_stock_price
from report_focus import buscar_serie_temporal_expectativas_focus

# --- FERRAMENTAS (sem alteração) ---

@tool
def busca_na_internet(query: str) -> str:
    """Obtém notícias e dados atualizados da internet em tempo real. Use para eventos recentes ou informações não encontradas em outras ferramentas."""
    return internet_search(query)

@tool
def obter_expectativas_focus(indicador: str) -> str:
    """Busca a série temporal de expectativas para um indicador econômico específico (ex: 'IPCA', 'Selic', 'PIB') no relatório Focus do Banco Central."""
    return buscar_serie_temporal_expectativas_focus(indicador)

@tool
def obter_preco_de_acao(symbol: str) -> str:
    """Obtém o preço atual de uma ação específica usando seu símbolo (ticker). Exemplo de símbolo: 'PETR4', 'MGLU3'."""
    return alpha_vantage_stock_price(symbol)


# --- FUNÇÃO PRINCIPAL PARA CRIAR O AGENTE ---

def create_agent(llm: ChatOpenAI, vector_store_manager: VectorStoreManager):
    """
    Cria e retorna um AgentExecutor moderno usando o padrão OpenAI Tools.
    """
    
    @tool
    def busca_documentos_internos(query: str) -> str:
        """Busca informações em relatórios e documentos internos sobre o mercado financeiro. Use para perguntas sobre dados históricos e análises já consolidadas."""
        results = vector_store_manager.retrieve_relevant_documents(query)
        if not results:
            return "Nenhuma informação relevante encontrada nos documentos internos."
        return "\n\n".join(r["content"] for r in results)

    all_tools: List = [
        busca_na_internet,
        obter_expectativas_focus,
        obter_preco_de_acao,
        busca_documentos_internos,
    ]

    # <<< MUDANÇA 2: Puxamos o prompt correto para agentes de ferramentas >>>
    # Este prompt é otimizado para o fluxo de "tool calling".
    prompt = hub.pull("hwchase17/openai-tools-agent")
    
    # Adicionamos sua mensagem de sistema ao prompt. A estrutura é um pouco diferente.
    # O prompt baixado já contém a mensagem de sistema, então nós a editamos.
    prompt.messages[0].prompt.template = "Você é um assistente especialista em análise de investimentos. Seja conciso e preciso. Responda sempre em português do Brasil."

    # <<< MUDANÇA 3: Usamos o construtor de agente correto >>>
    agent = create_openai_tools_agent(llm, all_tools, prompt)

    # Executor do Agente (sem alteração na sua chamada)
    agent_executor = AgentExecutor(
        agent=agent,
        tools=all_tools,
        verbose=True,
        handle_parsing_errors=True,
    )
    
    return agent_executor