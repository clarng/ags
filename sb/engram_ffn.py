"""
Engram FFN Implementation

A simplified implementation of DeepSeek-style Mixture of Experts (MoE) FFN
with engram prefetch and overlap capabilities.

The engram system prefetches expert weights before they're needed, allowing
memory transfers to overlap with computation rather than blocking.

This implementation uses numpy for portability but maintains the same
interface and concepts as a PyTorch implementation.
"""

import numpy as np
from typing import Optional, List, Tuple, Dict, Any
import threading
import queue
import time


def silu(x: np.ndarray) -> np.ndarray:
    """SiLU (Swish) activation function."""
    return x * (1.0 / (1.0 + np.exp(-x)))


def softmax(x: np.ndarray, axis: int = -1) -> np.ndarray:
    """Softmax activation function."""
    exp_x = np.exp(x - np.max(x, axis=axis, keepdims=True))
    return exp_x / np.sum(exp_x, axis=axis, keepdims=True)


class ExpertFFN:
    """Single expert FFN layer with SwiGLU activation."""

    def __init__(self, hidden_size: int, intermediate_size: int):
        self.hidden_size = hidden_size
        self.intermediate_size = intermediate_size
        # Initialize weights (He initialization)
        scale = np.sqrt(2.0 / hidden_size)
        self.gate_proj = np.random.randn(intermediate_size, hidden_size).astype(np.float32) * scale
        self.up_proj = np.random.randn(intermediate_size, hidden_size).astype(np.float32) * scale
        self.down_proj = np.random.randn(hidden_size, intermediate_size).astype(np.float32) * scale

    def forward(self, x: np.ndarray) -> np.ndarray:
        """Forward pass with SwiGLU activation."""
        gate_out = x @ self.gate_proj.T
        up_out = x @ self.up_proj.T
        hidden = silu(gate_out) * up_out
        return hidden @ self.down_proj.T

    def get_weights(self) -> Dict[str, np.ndarray]:
        """Return a copy of the weights."""
        return {
            'gate_proj': self.gate_proj.copy(),
            'up_proj': self.up_proj.copy(),
            'down_proj': self.down_proj.copy(),
        }

    def __call__(self, x: np.ndarray) -> np.ndarray:
        return self.forward(x)


class EngramPrefetcher:
    """
    Engram prefetch system for expert weights.

    Handles asynchronous prefetching of expert weights from CPU/storage
    to 'GPU' memory (simulated), allowing overlap with computation.
    """

    def __init__(self, num_experts: int, simulate_transfer_time: float = 0.001):
        """
        Args:
            num_experts: Number of experts in the MoE layer
            simulate_transfer_time: Simulated memory transfer time in seconds
        """
        self.num_experts = num_experts
        self.simulate_transfer_time = simulate_transfer_time
        self.prefetch_queue = queue.Queue()
        self.prefetch_cache: Dict[int, Dict[str, np.ndarray]] = {}
        self.prefetch_events: Dict[int, threading.Event] = {}
        self._prefetch_thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.Lock()
        self.stats = {
            'prefetch_hits': 0,
            'prefetch_misses': 0,
            'total_prefetch_time': 0.0,
            'blocked_time': 0.0,
        }

    def start(self):
        """Start the prefetch worker thread."""
        self._running = True
        self._prefetch_thread = threading.Thread(target=self._prefetch_worker, daemon=True)
        self._prefetch_thread.start()

    def stop(self):
        """Stop the prefetch worker thread."""
        self._running = False
        if self._prefetch_thread:
            self.prefetch_queue.put(None)  # Signal to stop
            self._prefetch_thread.join(timeout=1.0)

    def _prefetch_worker(self):
        """Background worker that handles prefetch requests."""
        while self._running:
            try:
                item = self.prefetch_queue.get(timeout=0.1)
                if item is None:
                    break
                expert_id, weights_cpu, event = item
                start_time = time.perf_counter()

                # Simulate async memory transfer (CPU -> GPU)
                time.sleep(self.simulate_transfer_time)

                # Store in cache (simulating GPU memory)
                with self._lock:
                    self.prefetch_cache[expert_id] = weights_cpu
                    self.stats['total_prefetch_time'] += time.perf_counter() - start_time

                event.set()

            except queue.Empty:
                continue

    def schedule_prefetch(self, expert_id: int, weights_cpu: Dict[str, np.ndarray]) -> threading.Event:
        """Schedule a prefetch for the given expert weights."""
        event = threading.Event()
        with self._lock:
            self.prefetch_events[expert_id] = event
        self.prefetch_queue.put((expert_id, weights_cpu, event))
        return event

    def get_weights(self, expert_id: int, fallback_fn) -> Tuple[Dict[str, np.ndarray], bool]:
        """
        Get weights for an expert, using prefetch cache if available.

        Returns:
            Tuple of (weights_dict, was_prefetch_hit)
        """
        with self._lock:
            if expert_id in self.prefetch_cache:
                # Check if prefetch is still in progress
                if expert_id in self.prefetch_events:
                    event = self.prefetch_events[expert_id]
                    # Release lock while waiting
                    self._lock.release()
                    try:
                        start_wait = time.perf_counter()
                        event.wait()
                        blocked_time = time.perf_counter() - start_wait
                    finally:
                        self._lock.acquire()
                    self.stats['blocked_time'] += blocked_time

                self.stats['prefetch_hits'] += 1
                weights = self.prefetch_cache.pop(expert_id)
                if expert_id in self.prefetch_events:
                    del self.prefetch_events[expert_id]
                return weights, True
            else:
                self.stats['prefetch_misses'] += 1
                return fallback_fn(), False

    def clear_cache(self):
        """Clear the prefetch cache."""
        with self._lock:
            self.prefetch_cache.clear()
            self.prefetch_events.clear()

    def reset_stats(self):
        """Reset statistics."""
        with self._lock:
            self.stats = {
                'prefetch_hits': 0,
                'prefetch_misses': 0,
                'total_prefetch_time': 0.0,
                'blocked_time': 0.0,
            }


class EngramMoEFFN:
    """
    Mixture of Experts FFN with Engram prefetch support.

    Features:
    - Top-k expert routing
    - Asynchronous weight prefetching
    - Overlap of memory transfer and computation
    """

    def __init__(
        self,
        hidden_size: int,
        intermediate_size: int,
        num_experts: int,
        top_k: int = 2,
        enable_prefetch: bool = True,
        simulate_transfer_time: float = 0.001,
    ):
        self.hidden_size = hidden_size
        self.intermediate_size = intermediate_size
        self.num_experts = num_experts
        self.top_k = top_k
        self.enable_prefetch = enable_prefetch

        # Router to select experts
        self.router_weight = np.random.randn(num_experts, hidden_size).astype(np.float32) * 0.01

        # Expert FFN layers
        self.experts = [
            ExpertFFN(hidden_size, intermediate_size)
            for _ in range(num_experts)
        ]

        # Prefetcher
        self.prefetcher = EngramPrefetcher(num_experts, simulate_transfer_time)

        # Timing stats
        self.timing_stats = {
            'router_time': 0.0,
            'expert_compute_time': 0.0,
            'total_forward_time': 0.0,
            'num_forwards': 0,
        }

    def start_prefetcher(self):
        """Start the prefetch system."""
        if self.enable_prefetch:
            self.prefetcher.start()

    def stop_prefetcher(self):
        """Stop the prefetch system."""
        if self.enable_prefetch:
            self.prefetcher.stop()

    def get_expert_weights(self, expert_id: int) -> Dict[str, np.ndarray]:
        """Get expert weights."""
        return self.experts[expert_id].get_weights()

    def prefetch_experts(self, expert_ids: List[int]):
        """Prefetch weights for the specified experts."""
        if not self.enable_prefetch:
            return

        for expert_id in expert_ids:
            if expert_id not in self.prefetcher.prefetch_cache:
                weights = self.get_expert_weights(expert_id)
                self.prefetcher.schedule_prefetch(expert_id, weights)

    def compute_with_weights(self, x: np.ndarray, weights: Dict[str, np.ndarray]) -> np.ndarray:
        """Compute FFN output using provided weights."""
        gate_out = x @ weights['gate_proj'].T
        up_out = x @ weights['up_proj'].T
        hidden = silu(gate_out) * up_out
        return hidden @ weights['down_proj'].T

    def forward(
        self,
        hidden_states: np.ndarray,
        prefetch_next_experts: Optional[List[int]] = None,
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Forward pass with optional prefetching for next layer.

        Args:
            hidden_states: Input array of shape (batch, seq_len, hidden_size)
            prefetch_next_experts: Expert IDs to prefetch for the next layer

        Returns:
            Tuple of (output_array, stats_dict)
        """
        forward_start = time.perf_counter()

        # Handle 2D input (batch, hidden) or 3D (batch, seq, hidden)
        original_shape = hidden_states.shape
        if len(original_shape) == 2:
            hidden_states = hidden_states.reshape(original_shape[0], 1, original_shape[1])

        batch_size, seq_len, _ = hidden_states.shape

        # Route tokens to experts
        router_start = time.perf_counter()
        # Flatten for routing
        flat_states = hidden_states.reshape(-1, self.hidden_size)
        router_logits = flat_states @ self.router_weight.T
        routing_probs = softmax(router_logits, axis=-1)

        # Select top-k experts
        selected_experts = np.argpartition(-routing_probs, self.top_k, axis=-1)[:, :self.top_k]
        routing_weights = np.take_along_axis(routing_probs, selected_experts, axis=-1)
        routing_weights = routing_weights / routing_weights.sum(axis=-1, keepdims=True)

        router_time = time.perf_counter() - router_start

        # Get unique experts needed for this batch
        unique_experts = list(set(selected_experts.flatten().tolist()))

        # Schedule prefetch for next layer's experts if provided
        if prefetch_next_experts is not None:
            self.prefetch_experts(prefetch_next_experts)

        # Prefetch current batch's experts
        self.prefetch_experts(unique_experts)

        # Compute expert outputs
        compute_start = time.perf_counter()
        output = np.zeros_like(flat_states)
        prefetch_hits = 0
        prefetch_misses = 0

        for expert_id in unique_experts:
            # Get weights (from cache or load)
            def fallback_load():
                return self.get_expert_weights(expert_id)

            weights, was_hit = self.prefetcher.get_weights(expert_id, fallback_load)
            if was_hit:
                prefetch_hits += 1
            else:
                prefetch_misses += 1

            # Find tokens routed to this expert
            for k in range(self.top_k):
                mask = selected_experts[:, k] == expert_id
                if not mask.any():
                    continue

                token_indices = np.where(mask)[0]
                token_weights = routing_weights[token_indices, k:k+1]

                # Compute expert output for these tokens
                expert_input = flat_states[token_indices]
                expert_output = self.compute_with_weights(expert_input, weights)

                # Accumulate weighted output
                output[token_indices] += expert_output * token_weights

        compute_time = time.perf_counter() - compute_start
        total_time = time.perf_counter() - forward_start

        # Update stats
        self.timing_stats['router_time'] += router_time
        self.timing_stats['expert_compute_time'] += compute_time
        self.timing_stats['total_forward_time'] += total_time
        self.timing_stats['num_forwards'] += 1

        # Reshape output
        output = output.reshape(original_shape)

        stats = {
            'router_time': router_time,
            'compute_time': compute_time,
            'total_time': total_time,
            'prefetch_hits': prefetch_hits,
            'prefetch_misses': prefetch_misses,
            'selected_experts': selected_experts.reshape(batch_size, seq_len, self.top_k) if len(original_shape) == 3 else selected_experts,
            'routing_weights': routing_weights.reshape(batch_size, seq_len, self.top_k) if len(original_shape) == 3 else routing_weights,
            'unique_experts': unique_experts,
        }

        return output, stats

    def __call__(self, *args, **kwargs):
        return self.forward(*args, **kwargs)

    def get_stats(self) -> Dict[str, Any]:
        """Get accumulated statistics."""
        return {
            **self.timing_stats,
            **self.prefetcher.stats,
        }

    def reset_stats(self):
        """Reset all statistics."""
        self.timing_stats = {
            'router_time': 0.0,
            'expert_compute_time': 0.0,
            'total_forward_time': 0.0,
            'num_forwards': 0,
        }
        self.prefetcher.reset_stats()
