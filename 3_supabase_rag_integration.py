# 3_supabase_rag_integration.py

import os
from supabase import create_client, Client
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter

# --- Configuração do Cliente Supabase e Embeddings ---
# Credenciais devem ser carregadas de variáveis de ambiente.
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

# Placeholder para o modelo de embeddings. OpenAI é uma escolha comum,
# mas pode ser substituído por outros (ex: SentenceTransformers).
# Garanta que a variável de ambiente OPENAI_API_KEY esteja configurada.
# embeddings_model = OpenAIEmbeddings()

# Inicialização do cliente Supabase
# supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def preprocess_document(file_path: str) -> str:
    """
    Placeholder para a lógica de pré-processamento de documentos.
    Em um caso real, esta função lidaria com a extração de texto
    de diferentes formatos de arquivo, como PDF ou DOCX.

    Args:
        file_path (str): O caminho para o arquivo do relatório (ex: "Relatorio_Focus.pdf").

    Returns:
        str: O conteúdo de texto extraído do documento.
    """
    print(f"Pré-processando o documento em '{file_path}'...")
    # Lógica de extração de texto (ex: usando PyPDF2, python-docx) iria aqui.
    # Por enquanto, retornamos um texto de exemplo.
    if "Focus" in file_path:
        return """
        Relatório Focus - 15 de Agosto de 2025.
        O mercado financeiro projeta um crescimento do Produto Interno Bruto (PIB) de 2.1% para este ano.
        A projeção para a taxa Selic ao final do ano se mantém em 9.50%.
        A estimativa para o Índice Nacional de Preços ao Consumidor Amplo (IPCA) é de 4.8% em 2025.
        O dólar é esperado em R$ 5,05 no final do ano.
        """
    elif "COPOM" in file_path:
        return """
        Ata da 274ª Reunião do COPOM - 10 de Agosto de 2025.
        O Comitê de Política Monetária (COPOM) decidiu, por unanimidade, manter a taxa Selic em 10.50% a.a.
        O Comitê avalia que o cenário externo se mostra adverso, com incertezas sobre a política monetária nas economias centrais.
        No cenário doméstico, a atividade econômica segue resiliente, mas a inflação de serviços preocupa.
        O balanço de riscos para a inflação é simétrico, com fatores de alta e baixa.
        """
    return ""

def create_and_embed_chunks(text: str, source: str):
    """
    Divide o texto em pedaços (chunks), gera embeddings e os insere no Supabase.
    """
    if not supabase or not embeddings_model:
        print("Cliente Supabase ou modelo de embeddings não inicializado. Abortando.")
        return

    # 1. Dividir o texto em chunks menores
    # RecursiveCharacterTextSplitter é eficaz para manter a coesão do texto.
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,  # Tamanho de cada pedaço de texto
        chunk_overlap=50, # Sobreposição para não perder contexto entre chunks
        length_function=len
    )
    chunks = text_splitter.split_text(text)

    print(f"Texto dividido em {len(chunks)} chunks.")

    # 2. Gerar embeddings para cada chunk
    embeddings = embeddings_model.embed_documents(chunks)

    print(f"Gerados {len(embeddings)} vetores de embedding.")

    # 3. Preparar os dados para inserção
    # O Supabase espera uma lista de dicionários.
    # Cada linha terá o conteúdo do chunk, o vetor de embedding e metadados.
    data_to_insert = [
        {
            'content': chunk,
            'embedding': embedding,
            'source': source # Metadado útil para saber a origem da informação
        }
        for chunk, embedding in zip(chunks, embeddings)
    ]

    # 4. Inserir os dados na tabela do Supabase
    # A tabela deve ter sido criada previamente no Supabase com as colunas:
    # id (int8, primary key), content (text), embedding (vector), source (text)
    try:
        response = supabase.table('documents').insert(data_to_insert).execute()
        print(f"Dados inseridos no Supabase com sucesso.")
    except Exception as e:
        print(f"Erro ao inserir dados no Supabase: {e}")
        print("Verifique se a tabela 'documents' existe e se a função de busca vetorial foi criada.")

def search_relevant_chunks(query: str, top_k: int = 3) -> list:
    """
    Realiza uma busca vetorial no Supabase para encontrar os chunks mais relevantes.
    Esta é a função que o agente LangChain usará como ferramenta.
    """
    if not supabase or not embeddings_model:
        print("Cliente Supabase ou modelo de embeddings não inicializado. Abortando.")
        return []

    # 1. Gera o embedding da pergunta do usuário
    query_embedding = embeddings_model.embed_query(query)

    # 2. Chama a função RPC do Supabase para busca de similaridade
    # É necessário criar uma função no seu banco de dados Supabase.
    # Exemplo de SQL para a função:
    #   create or replace function match_documents (
    #     query_embedding vector(1536), -- O tamanho deve corresponder ao do seu modelo de embedding
    #     match_count int
    #   )
    #   returns table (
    #     id bigint,
    #     content text,
    #     source text,
    #     similarity float
    #   )
    #   language plpgsql
    #   as $$
    #   begin
    #     return query
    #     select
    #       documents.id,
    #       documents.content,
    #       documents.source,
    #       1 - (documents.embedding <=> query_embedding) as similarity
    #     from documents
    #     order by documents.embedding <=> query_embedding
    #     limit match_count;
    #   end;
    #   $$;
    try:
        response = supabase.rpc('match_documents', {
            'query_embedding': query_embedding,
            'match_count': top_k
        }).execute()

        print(f"Busca por '{query}' retornou {len(response.data)} resultados.")
        return response.data
    except Exception as e:
        print(f"Erro ao executar a busca vetorial no Supabase: {e}")
        return []

# --- Exemplo de Uso ---
if __name__ == '__main__':
    print("Integração com Supabase para RAG.")

    if not all([SUPABASE_URL, SUPABASE_KEY, os.getenv('OPENAI_API_KEY')]):
        print("\nAs variáveis de ambiente SUPABASE_URL, SUPABASE_KEY e OPENAI_API_KEY devem estar configuradas.")
    else:
        # Inicializa os clientes
        embeddings_model = OpenAIEmbeddings()
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

        # 1. Simula o processamento e embedding de dois relatórios
        print("\n--- Processando e Inserindo Documentos ---")
        text_focus = preprocess_document("Relatorio_Focus.pdf")
        create_and_embed_chunks(text_focus, "Relatório Focus")

        text_copom = preprocess_document("Ata_COPOM.pdf")
        create_and_embed_chunks(text_copom, "Ata do COPOM")

        # 2. Simula uma pergunta do usuário e busca por chunks relevantes
        print("\n--- Realizando Busca Vetorial ---")
        user_query = "Qual a visão do COPOM sobre o cenário externo?"
        results = search_relevant_chunks(user_query)

        if results:
            print(f"\nResultados mais relevantes para a pergunta: '{user_query}'")
            for result in results:
                print(f"  Fonte: {result['source']}")
                print(f"  Similaridade: {result['similarity']:.4f}")
                print(f"  Conteúdo: {result['content']}\n")
