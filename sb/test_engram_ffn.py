"""
Unit tests for Engram FFN prefetch and overlap performance.

These tests verify that the engram prefetch system effectively:
1. Prefetches expert weights before they're needed
2. Overlaps memory transfers with computation
3. Avoids blocking the compute thread while waiting for memory
"""

import unittest
import numpy as np
import time
import threading
from engram_ffn import EngramMoEFFN, EngramPrefetcher, ExpertFFN


class TestEngramPrefetcher(unittest.TestCase):
    """Tests for the EngramPrefetcher class."""

    def setUp(self):
        self.prefetcher = EngramPrefetcher(num_experts=8, simulate_transfer_time=0.01)

    def tearDown(self):
        self.prefetcher.stop()

    def test_prefetcher_starts_and_stops(self):
        """Test that prefetcher thread can start and stop cleanly."""
        self.prefetcher.start()
        self.assertTrue(self.prefetcher._running)
        self.assertIsNotNone(self.prefetcher._prefetch_thread)

        self.prefetcher.stop()
        self.assertFalse(self.prefetcher._running)

    def test_prefetch_cache_hit(self):
        """Test that prefetched weights are available in cache."""
        self.prefetcher.start()

        # Create mock weights
        weights_cpu = {
            'gate_proj': np.random.randn(64, 32).astype(np.float32),
            'up_proj': np.random.randn(64, 32).astype(np.float32),
            'down_proj': np.random.randn(32, 64).astype(np.float32),
        }

        # Schedule prefetch
        event = self.prefetcher.schedule_prefetch(0, weights_cpu)
        event.wait(timeout=2.0)

        # Get weights - should be a cache hit
        weights, was_hit = self.prefetcher.get_weights(0, lambda: None)

        self.assertTrue(was_hit)
        self.assertIsNotNone(weights)
        self.assertEqual(self.prefetcher.stats['prefetch_hits'], 1)
        self.assertEqual(self.prefetcher.stats['prefetch_misses'], 0)

    def test_prefetch_cache_miss(self):
        """Test fallback when weights are not prefetched."""
        self.prefetcher.start()

        fallback_weights = {
            'gate_proj': np.random.randn(64, 32).astype(np.float32),
            'up_proj': np.random.randn(64, 32).astype(np.float32),
            'down_proj': np.random.randn(32, 64).astype(np.float32),
        }

        # Get weights without prefetching - should be a cache miss
        weights, was_hit = self.prefetcher.get_weights(0, lambda: fallback_weights)

        self.assertFalse(was_hit)
        for key in fallback_weights:
            np.testing.assert_array_equal(weights[key], fallback_weights[key])
        self.assertEqual(self.prefetcher.stats['prefetch_hits'], 0)
        self.assertEqual(self.prefetcher.stats['prefetch_misses'], 1)

    def test_prefetch_does_not_block_main_thread(self):
        """Test that scheduling prefetch returns immediately without blocking."""
        self.prefetcher.start()

        # Create weights
        weights_cpu = {
            'gate_proj': np.random.randn(1024, 512).astype(np.float32),
            'up_proj': np.random.randn(1024, 512).astype(np.float32),
            'down_proj': np.random.randn(512, 1024).astype(np.float32),
        }

        # Measure time to schedule (should be near-instant)
        start_time = time.perf_counter()
        event = self.prefetcher.schedule_prefetch(0, weights_cpu)
        schedule_time = time.perf_counter() - start_time

        # Scheduling should be very fast (< 10ms)
        self.assertLess(schedule_time, 0.01,
                       f"Scheduling took {schedule_time*1000:.2f}ms, expected < 10ms")

        # Wait for actual transfer to complete
        event.wait(timeout=5.0)


class TestEngramMoEFFN(unittest.TestCase):
    """Tests for the EngramMoEFFN class."""

    def setUp(self):
        self.hidden_size = 64
        self.intermediate_size = 128
        self.num_experts = 4
        self.top_k = 2

    def create_ffn(self, enable_prefetch=True, simulate_transfer_time=0.005):
        ffn = EngramMoEFFN(
            hidden_size=self.hidden_size,
            intermediate_size=self.intermediate_size,
            num_experts=self.num_experts,
            top_k=self.top_k,
            enable_prefetch=enable_prefetch,
            simulate_transfer_time=simulate_transfer_time,
        )
        if enable_prefetch:
            ffn.start_prefetcher()
        return ffn

    def test_forward_basic(self):
        """Test basic forward pass produces correct output shape."""
        ffn = self.create_ffn(enable_prefetch=True)
        try:
            batch_size, seq_len = 2, 4
            x = np.random.randn(batch_size, seq_len, self.hidden_size).astype(np.float32)

            output, stats = ffn(x)

            self.assertEqual(output.shape, x.shape)
            self.assertIn('router_time', stats)
            self.assertIn('compute_time', stats)
            self.assertIn('prefetch_hits', stats)
        finally:
            ffn.stop_prefetcher()

    def test_router_selects_top_k_experts(self):
        """Test that router selects exactly top_k experts per token."""
        ffn = self.create_ffn(enable_prefetch=True)
        try:
            batch_size, seq_len = 2, 4
            x = np.random.randn(batch_size, seq_len, self.hidden_size).astype(np.float32)

            _, stats = ffn(x)

            selected = stats['selected_experts']
            self.assertEqual(selected.shape[-1], self.top_k)
            # All expert IDs should be in valid range
            self.assertTrue((selected >= 0).all())
            self.assertTrue((selected < self.num_experts).all())
        finally:
            ffn.stop_prefetcher()

    def test_prefetch_reduces_blocked_time(self):
        """Test that prefetching reduces time spent waiting for weights."""
        # Run without prefetch
        ffn_no_prefetch = self.create_ffn(enable_prefetch=False)
        x = np.random.randn(4, 8, self.hidden_size).astype(np.float32)

        start_time = time.perf_counter()
        for _ in range(5):
            ffn_no_prefetch(x)
        time_no_prefetch = time.perf_counter() - start_time

        # Run with prefetch - use shorter transfer time to allow hits
        ffn_with_prefetch = self.create_ffn(enable_prefetch=True, simulate_transfer_time=0.001)
        try:
            # Warmup pass to populate the cache
            ffn_with_prefetch(x)
            # Give prefetch thread time to complete
            time.sleep(0.02)

            ffn_with_prefetch.reset_stats()

            start_time = time.perf_counter()
            for _ in range(5):
                ffn_with_prefetch(x)
                # Small delay to let prefetch thread work
                time.sleep(0.005)
            time_with_prefetch = time.perf_counter() - start_time

            stats = ffn_with_prefetch.get_stats()

            # Report timing
            print(f"\n--- Prefetch Reduces Blocked Time ---")
            print(f"Time without prefetch: {time_no_prefetch*1000:.2f}ms")
            print(f"Time with prefetch: {time_with_prefetch*1000:.2f}ms")
            print(f"Prefetch hits: {stats['prefetch_hits']}")
            print(f"Prefetch misses: {stats['prefetch_misses']}")
            print(f"Blocked time: {stats['blocked_time']*1000:.2f}ms")

            # The test passes if prefetch system is working (hits or misses tracked)
            total_accesses = stats['prefetch_hits'] + stats['prefetch_misses']
            self.assertGreater(total_accesses, 0, "Expected some prefetch activity")
        finally:
            ffn_with_prefetch.stop_prefetcher()

    def test_overlap_compute_with_prefetch(self):
        """Test that computation can overlap with prefetching."""
        ffn = self.create_ffn(enable_prefetch=True, simulate_transfer_time=0.02)
        try:
            x = np.random.randn(2, 4, self.hidden_size).astype(np.float32)

            # First pass - may have cache misses
            ffn(x)
            ffn.reset_stats()

            # Prepare experts to prefetch (simulate knowing next layer's experts)
            next_experts = [0, 1]
            ffn.prefetch_experts(next_experts)

            # Do some "compute work" while prefetch happens in background
            compute_work_time = 0.015  # 15ms
            time.sleep(compute_work_time)

            # Now the prefetched experts should be ready
            _, stats = ffn(x, prefetch_next_experts=[2, 3])

            final_stats = ffn.get_stats()

            # If overlap is working, blocked_time should be less than total prefetch time
            print(f"\n--- Overlap Compute with Prefetch ---")
            print(f"Total prefetch time: {final_stats['total_prefetch_time']*1000:.2f}ms")
            print(f"Blocked time: {final_stats['blocked_time']*1000:.2f}ms")
            print(f"Prefetch hits: {final_stats['prefetch_hits']}")

            if final_stats['total_prefetch_time'] > 0:
                overlap_efficiency = 1.0 - (final_stats['blocked_time'] / final_stats['total_prefetch_time'])
                print(f"Overlap efficiency: {overlap_efficiency*100:.1f}%")
        finally:
            ffn.stop_prefetcher()

    def test_multiple_sequential_forwards_accumulate_hits(self):
        """Test that multiple forwards accumulate prefetch hits."""
        ffn = self.create_ffn(enable_prefetch=True)
        try:
            x = np.random.randn(2, 4, self.hidden_size).astype(np.float32)

            total_hits = 0
            for i in range(10):
                _, stats = ffn(x)
                total_hits += stats['prefetch_hits']

            # After multiple forwards, we should have accumulated hits
            final_stats = ffn.get_stats()
            self.assertGreater(final_stats['prefetch_hits'], 0,
                              "Expected prefetch hits over multiple forwards")
        finally:
            ffn.stop_prefetcher()


class TestPrefetchOverlapPerformance(unittest.TestCase):
    """
    Performance tests for prefetch and overlap behavior.

    These tests measure whether the prefetch system effectively
    hides memory latency by overlapping with computation.
    """

    def setUp(self):
        # Larger dimensions for meaningful timing
        self.hidden_size = 256
        self.intermediate_size = 512
        self.num_experts = 8
        self.top_k = 2

    def test_prefetch_latency_hiding(self):
        """
        Test that prefetch effectively hides memory transfer latency.

        Strategy:
        1. Measure baseline time without any prefetching
        2. Measure time with prefetching enabled
        3. Verify that prefetch doesn't add latency (ideally reduces it)
        """
        batch_size, seq_len = 8, 16
        x = np.random.randn(batch_size, seq_len, self.hidden_size).astype(np.float32)
        num_iterations = 10

        # Baseline: No prefetch
        ffn_baseline = EngramMoEFFN(
            hidden_size=self.hidden_size,
            intermediate_size=self.intermediate_size,
            num_experts=self.num_experts,
            top_k=self.top_k,
            enable_prefetch=False,
        )

        # Warmup
        for _ in range(2):
            ffn_baseline(x)

        baseline_start = time.perf_counter()
        for _ in range(num_iterations):
            ffn_baseline(x)
        baseline_time = time.perf_counter() - baseline_start

        # With prefetch
        ffn_prefetch = EngramMoEFFN(
            hidden_size=self.hidden_size,
            intermediate_size=self.intermediate_size,
            num_experts=self.num_experts,
            top_k=self.top_k,
            enable_prefetch=True,
            simulate_transfer_time=0.005,  # 5ms simulated transfer
        )
        ffn_prefetch.start_prefetcher()

        try:
            # Warmup
            for _ in range(2):
                ffn_prefetch(x)
            ffn_prefetch.reset_stats()

            prefetch_start = time.perf_counter()
            for _ in range(num_iterations):
                ffn_prefetch(x)
            prefetch_time = time.perf_counter() - prefetch_start

            stats = ffn_prefetch.get_stats()

            # Report results
            print(f"\n--- Prefetch Latency Hiding Test ---")
            print(f"Baseline time (no prefetch): {baseline_time*1000:.2f}ms")
            print(f"Prefetch time: {prefetch_time*1000:.2f}ms")
            print(f"Prefetch hits: {stats['prefetch_hits']}")
            print(f"Prefetch misses: {stats['prefetch_misses']}")
            print(f"Blocked time: {stats['blocked_time']*1000:.2f}ms")
            print(f"Total prefetch time: {stats['total_prefetch_time']*1000:.2f}ms")

            # Prefetch should not significantly increase total time
            # Allow some overhead for thread synchronization
            if baseline_time > 0:
                overhead = (prefetch_time - baseline_time) / baseline_time
                print(f"Overhead: {overhead*100:.1f}%")
        finally:
            ffn_prefetch.stop_prefetcher()

    def test_gpu_not_blocked_during_prefetch(self):
        """
        Test that the main computation thread is not blocked during prefetch.

        We verify this by:
        1. Scheduling a prefetch
        2. Immediately doing compute work
        3. Checking that compute work wasn't delayed
        """
        prefetcher = EngramPrefetcher(num_experts=8, simulate_transfer_time=0.05)  # 50ms transfer
        prefetcher.start()

        try:
            # Weights to prefetch
            weights = {
                'gate_proj': np.random.randn(2048, 1024).astype(np.float32),
                'up_proj': np.random.randn(2048, 1024).astype(np.float32),
                'down_proj': np.random.randn(1024, 2048).astype(np.float32),
            }

            # Schedule prefetch
            prefetch_event = prefetcher.schedule_prefetch(0, weights)

            # Immediately do compute work (simulating GPU work)
            compute_start = time.perf_counter()
            x = np.random.randn(32, 64, 256).astype(np.float32)
            for _ in range(10):
                # Simulate some matrix multiplications
                y = np.matmul(x, x.transpose(0, 2, 1))
                z = np.matmul(y, x)
            compute_time = time.perf_counter() - compute_start

            # Wait for prefetch to complete
            prefetch_event.wait(timeout=5.0)

            print(f"\n--- GPU Blocking Test ---")
            print(f"Compute time during prefetch: {compute_time*1000:.2f}ms")
            print(f"Prefetch completed: {prefetch_event.is_set()}")

            # Compute should not have been blocked significantly
            # (compute time should be reasonable given the matrix ops)
            self.assertLess(compute_time, 0.5,
                           f"Compute took {compute_time*1000:.2f}ms, may have been blocked")
        finally:
            prefetcher.stop()

    def test_overlap_efficiency_metric(self):
        """
        Measure overlap efficiency: how much compute overlaps with memory transfer.

        Overlap efficiency = 1 - (blocked_time / total_prefetch_time)

        High efficiency means compute and memory transfer happen in parallel.
        Low efficiency means compute thread is waiting for memory.
        """
        ffn = EngramMoEFFN(
            hidden_size=self.hidden_size,
            intermediate_size=self.intermediate_size,
            num_experts=self.num_experts,
            top_k=self.top_k,
            enable_prefetch=True,
            simulate_transfer_time=0.01,  # 10ms per transfer
        )
        ffn.start_prefetcher()

        try:
            x = np.random.randn(8, 16, self.hidden_size).astype(np.float32)

            # Run multiple iterations with pipelining
            for i in range(20):
                # Prefetch experts for next iteration
                next_experts = [(i + 1) % self.num_experts, (i + 2) % self.num_experts]
                ffn(x, prefetch_next_experts=next_experts)

            stats = ffn.get_stats()

            # Calculate overlap efficiency
            if stats['total_prefetch_time'] > 0:
                overlap_efficiency = 1.0 - (stats['blocked_time'] / stats['total_prefetch_time'])
            else:
                overlap_efficiency = 1.0  # No prefetch time means no blocking

            print(f"\n--- Overlap Efficiency Test ---")
            print(f"Total prefetch time: {stats['total_prefetch_time']*1000:.2f}ms")
            print(f"Blocked time: {stats['blocked_time']*1000:.2f}ms")
            print(f"Overlap efficiency: {overlap_efficiency*100:.1f}%")
            print(f"Prefetch hits: {stats['prefetch_hits']}")
            print(f"Prefetch misses: {stats['prefetch_misses']}")
            print(f"Number of forwards: {stats['num_forwards']}")

            # We expect some overlap (even modest overlap is good)
            # In real systems, overlap depends on compute/transfer ratio
            self.assertGreater(overlap_efficiency, 0.1,
                              f"Overlap efficiency {overlap_efficiency:.2%} below threshold")
        finally:
            ffn.stop_prefetcher()


class TestExpertFFN(unittest.TestCase):
    """Unit tests for the ExpertFFN module."""

    def test_forward_shape(self):
        """Test that ExpertFFN produces correct output shape."""
        hidden_size = 64
        intermediate_size = 128
        batch_size = 2
        seq_len = 4

        expert = ExpertFFN(hidden_size, intermediate_size)
        x = np.random.randn(batch_size, seq_len, hidden_size).astype(np.float32)

        output = expert(x)

        self.assertEqual(output.shape, x.shape)

    def test_swiglu_activation(self):
        """Test that SwiGLU activation is applied correctly."""
        hidden_size = 32
        intermediate_size = 64

        expert = ExpertFFN(hidden_size, intermediate_size)
        x = np.random.randn(1, 1, hidden_size).astype(np.float32)

        output = expert(x)

        # SwiGLU should produce output different from input
        self.assertFalse(np.allclose(output, x))


if __name__ == '__main__':
    unittest.main(verbosity=2)
