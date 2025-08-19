# 3_vector_store_manager_refactored.py

import os
import logging
from typing import Any, Dict, List

from supabase import Client, create_client
from postgrest.exceptions import APIError
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from PyPDF2 import PdfReader
from dotenv import load_dotenv

load_dotenv()

# --- Configuration ---
# Set up basic logging to see the script's output
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class VectorStoreManager:
    """
    Manages embedding, storage, and retrieval of documents with Supabase.
    """
    def __init__(self, supabase_url: str, supabase_key: str, openai_key: str):
        """
        Initializes the Supabase client and the OpenAI embeddings model.
        
        Raises:
            ValueError: If any of the required API keys or URLs are not provided.
        """
        if not all([supabase_url, supabase_key, openai_key]):
            raise ValueError("Supabase URL/Key and OpenAI API Key are required.")

        try:
            self.client: Client = create_client(supabase_url, supabase_key)
            self.embeddings_model: OpenAIEmbeddings = OpenAIEmbeddings(
                model="text-embedding-ada-002",
                api_key=openai_key
            )
            logging.info("VectorStoreManager initialized successfully.")
        except Exception as e:
            logging.error(f"Failed to initialize clients: {e}")
            raise

    @staticmethod
    def preprocess_document(file_path: str) -> str:
        """
        Extracts text from a PDF or a plain text file.
        This is a static method because it doesn't rely on instance state (self).
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        if file_path.lower().endswith(".pdf"):
            text = ""
            with open(file_path, "rb") as fp:
                reader = PdfReader(fp)
                for page in reader.pages:
                    text += page.extract_text() or ""
            return text

        with open(file_path, "r", encoding="utf-8") as fp:
            return fp.read()

    def upsert_documents(self, chunks: List[Dict[str, Any]]) -> None:
        """Inserts or updates document chunks with their embeddings into Supabase."""
        texts = [c["content"] for c in chunks]
        if not texts:
            logging.warning("No text found in chunks to upsert.")
            return

        embeddings = self.embeddings_model.embed_documents(texts)
        
        rows = [
            {
                "content": chunk["content"],
                "embedding": emb,
                "metadata": chunk.get("metadata", {}),
            }
            for chunk, emb in zip(chunks, embeddings)
        ]

        try:
            self.client.table("documents").upsert(rows).execute()
            logging.info(f"{len(rows)} document chunks upserted into Supabase.")
        except APIError as e:
            logging.error(f"Error upserting chunks: {e.message}")

    def retrieve_relevant_documents(
        self, query: str, match_threshold: float = 0.78, top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Retrieves the most relevant document chunks from Supabase via vector search."""
        query_embedding = self.embeddings_model.embed_query(query)
        
        try:
            response = self.client.rpc(
                "match_documents",
                {
                    "query_embedding": query_embedding,
                    "match_count": top_k,
                    "match_threshold": match_threshold,
                },
            ).execute()
            return response.data or []
        except APIError as e:
            logging.error(f"Error during vector search: {e.message}")
            return []

    def ingest_file(self, file_path: str, source_name: str) -> None:
        """Utility method to process and ingest a file into the vector store."""
        try:
            text = self.preprocess_document(file_path)
            splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
            chunks = [
                {"content": c, "metadata": {"source": source_name}} 
                for c in splitter.split_text(text)
            ]
            self.upsert_documents(chunks)
            logging.info(f"Successfully ingested file: {file_path}")
        except FileNotFoundError as e:
            logging.error(e)
        except Exception as e:
            logging.error(f"An unexpected error occurred during ingestion of {file_path}: {e}")


def main():
    """Main function to demonstrate the VectorStoreManager."""
    try:
        # Load credentials from environment variables
        manager = VectorStoreManager(
            supabase_url=os.getenv("SUPABASE_URL"),
            supabase_key=os.getenv("SUPABASE_KEY"),
            openai_key=os.getenv("OPENAI_API_KEY")
        )

        # 1. Preload some example documents
        logging.info("Preloading example documents...")
        example_docs = [
            {"content": "Relatório Focus projeta inflação de 3.9% para 2024.", "metadata": {"source": "Focus"}},
            {"content": "Ata do COPOM registra manutenção da taxa Selic em 13.75%.", "metadata": {"source": "COPOM"}},
        ]
        manager.upsert_documents(example_docs)

        # 2. Retrieve relevant documents
        query = "qual a projeção da inflação?"
        logging.info(f"\nSearching for documents relevant to: '{query}'")
        results = manager.retrieve_relevant_documents(query)
        
        if results:
            print("\n--- Search Results ---")
            for doc in results:
                print(f"  Content: {doc['content']}")
                print(f"  Similarity: {doc['similarity']:.4f}")
                print(f"  Metadata: {doc['metadata']}")
                print("-" * 20)
        else:
            print("No relevant documents found.")

    except ValueError as e:
        logging.error(f"Initialization failed: {e}")

if __name__ == "__main__":
    main()