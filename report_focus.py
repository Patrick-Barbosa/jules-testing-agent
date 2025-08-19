import requests
from datetime import datetime, timedelta
from cachetools import cached, TTLCache
from langchain.agents import tool

# Criamos um cache de 5 horas que será usado pela ferramenta
five_hour_cache = TTLCache(maxsize=100, ttl=18000)

@tool
@cached(cache=five_hour_cache)
def buscar_serie_temporal_expectativas_focus(indicador: str) -> dict:
    """
    Ferramenta para buscar a série temporal de expectativas de mercado do Relatório Focus do Banco Central do Brasil.
    Use-a para obter a evolução histórica recente e as projeções futuras para indicadores econômicos brasileiros.
    O input deve ser uma string com o nome do indicador. Exemplos: 'IPCA', 'Selic', 'PIB', 'Câmbio'.
    A função retorna um dicionário JSON com os dados.
    """
    print(f"--- [LOG DA FERRAMENTA] FAZENDO CHAMADA REAL NA API PARA: {indicador} ---")
    
    # --- 1. Buscar a Evolução Histórica (últimos 12 meses) ---
    data_inicio_historico = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    url_historico = (
        f"https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/"
        f"ExpectativasMercadoAnuais?$top=200"
        f"&$filter=Indicador%20eq%20'{indicador}'%20and%20Data%20ge%20'{data_inicio_historico}'"
        f"&$orderby=Data%20asc"
        f"&$format=json"
    )
    historico_evolucao = []
    try:
        response = requests.get(url_historico, timeout=15)
        response.raise_for_status()
        dados = response.json().get('value', [])
        for projecao in dados:
            historico_evolucao.append({
                "data_previsao": projecao['Data'],
                "ano_referencia": projecao['DataReferencia'],
                "media": projecao['Media']
            })
    except requests.exceptions.RequestException as e:
        return {"erro": f"Erro ao buscar histórico da API: {e}"}

    # --- 2. Buscar Projeções para os Próximos 5 Anos ---
    url_futuro = (
        f"https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/"
        f"ExpectativasMercadoAnuais?$top=5"
        f"&$filter=Indicador%20eq%20'{indicador}'"
        f"&$orderby=Data%20desc,DataReferencia%20asc"
        f"&$format=json"
    )
    projecoes_futuras = []
    try:
        response = requests.get(url_futuro, timeout=15)
        response.raise_for_status()
        dados = response.json().get('value', [])
        if dados:
            data_recente = dados[0]['Data']
            projecoes_recentes = [p for p in dados if p['Data'] == data_recente]
            for projecao in projecoes_recentes:
                 projecoes_futuras.append({
                    "ano_projecao": projecao['DataReferencia'],
                    "media": projecao['Media'],
                    "mediana": projecao['Mediana'],
                    "desvio_padrao": projecao['DesvioPadrao']
                })
    except requests.exceptions.RequestException as e:
        return {"erro": f"Erro ao buscar projeções futuras da API: {e}"}

    if not historico_evolucao and not projecoes_futuras:
        return {"erro": f"Nenhum dado encontrado para o indicador '{indicador}'."}

    return {
        "indicador": indicador,
        "resumo": f"Análise temporal para {indicador} coletada em {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "evolucao_recente_12m": historico_evolucao,
        "projecoes_proximos_anos": projecoes_futuras
    }
