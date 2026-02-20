#!/usr/bin/env python3
"""
Integration test for Sampler library.

Usage:
    OPENAI_API_KEY=sk-... ANTHROPIC_API_KEY=sk-ant-... python -m ags.lib.sampler_test
    OPENAI_API_KEY=sk-... python -m ags.lib.sampler_test openai
    ANTHROPIC_API_KEY=sk-ant-... python -m ags.lib.sampler_test claude
"""

import os
import sys

from ags.lib.sampler import Sampler, PROVIDERS


def test_chat(provider: str) -> bool:
    print(f"\n--- Testing {provider.upper()} Chat ---")
    try:
        sampler = Sampler.create(provider=provider)
        response = sampler.chat(
            system_prompt="You are a helpful assistant. Be very brief.",
            messages=[
                {"role": "user", "content": f'Say "Hello from {provider}!" and nothing else.'}
            ],
            max_tokens=50,
        )
        print(f"  Response: {response.text}")
        print(f"  Model:    {response.model}")
        print(f"  Tokens:   in={response.input_tokens} out={response.output_tokens}")
        print("  PASS")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        return False


def test_stream(provider: str) -> bool:
    print(f"\n--- Testing {provider.upper()} Stream ---")
    try:
        sampler = Sampler.create(provider=provider)
        sys.stdout.write("  Streaming: ")
        for chunk in sampler.chat_stream(
            system_prompt="You are a helpful assistant. Be very brief.",
            messages=[
                {"role": "user", "content": "Count from 1 to 5, separated by commas."}
            ],
            max_tokens=50,
        ):
            sys.stdout.write(chunk)
            sys.stdout.flush()
        print("\n  PASS")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        return False


def main():
    print("=== Sampler Integration Test ===")

    args = sys.argv[1:]
    providers_to_test = []

    if args:
        providers_to_test = [a.lower() for a in args]
    else:
        if os.environ.get("OPENAI_API_KEY"):
            providers_to_test.append("openai")
        if os.environ.get("ANTHROPIC_API_KEY"):
            providers_to_test.append("claude")

    if not providers_to_test:
        print("\nNo API keys found. Set OPENAI_API_KEY and/or ANTHROPIC_API_KEY")
        print("\nUsage:")
        print("  OPENAI_API_KEY=sk-... python -m ags.lib.sampler_test")
        print("  ANTHROPIC_API_KEY=sk-ant-... python -m ags.lib.sampler_test claude")
        sys.exit(1)

    results = {}
    for provider in providers_to_test:
        chat_ok = test_chat(provider)
        stream_ok = test_stream(provider)
        results[provider] = chat_ok and stream_ok

    print("\n=== Summary ===")
    all_passed = True
    for provider, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  {status}: {provider}")
        if not passed:
            all_passed = False

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
