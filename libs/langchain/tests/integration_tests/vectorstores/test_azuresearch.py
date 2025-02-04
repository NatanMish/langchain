import os
import time

import pytest
from azure.search.documents.indexes.models import (
    SearchableField,
    SearchField,
    SearchFieldDataType,
    SimpleField,
)
from dotenv import load_dotenv

from langchain.chains import RetrievalQA
from langchain.chat_models.azure_openai import AzureChatOpenAI
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores.azuresearch import AzureSearch

load_dotenv()

model = os.getenv("OPENAI_EMBEDDINGS_ENGINE_DOC", "text-embedding-ada-002")
# Vector store settings
vector_store_address: str = os.getenv("AZURE_SEARCH_ENDPOINT", "")
vector_store_password: str = os.getenv("AZURE_SEARCH_ADMIN_KEY", "")
index_name: str = "embeddings-vector-store-test"


@pytest.fixture
def similarity_search_test() -> None:
    """Test end to end construction and search."""
    # Create Embeddings
    embeddings: OpenAIEmbeddings = OpenAIEmbeddings(model=model, chunk_size=1)
    # Create Vector store
    vector_store: AzureSearch = AzureSearch(
        azure_search_endpoint=vector_store_address,
        azure_search_key=vector_store_password,
        index_name=index_name,
        embedding_function=embeddings.embed_query,
    )
    # Add texts to vector store and perform a similarity search
    vector_store.add_texts(
        ["Test 1", "Test 2", "Test 3"],
        [
            {"title": "Title 1", "any_metadata": "Metadata 1"},
            {"title": "Title 2", "any_metadata": "Metadata 2"},
            {"title": "Title 3", "any_metadata": "Metadata 3"},
        ],
    )
    time.sleep(1)
    res = vector_store.similarity_search(query="Test 1", k=3)
    assert len(res) == 3


def from_text_similarity_search_test() -> None:
    """Test end to end construction and search."""
    # Create Embeddings
    embeddings: OpenAIEmbeddings = OpenAIEmbeddings(model=model, chunk_size=1)
    # Create Vector store
    vector_store: AzureSearch = AzureSearch.from_texts(
        azure_search_endpoint=vector_store_address,
        azure_search_key=vector_store_password,
        index_name=index_name,
        texts=["Test 1", "Test 2", "Test 3"],
        embedding=embeddings,
    )
    time.sleep(1)
    # Perform a similarity search
    res = vector_store.similarity_search(query="Test 1", k=3)
    assert len(res) == 3


def test_semantic_hybrid_search() -> None:
    """Test end to end construction and search."""
    # Create Embeddings
    embeddings: OpenAIEmbeddings = OpenAIEmbeddings(model=model, chunk_size=1)
    # Create Vector store
    vector_store: AzureSearch = AzureSearch(
        azure_search_endpoint=vector_store_address,
        azure_search_key=vector_store_password,
        index_name=index_name,
        embedding_function=embeddings.embed_query,
        semantic_configuration_name="default",
    )
    # Add texts to vector store and perform a semantic hybrid search
    vector_store.add_texts(
        ["Test 1", "Test 2", "Test 3"],
        [
            {"title": "Title 1", "any_metadata": "Metadata 1"},
            {"title": "Title 2", "any_metadata": "Metadata 2"},
            {"title": "Title 3", "any_metadata": "Metadata 3"},
        ],
    )
    time.sleep(1)
    res = vector_store.semantic_hybrid_search(query="What's Azure Search?", k=3)
    assert len(res) == 3


def test_azuresearch_custom_fields() -> None:
    """Tests that custom fields are correctly passed to Azure Search."""
    llm = AzureChatOpenAI(
        openai_api_base=f"https://{os.environ['openai_instance']}.openai.azure.com/",
        openai_api_version="2023-05-15",
        openai_api_key=os.environ["OPENAI_API_KEY"],
        deployment_name="gpt-35-turbo",
        openai_api_type="azure",
        model_name="gpt-35-turbo",
    )

    fields = [
        SimpleField(
            name="id",
            type=SearchFieldDataType.String,
            key=True,
            filterable=True,
        ),
        SearchableField(
            name="text",
            type=SearchFieldDataType.String,
            searchable=True,
        ),
        SearchField(
            name="embedding",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=1536,
            vector_search_configuration="default",
        ),
    ]

    # Create Embeddings
    embeddings: OpenAIEmbeddings = OpenAIEmbeddings(model=model, chunk_size=1)
    vector_store: AzureSearch = AzureSearch(
        azure_search_endpoint=vector_store_address,
        azure_search_key=vector_store_password,
        index_name=index_name,
        embedding_function=embeddings.embed_query,
        fields=fields,
    )

    assert vector_store.fields == fields

    retriever = vector_store.as_retriever(search_type="similarity", kwargs={"k": 3})

    # Creating instance of RetrievalQA
    chain = RetrievalQA.from_chain_type(
        llm=llm, chain_type="stuff", retriever=retriever, return_source_documents=True
    )

    # Generating response to user's query
    assert chain({"query": "some_query"})
