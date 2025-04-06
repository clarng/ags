from functools import cache
import os
from typing import Any, List, Dict, Optional, Union
import pinecone
from pinecone import Index
from mcp.server.fastmcp import FastMCP
from ags.lib.embeddings import generate_oai_embeddings

# Initialize FastMCP server
mcp = FastMCP("pinecone")

# Initialize Pinecone
@cache
def init_pinecone() -> pinecone.Pinecone:
    """Initialize Pinecone with API key from environment variable."""
    api_key = os.environ.get("PINECONE_API_KEY")
    if not api_key:
        raise ValueError("PINECONE_API_KEY environment variable not set")
    
    return pinecone.Pinecone(api_key=api_key)

# Get or create index
def get_index(index_name: str, dimension: int = 1536) -> Union[Index, str]:
    """Get or create a Pinecone index."""
    try:
        pc = init_pinecone()
        
        # Check if index exists
        if index_name not in pc.list_indexes().names():
            # Create index if it doesn't exist
            pc.create_index(
                name=index_name,
                dimension=dimension,
                metric="cosine"
            )
        
        # Connect to the index
        return pc.Index(index_name)
    except Exception as e:
        return f"Error initializing Pinecone: {str(e)}"

@mcp.tool()
async def store_embedding(
    index_name: str,
    text: str,
    metadata: Dict[str, Any] | None = None,
    id: Optional[str] = None
) -> None:
    """Store text embedding.
    
    Args:
        index_name: Name of the index
        text: Text to generate embedding from
        metadata: Optional metadata to store with the embedding
        id: Optional ID for the vector. If not provided, a stable hash of the text will be used.
        
    Raises:
        Exception: If there is an error storing the embedding
    """
    index = get_index(index_name)
    if isinstance(index, str):  # Error message
        raise Exception(index)
        
    # Generate embedding
    embedding = generate_oai_embeddings(text)
    
    # Prepare metadata
    if metadata is None:
        metadata = {}
    metadata["text"] = text
    
    # Upsert to Pinecone
    index.upsert(
        vectors=[(id or f"vec_{hash(text)}", embedding, metadata)],
        namespace="default"
    )

@mcp.tool()
async def query_similar(
    index_name: str,
    query_text: str,
    top_k: int = 5
) -> List[Dict[str, Any]]:
    """Query for similar texts.
    
    Args:
        index_name: Name of the index
        query_text: Text to find similar embeddings for
        top_k: Number of closest matching results to return
        
    Returns:
        List of similar texts with their metadata
        
    Raises:
        Exception: If there is an error querying Pinecone
    """
    index = get_index(index_name)
    if isinstance(index, str):  # Error message
        raise Exception(index)
            
    # Generate embedding for query
    query_embedding = generate_oai_embeddings(query_text)
    
    # Query Pinecone
    results = index.query(
        vector=query_embedding,
        top_k=top_k,
        include_metadata=True,
        namespace="default"
    )
    
    # Format results
    formatted_results = []
    for match in results.matches:
        formatted_results.append({
            "id": match.id,
            "score": match.score,
            "text": match.metadata.get("text", ""),
            "metadata": match.metadata
        })
        
    return formatted_results

if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')