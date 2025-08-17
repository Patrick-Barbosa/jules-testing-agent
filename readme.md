# Agente de Análise de Investimentos com LangChain

## Descrição Geral

Este projeto estabelece a arquitetura fundamental para um Agente de Análise de Investimentos autônomo. Utilizando a biblioteca LangChain, o agente é projetado para fornecer insights financeiros e recomendações de investimento.

A arquitetura integra os seguintes componentes:
- **Agente de IA:** Orquestrado com **LangChain** para processar requisições e utilizar ferramentas.
- **Gerenciamento de Sessão:** Utiliza **PostgreSQL** para armazenar o histórico de interações, garantindo continuidade e personalização.
- **Base de Conhecimento (RAG):** Emprega **Supabase** como um banco de dados vetorial para indexar e consultar documentos importantes (ex: Relatórios Focus, Atas do COPOM) através da técnica de Retrieval Augmented Generation.
- **Busca na Internet:** Possui uma estrutura para realizar buscas na web e obter dados em tempo real.

## Estrutura do Projeto

O projeto é composto pelos seguintes scripts modulares:

-   `1_langchain_agent_structure.py`
    -   **Propósito:** Define o esqueleto do agente de IA. Inclui placeholders para a inicialização do modelo de linguagem (LLM) e para a integração das ferramentas de busca.
-   `2_postgresql_session_management.py`
    -   **Propósito:** Gerencia a conexão com o banco de dados PostgreSQL. Contém funções para criar a tabela de histórico, salvar e carregar conversas de usuários associadas a uma ID de sessão.
-   `3_supabase_rag_integration.py`
    -   **Propósito:** Lida com a integração com o Supabase para a funcionalidade RAG. Inclui código para inicializar o cliente, pré-processar documentos, gerar embeddings de texto e realizar buscas vetoriais para encontrar informações relevantes.
-   `4_internet_search_stub.py`
    -   **Propósito:** Fornece um placeholder para uma ferramenta de busca na internet. Simula a funcionalidade que, em uma implementação completa, se conectaria a uma API de busca (como Google, Bing ou Tavily) para obter dados externos.

## Instalação

Siga os passos abaixo para configurar e executar o projeto em seu ambiente local.

1.  **Clonar o Repositório**
    ```bash
    git clone [URL_do_seu_repositório]
    cd [nome_do_repositorio]
    ```

2.  **Criar e Ativar um Ambiente Virtual**
    ```bash
    # Crie o ambiente virtual
    python -m venv venv

    # Ative o ambiente (Linux/macOS)
    source venv/bin/activate

    # Ative o ambiente (Windows)
    venv\Scripts\activate
    ```

3.  **Instalar as Dependências**
    Instale todas as bibliotecas Python necessárias com o seguinte comando:
    ```bash
    pip install -r requirements.txt
    ```

## Configuração do Ambiente (.env)

Para garantir a segurança das credenciais, o projeto utiliza um arquivo `.env` para carregar variáveis de ambiente.

1.  Crie um arquivo chamado `.env` na raiz do projeto.
2.  Copie o conteúdo abaixo para o seu arquivo `.env` e substitua os placeholders pelas suas credenciais reais.

```plaintext
# .env.example

# Credenciais para o banco de dados PostgreSQL
# Formato: postgresql://[user]:[password]@[host]:[port]/[dbname]
DATABASE_URL="postgresql://postgres:seu_password_aqui@db.example.com:5432/postgres"

# Credenciais do Supabase (encontradas no painel do seu projeto Supabase)
SUPABASE_URL="https://[seu_id_de_projeto].supabase.co"
SUPABASE_KEY="sua_chave_anon_ou_service_role_aqui"

# Chave de API para o modelo de linguagem (ex: OpenAI)
OPENAI_API_KEY="sk-sua_chave_de_api_aqui"

# (Opcional) Chave de API para um serviço de busca na internet (ex: Tavily)
TAVILY_API_KEY="tvly-sua_chave_de_api_aqui"
```

## Uso

Cada script pode ser executado individualmente para testar sua funcionalidade. Certifique-se de que seu arquivo `.env` está configurado corretamente antes de prosseguir.

-   **Estrutura do Agente**
    Este script imprime uma mensagem indicando que a estrutura do agente está pronta.
    ```bash
    python 1_langchain_agent_structure.py
    ```

-   **Gerenciamento de Sessão com PostgreSQL**
    Este script testa a conexão com o banco de dados, cria a tabela de histórico (se não existir) e demonstra como salvar e carregar uma conversa.
    ```bash
    python 2_postgresql_session_management.py
    ```

-   **Integração RAG com Supabase**
    Este script demonstra o fluxo de processamento de documentos, geração de embeddings e busca vetorial no Supabase.
    ```bash
    python 3_supabase_rag_integration.py
    ```

-   **Busca na Internet**
    Este script executa uma simulação de busca na internet e imprime os resultados mocados.
    ```bash
    python 4_internet_search_stub.py
    ```

## Contribuição

Contribuições são bem-vindas! Se você tiver sugestões para melhorar este projeto, sinta-se à vontade para abrir uma *issue* ou enviar um *pull request*.

## Licença

Este projeto está sob a licença MIT.
