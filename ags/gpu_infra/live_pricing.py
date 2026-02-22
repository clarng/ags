"""
Live pricing fetcher - scrapes provider APIs/pages for current GPU pricing.

Providers with public APIs (no auth needed):
  - Lambda Labs: /api/v1/instance-types
  - RunPod: GraphQL (gpuTypes query)
  - Vast.ai: /api/v0/bundles

CoreWeave requires auth, so we skip live fetch for it.
"""

import json
from typing import Optional

import requests

from .types import GPUType, PricingTier


# Map provider GPU names -> our GPUType enum
_LAMBDA_GPU_MAP = {
    "gpu_1x_a100": GPUType.A100_40GB,
    "gpu_1x_a100_sxm4": GPUType.A100_40GB,
    "gpu_1x_a100_80gb_sxm4": GPUType.A100_80GB,
    "gpu_1x_a10": GPUType.A10,
    "gpu_1x_h100_sxm5": GPUType.H100,
    "gpu_1x_h100_pcie": GPUType.H100,
}

_RUNPOD_GPU_MAP = {
    "NVIDIA A100 80GB": GPUType.A100_80GB,
    "NVIDIA A100-80GB": GPUType.A100_80GB,
    "NVIDIA A100 PCIE 40GB": GPUType.A100_40GB,
    "NVIDIA A100 40GB": GPUType.A100_40GB,
    "NVIDIA A100-40GB": GPUType.A100_40GB,
    "NVIDIA H100 80GB HBM3": GPUType.H100,
    "NVIDIA H100": GPUType.H100,
    "NVIDIA GeForce RTX 4090": GPUType.RTX_4090,
    "NVIDIA RTX 4090": GPUType.RTX_4090,
    "NVIDIA GeForce RTX 3090": GPUType.RTX_3090,
    "NVIDIA RTX 3090": GPUType.RTX_3090,
    "NVIDIA RTX A10": GPUType.A10,
    "NVIDIA L40S": GPUType.L40S,
}


def fetch_lambda_live() -> list[PricingTier]:
    """Fetch live pricing from Lambda Labs public API."""
    tiers = []
    try:
        resp = requests.get(
            "https://cloud.lambdalabs.com/api/v1/instance-types",
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json().get("data", {})

        for type_id, info in data.items():
            specs = info.get("instance_type", {}).get("specs", {})
            price = info.get("instance_type", {}).get("price_cents_per_hour")
            if price is None:
                continue

            # Try to map the GPU
            gpu_type = None
            for key, gtype in _LAMBDA_GPU_MAP.items():
                if key in type_id:
                    gpu_type = gtype
                    break
            if not gpu_type:
                continue

            hourly = price / 100.0
            vcpus = specs.get("vcpus", 0)
            ram = specs.get("memory_gib", 0)
            storage = specs.get("storage_gib", 0)

            tiers.append(PricingTier(
                gpu_type=gpu_type,
                hourly_cost=hourly,
                vcpus=vcpus,
                ram_gb=ram,
                storage_gb=storage,
            ))
    except Exception as e:
        print(f"  [lambda] live fetch failed: {e}")
    return tiers


def fetch_runpod_live() -> list[PricingTier]:
    """Fetch live pricing from RunPod public GraphQL API."""
    tiers = []
    query = """
    {
        gpuTypes {
            id
            displayName
            memoryInGb
            secureCloud
            communityCloud
            lowestPrice {
                minimumBidPrice
                uninterruptablePrice
            }
        }
    }
    """
    try:
        resp = requests.post(
            "https://api.runpod.io/graphql",
            json={"query": query},
            timeout=10,
        )
        resp.raise_for_status()
        gpu_types = resp.json().get("data", {}).get("gpuTypes", [])

        for gpu in gpu_types:
            name = gpu.get("displayName", "")
            gpu_type = None
            for key, gtype in _RUNPOD_GPU_MAP.items():
                if key.lower() in name.lower() or name.lower() in key.lower():
                    gpu_type = gtype
                    break
            if not gpu_type:
                continue

            lowest = gpu.get("lowestPrice", {}) or {}
            on_demand = lowest.get("uninterruptablePrice")
            spot = lowest.get("minimumBidPrice")
            if on_demand is None:
                # Try secureCloud pricing
                secure = gpu.get("secureCloud", {}) or {}
                on_demand = secure if isinstance(secure, (int, float)) else None
            if on_demand is None:
                continue

            vram = gpu.get("memoryInGb", 0)

            tiers.append(PricingTier(
                gpu_type=gpu_type,
                hourly_cost=float(on_demand),
                spot_cost=float(spot) if spot else None,
                vcpus=16,
                ram_gb=vram * 4,  # rough estimate
                storage_gb=100,
            ))
    except Exception as e:
        print(f"  [runpod] live fetch failed: {e}")
    return tiers


def fetch_vastai_live() -> list[PricingTier]:
    """Fetch live pricing from Vast.ai public API (median of current offers)."""
    tiers = []
    gpu_queries = [
        ("A100", GPUType.A100_40GB),
        ("A100_80GB", GPUType.A100_80GB),
        ("RTX 4090", GPUType.RTX_4090),
        ("RTX 3090", GPUType.RTX_3090),
        ("H100", GPUType.H100),
    ]

    for gpu_name, gpu_type in gpu_queries:
        try:
            resp = requests.get(
                "https://console.vast.ai/api/v0/bundles",
                params={"q": json.dumps({
                    "gpu_name": {"eq": gpu_name},
                    "rentable": {"eq": True},
                    "num_gpus": {"eq": 1},
                })},
                timeout=10,
            )
            resp.raise_for_status()
            offers = resp.json().get("offers", [])
            if not offers:
                continue

            # Get median price
            prices = sorted(o.get("dph_total", 0) for o in offers if o.get("dph_total"))
            if not prices:
                continue
            median_price = prices[len(prices) // 2]

            # Spot prices (interruptible)
            spot_prices = sorted(
                o.get("min_bid", 0) for o in offers
                if o.get("min_bid") and o["min_bid"] > 0
            )
            spot_median = spot_prices[len(spot_prices) // 2] if spot_prices else None

            tiers.append(PricingTier(
                gpu_type=gpu_type,
                hourly_cost=round(median_price, 2),
                spot_cost=round(spot_median, 2) if spot_median else None,
                vcpus=16,
                ram_gb=128,
                storage_gb=100,
            ))
        except Exception as e:
            print(f"  [vastai/{gpu_name}] live fetch failed: {e}")

    return tiers


def fetch_all_live(verbose: bool = True) -> dict[str, list[PricingTier]]:
    """
    Fetch live pricing from all providers that have public APIs.

    Returns dict of provider_name -> list[PricingTier].
    """
    results = {}

    if verbose:
        print("Fetching live pricing...")

    if verbose:
        print("  [lambda] fetching...")
    lam = fetch_lambda_live()
    if lam:
        results["lambda"] = lam
        if verbose:
            print(f"  [lambda] got {len(lam)} GPU types")

    if verbose:
        print("  [runpod] fetching...")
    rp = fetch_runpod_live()
    if rp:
        results["runpod"] = rp
        if verbose:
            print(f"  [runpod] got {len(rp)} GPU types")

    if verbose:
        print("  [vastai] fetching...")
    va = fetch_vastai_live()
    if va:
        results["vastai"] = va
        if verbose:
            print(f"  [vastai] got {len(va)} GPU types")

    if verbose and not results:
        print("  No live data fetched, using cached pricing.")

    return results
