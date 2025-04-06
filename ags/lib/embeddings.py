from ags.lib.oai import get_oai_client

def generate_oai_embeddings(texts: list[str], model: str = "text-embedding-3-small") -> list[list[float]]:
    """Generate embeddings for a batch of texts.
    
    Args:
        texts: List of texts to generate embeddings for
        model: Model to use for embeddings
        
    Returns:
        List of embeddings, one for each input text
    """
    if not texts:
        return []
        
    response = get_oai_client().embeddings.create(
        input=texts,
        model=model
    )
    
    return [item.embedding for item in response.data]

def test():
    print("hi")
