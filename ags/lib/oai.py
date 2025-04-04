from functools import cache
from openai import OpenAI


@cache
def get_oai_client() -> OpenAI:
    return OpenAI()
