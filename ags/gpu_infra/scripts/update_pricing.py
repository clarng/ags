#!/usr/bin/env python3
"""
Script to fetch and update GPU pricing information from cloud providers.

Usage:
    python -m ags.gpu_infra.scripts.update_pricing [--output README.md]

This script fetches current pricing from provider APIs (where available)
and updates the pricing README with the latest information.
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from ags.gpu_infra.types import GPUType, ProviderInfo, PricingTier
from ags.gpu_infra.providers.lambda_labs import LambdaLabsProvider
from ags.gpu_infra.providers.runpod import RunPodProvider
from ags.gpu_infra.providers.vastai import VastAIProvider
from ags.gpu_infra.providers.coreweave import CoreWeaveProvider


# Known GPU specs (VRAM, TFLOPs FP16, etc.)
GPU_SPECS = {
    GPUType.H100: {"vram_gb": 80, "fp16_tflops": 1979, "memory_bandwidth_gbps": 3350, "tdp_watts": 700},
    GPUType.A100_80GB: {"vram_gb": 80, "fp16_tflops": 312, "memory_bandwidth_gbps": 2039, "tdp_watts": 400},
    GPUType.A100_40GB: {"vram_gb": 40, "fp16_tflops": 312, "memory_bandwidth_gbps": 1555, "tdp_watts": 400},
    GPUType.A10: {"vram_gb": 24, "fp16_tflops": 125, "memory_bandwidth_gbps": 600, "tdp_watts": 150},
    GPUType.RTX_4090: {"vram_gb": 24, "fp16_tflops": 330, "memory_bandwidth_gbps": 1008, "tdp_watts": 450},
    GPUType.RTX_3090: {"vram_gb": 24, "fp16_tflops": 142, "memory_bandwidth_gbps": 936, "tdp_watts": 350},
    GPUType.V100: {"vram_gb": 16, "fp16_tflops": 125, "memory_bandwidth_gbps": 900, "tdp_watts": 300},
    GPUType.L40S: {"vram_gb": 48, "fp16_tflops": 362, "memory_bandwidth_gbps": 864, "tdp_watts": 350},
}


def fetch_lambda_pricing() -> Optional[dict]:
    """Fetch current pricing from Lambda Labs API."""
    try:
        import requests
        resp = requests.get("https://cloud.lambdalabs.com/api/v1/instance-types", timeout=10)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        print(f"  Warning: Could not fetch Lambda Labs pricing: {e}")
    return None


def fetch_runpod_pricing() -> Optional[dict]:
    """Fetch current pricing from RunPod API."""
    try:
        import requests
        # RunPod has a public GPU types endpoint
        resp = requests.get("https://api.runpod.io/graphql",
                          json={"query": "{ gpuTypes { id displayName memoryInGb secureCloud communityCloud } }"},
                          timeout=10)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        print(f"  Warning: Could not fetch RunPod pricing: {e}")
    return None


def fetch_vastai_pricing() -> Optional[dict]:
    """Fetch current pricing from Vast.ai API."""
    try:
        import requests
        # Vast.ai search endpoint for current offers
        resp = requests.get("https://console.vast.ai/api/v0/bundles",
                          params={"q": json.dumps({"gpu_name": {"eq": "A100"}})},
                          timeout=10)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        print(f"  Warning: Could not fetch Vast.ai pricing: {e}")
    return None


def get_all_pricing_data() -> dict:
    """Collect pricing from all providers."""
    print("Fetching pricing data...")

    providers = {
        "lambda": LambdaLabsProvider(),
        "runpod": RunPodProvider(),
        "vastai": VastAIProvider(),
        "coreweave": CoreWeaveProvider(),
    }

    data = {
        "updated_at": datetime.utcnow().isoformat() + "Z",
        "providers": {},
        "gpu_specs": {k.value: v for k, v in GPU_SPECS.items()},
    }

    for name, provider in providers.items():
        print(f"  Processing {name}...")
        info = provider.info
        data["providers"][name] = {
            "name": info.name,
            "reliability_score": info.reliability_score,
            "supports_spot": info.supports_spot,
            "regions": info.regions,
            "min_billing_increment": info.min_billing_increment,
            "notes": info.notes,
            "pricing": [
                {
                    "gpu_type": tier.gpu_type.value,
                    "hourly_cost": tier.hourly_cost,
                    "spot_cost": tier.spot_cost,
                    "vcpus": tier.vcpus,
                    "ram_gb": tier.ram_gb,
                    "storage_gb": tier.storage_gb,
                }
                for tier in info.pricing
            ],
        }

    # Try to fetch live pricing
    print("  Fetching live pricing from APIs...")
    live_lambda = fetch_lambda_pricing()
    if live_lambda and "data" in live_lambda:
        data["live_pricing"] = {"lambda": live_lambda["data"]}

    return data


def generate_readme(data: dict) -> str:
    """Generate README markdown from pricing data."""

    updated = data.get("updated_at", "Unknown")

    lines = [
        "# GPU Cloud Infrastructure Pricing Guide",
        "",
        f"Last updated: {updated}",
        "",
        "This document compares GPU cloud providers for ML/AI workloads.",
        "Prices are approximate and may vary. Always check provider websites for current pricing.",
        "",
        "## Quick Comparison: A100 40GB",
        "",
        "| Provider | On-Demand $/hr | Spot $/hr | Reliability | vCPUs | RAM | Notes |",
        "|----------|----------------|-----------|-------------|-------|-----|-------|",
    ]

    # Sort by on-demand price for A100
    provider_a100_prices = []
    for pname, pdata in data["providers"].items():
        for tier in pdata["pricing"]:
            if tier["gpu_type"] == "a100_40gb":
                provider_a100_prices.append((pname, pdata, tier))
                break

    provider_a100_prices.sort(key=lambda x: x[2]["hourly_cost"])

    for pname, pdata, tier in provider_a100_prices:
        spot = f"${tier['spot_cost']:.2f}" if tier.get("spot_cost") else "N/A"
        lines.append(
            f"| {pdata['name']} | ${tier['hourly_cost']:.2f} | {spot} | "
            f"{pdata['reliability_score']}% | {tier['vcpus']} | {tier['ram_gb']}GB | "
            f"{pdata['notes'][:50]}{'...' if len(pdata['notes']) > 50 else ''} |"
        )

    lines.extend([
        "",
        "## Full Pricing by GPU Type",
        "",
    ])

    # Group by GPU type
    gpu_types = ["h100", "a100_80gb", "a100_40gb", "l40s", "a10", "rtx_4090", "rtx_3090", "v100"]

    for gpu_type in gpu_types:
        gpu_spec = data["gpu_specs"].get(gpu_type, {})

        lines.extend([
            f"### {gpu_type.upper().replace('_', ' ')}",
            "",
        ])

        if gpu_spec:
            lines.extend([
                f"- **VRAM:** {gpu_spec.get('vram_gb', 'N/A')} GB",
                f"- **FP16 Performance:** {gpu_spec.get('fp16_tflops', 'N/A')} TFLOPS",
                f"- **Memory Bandwidth:** {gpu_spec.get('memory_bandwidth_gbps', 'N/A')} GB/s",
                f"- **TDP:** {gpu_spec.get('tdp_watts', 'N/A')} W",
                "",
            ])

        lines.append("| Provider | On-Demand $/hr | Spot $/hr | vCPUs | RAM | Storage |")
        lines.append("|----------|----------------|-----------|-------|-----|---------|")

        has_pricing = False
        for pname, pdata in sorted(data["providers"].items()):
            for tier in pdata["pricing"]:
                if tier["gpu_type"] == gpu_type:
                    has_pricing = True
                    spot = f"${tier['spot_cost']:.2f}" if tier.get("spot_cost") else "N/A"
                    lines.append(
                        f"| {pdata['name']} | ${tier['hourly_cost']:.2f} | {spot} | "
                        f"{tier['vcpus']} | {tier['ram_gb']}GB | {tier['storage_gb']}GB |"
                    )
                    break

        if not has_pricing:
            lines.append("| *No providers currently offer this GPU* | - | - | - | - | - |")

        lines.append("")

    lines.extend([
        "## Provider Details",
        "",
    ])

    for pname, pdata in sorted(data["providers"].items(), key=lambda x: -x[1]["reliability_score"]):
        lines.extend([
            f"### {pdata['name']}",
            "",
            f"- **Reliability Score:** {pdata['reliability_score']}%",
            f"- **Spot Instances:** {'Yes' if pdata['supports_spot'] else 'No'}",
            f"- **Regions:** {', '.join(pdata['regions'])}",
            f"- **Min Billing:** {pdata['min_billing_increment']} seconds",
            f"- **Notes:** {pdata['notes']}",
            "",
        ])

    lines.extend([
        "## Cost Optimization Tips",
        "",
        "1. **Use spot instances** for fault-tolerant workloads (training with checkpoints)",
        "2. **Lambda Labs** offers best value for on-demand A100s when available",
        "3. **Vast.ai** has cheapest spot prices but variable reliability",
        "4. **CoreWeave** best for production workloads requiring high uptime",
        "5. **Consider H100** for large models - 2-3x faster than A100 for ~2x price",
        "",
        "## Updating This Document",
        "",
        "Run the update script to refresh pricing:",
        "",
        "```bash",
        "python -m ags.gpu_infra.scripts.update_pricing --output ags/gpu_infra/PRICING.md",
        "```",
        "",
        "Or fetch live pricing programmatically:",
        "",
        "```python",
        "from ags.gpu_infra import GPUInfraAnalyzer, GPUType",
        "",
        "analyzer = GPUInfraAnalyzer()",
        "print(analyzer.print_comparison_table(GPUType.A100_40GB))",
        "recs = analyzer.get_recommendations(GPUType.A100_40GB)",
        "```",
        "",
    ])

    return "\n".join(lines)


def save_pricing_json(data: dict, path: Path):
    """Save raw pricing data as JSON for programmatic access."""
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Saved pricing data to {path}")


def main():
    parser = argparse.ArgumentParser(description="Update GPU pricing information")
    parser.add_argument("--output", "-o", default="ags/gpu_infra/PRICING.md",
                       help="Output path for README")
    parser.add_argument("--json", "-j", default="ags/gpu_infra/pricing_data.json",
                       help="Output path for JSON data")
    parser.add_argument("--no-json", action="store_true",
                       help="Skip JSON output")
    args = parser.parse_args()

    # Get pricing data
    data = get_all_pricing_data()

    # Generate and save README
    readme = generate_readme(data)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        f.write(readme)
    print(f"Saved pricing README to {output_path}")

    # Save JSON data
    if not args.no_json:
        json_path = Path(args.json)
        save_pricing_json(data, json_path)

    print("\nDone!")


if __name__ == "__main__":
    main()
