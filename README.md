# Agente de Análise de Investimentos com LangChain

## Descrição Geral

Este projeto estabelece a arquitetura fundamental para um Agente de Análise de Investimentos autônomo. Utilizando a biblioteca LangChain, o agente fornece insights financeiros e recomendações de investimento.

A arquitetura integra os seguintes componentes:
- **Agente de IA:** Orquestrado com **LangChain** para processar requisições e utilizar ferramentas.
- **Gerenciamento de Sessão:** Utiliza **Supabase** (API REST) para armazenar o histórico de interações, garantindo continuidade e personalização.
- **Base de Conhecimento (RAG):** Emprega **Supabase** como banco de dados vetorial para indexar e consultar documentos importantes (ex: Relatórios Focus, Atas do COPOM) através de Retrieval Augmented Generation.
- **Busca na Internet:** Estrutura para realizar buscas na web e obter dados em tempo real.

## Estrutura do Projeto

O projeto é composto pelos seguintes scripts modulares:

- `langchain_agent.py`
  - **Propósito:** Define o agente de IA já configurado com ferramentas reais de busca vetorial (Supabase) e busca na internet.
- `postgresql_session_management.py`
  - **Propósito:** Gerencia a persistência do histórico de conversa usando Supabase.
- `supabase_rag_integration.py`
  - **Propósito:** Implementa a integração com o Supabase para a funcionalidade RAG, incluindo extração de texto de PDFs, geração de embeddings e busca vetorial.
- `internet_search.py`
  - **Propósito:** Implementa uma ferramenta real de busca na internet utilizando a API Tavily.
- `main.py`
  - **Propósito:** Exponibiliza o agente como uma API FastAPI compatível com o formato da OpenAI.

## Instalação

Siga os passos abaixo para configurar e executar o projeto em seu ambiente local.

1. **Clonar o Repositório**
   ```bash
   git clone [URL_do_seu_repositório]
   cd [nome_do_repositorio]
   ```

2. **Criar e Ativar um Ambiente Virtual**
   ```bash
   # Crie o ambiente virtual
   python -m venv venv

   # Ative o ambiente (Linux/macOS)
   source venv/bin/activate

   # Ative o ambiente (Windows)
   venv\Scripts\activate
   ```

3. **Instalar as Dependências**
   Instale todas as bibliotecas Python necessárias com o seguinte comando:
   ```bash
   pip install -r requirements.txt
   ```

## Configuração do Ambiente (.env)

Para garantir a segurança das credenciais, o projeto utiliza um arquivo `.env` para carregar variáveis de ambiente.

1. Crie um arquivo chamado `.env` na raiz do projeto.
2. Copie o conteúdo abaixo para o seu arquivo `.env` e substitua os placeholders pelas suas credenciais reais.

```plaintext
# .env.example

# Credenciais do Supabase (encontradas no painel do seu projeto Supabase)
SUPABASE_URL="https://[seu_id_de_projeto].supabase.co"
SUPABASE_KEY="sua_chave_anon_ou_service_role_aqui"

# Chave de API para o modelo de linguagem (ex: OpenAI)
OPENAI_API_KEY="sk-sua_chave_de_api_aqui"

# Chave de API para consultas de ações na Alpha Vantage
# Pode ser definida como `ALPHA_VANTAGE` (recomendado) ou `ALPHA_VANTAGE_API_KEY`
ALPHA_VANTAGE="sua_chave_alpha_vantage_aqui"

# Chave utilizada para autenticar requisições à API FastAPI deste projeto
API_KEY="chave_de_acesso_local"

# (Opcional) Chave de API para um serviço de busca na internet (ex: Tavily)
TAVILY_API_KEY="tvly-sua_chave_de_api_aqui"
```

## Inicialização do Banco (Supabase)

Após configurar o arquivo `.env`, execute uma única vez o script de inicialização
para preparar o banco de dados no Supabase:

```bash
python initialize_supabase.py
```

Esse script habilita a extensão `vector`, cria as tabelas necessárias e define a
função `match_documents` usada nas buscas vetoriais.

## Uso

Cada script pode ser executado individualmente para testar sua funcionalidade. Certifique-se de que seu arquivo `.env` está configurado corretamente antes de prosseguir.

- **Estrutura do Agente**
  ```bash
  python langchain_agent.py
  ```

- **Gerenciamento de Sessão (Supabase)**
  ```bash
  python postgresql_session_management.py
  ```

- **Integração RAG com Supabase**
  ```bash
  python supabase_rag_integration.py
  ```

- **Busca na Internet**
  ```bash
  python internet_search.py
  ```

- **API FastAPI**
  ```bash
  uvicorn main:app --host 0.0.0.0 --port 8000
  ```

- **Teste integrado**
  ```bash
  python main.py
  ```

- **Exemplo de chamada ao endpoint**
  Com o servidor em execução, envie uma requisição com `curl` (substitua `API_KEY` pelo valor definido no `.env`):
  ```bash
  curl -X POST "http://localhost:8000/v1/chat/completions" \
       -H "Content-Type: application/json" \
       -H "Authorization: Bearer ${API_KEY}" \
       -d '{"messages":[{"role":"user","content":"Qual o preço da ação BBAS3?"}]}'
  ```

## Contribuição

Contribuições são bem-vindas! Se você tiver sugestões para melhorar este projeto, sinta-se à vontade para abrir uma *issue* ou enviar um *pull request*.

## Licença

Este projeto está sob a licença MIT.
