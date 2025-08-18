"""Ferramenta para consultar preços de ações via Alpha Vantage."""

import os
from typing import Any

import requests
from langchain.tools import tool

# A variável de ambiente pode ser definida como ALPHA_VANTAGE ou ALPHA_VANTAGE_API_KEY
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE") or os.getenv("ALPHA_VANTAGE_API_KEY")


@tool
def alpha_vantage_stock_price(symbol: str) -> str:
    """Retorna o preço atual de uma ação usando a API Alpha Vantage.

    O símbolo deve incluir o sufixo do mercado quando necessário (ex: 'BBAS3.SA').
    """
    if not ALPHA_VANTAGE_API_KEY:
        return "Chave da API Alpha Vantage não configurada."

    url = "https://www.alphavantage.co/query"
    params = {
        "function": "GLOBAL_QUOTE",
        "symbol": symbol,
        "apikey": ALPHA_VANTAGE_API_KEY,
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data: Any = resp.json().get("Global Quote", {})
        price = data.get("05. price")
        if price:
            change = data.get("09. change", "N/A")
            percent = data.get("10. change percent", "N/A")
            return f"Preço: {price} USD\nVariação: {change} ({percent})"
        return f"Resposta inesperada: {data}"
    except Exception as exc:  # noqa: BLE001
        return f"Erro ao consultar Alpha Vantage: {exc}"
