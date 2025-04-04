from ags.lib.oai import get_oai_client

def generate_oai_embeddings(text: str, model: str = "text-embedding-3-small") -> list[float]:
    response = get_oai_client().embeddings.create(
        input=text,
        model=model
    )

    return response.data[0].embedding

def test():
    print("hi")
