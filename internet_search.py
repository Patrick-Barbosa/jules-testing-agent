"""Ferramenta de busca na internet utilizando a API Tavily."""

import os
from langchain_community.tools.tavily_search import TavilySearchResults

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")


def internet_search(query: str) -> str:
    """Executa uma busca real na internet via Tavily."""
    if not TAVILY_API_KEY:
        return "Chave de API do Tavily não configurada."

    try:
        search_tool = TavilySearchResults(k=3)
        results = search_tool.invoke({"query": query})
        if isinstance(results, dict) and "results" in results:
            formatted = "\n".join(
                f"Title: {r['title']}\nURL: {r['url']}\nSnippet: {r['snippet']}\n"
                for r in results["results"]
            )
            return formatted
        return str(results)
    except Exception as exc:
        return f"Erro na busca: {exc}"


if __name__ == "__main__":
    print("Ferramenta de Busca na Internet.")
    consulta = "cotação atual do dólar"
    print(internet_search(consulta))
