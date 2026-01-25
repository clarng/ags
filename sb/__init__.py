"""
SB (Sparse Brain) - DeepSeek-style Engram FFN Implementation

This package provides a simplified implementation of Mixture of Experts (MoE)
FFN layers with engram prefetch and overlap capabilities, inspired by DeepSeek's
architecture.

Key features:
- Mixture of Experts FFN with top-k routing
- Asynchronous weight prefetching (engram system)
- Overlap of memory transfers with computation
- Performance metrics for prefetch/overlap efficiency

The engram system prefetches expert weights before they're needed, allowing
memory transfers to overlap with computation rather than blocking. This is
particularly important for large MoE models where expert weights may need
to be loaded from CPU/disk to GPU memory.

Usage:
    from sb import EngramMoEFFN

    ffn = EngramMoEFFN(
        hidden_size=256,
        intermediate_size=512,
        num_experts=8,
        top_k=2,
        enable_prefetch=True,
    )
    ffn.start_prefetcher()

    output, stats = ffn(hidden_states)
    print(f"Prefetch hits: {stats['prefetch_hits']}")
    print(f"Overlap efficiency: {1 - stats['blocked_time']/stats['total_time']:.1%}")

    ffn.stop_prefetcher()
"""

from .engram_ffn import EngramMoEFFN, EngramPrefetcher, ExpertFFN

__all__ = ['EngramMoEFFN', 'EngramPrefetcher', 'ExpertFFN']
__version__ = '0.1.0'
