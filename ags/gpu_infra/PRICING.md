# GPU Cloud Infrastructure Pricing Guide

Last updated: 2026-01-28T05:45:09.189677Z

This document compares GPU cloud providers for ML/AI workloads.
Prices are approximate and may vary. Always check provider websites for current pricing.

## Quick Comparison: A100 40GB

| Provider | On-Demand $/hr | Spot $/hr | Reliability | vCPUs | RAM | Notes |
|----------|----------------|-----------|-------------|-------|-----|-------|
| Lambda Labs | $1.10 | N/A | 92.0% | 30 | 200GB | High reliability, good for production workloads. O... |
| Vast.ai | $1.20 | $0.55 | 75.0% | 16 | 128GB | Cheapest option, marketplace model. Variable relia... |
| RunPod | $1.64 | $0.79 | 85.0% | 16 | 125GB | Great spot prices, community cloud option. Good fo... |
| CoreWeave | $2.06 | N/A | 95.0% | 16 | 128GB | Enterprise-grade, best reliability. Uses Kubernete... |

## Full Pricing by GPU Type

### H100

- **VRAM:** 80 GB
- **FP16 Performance:** 1979 TFLOPS
- **Memory Bandwidth:** 3350 GB/s
- **TDP:** 700 W

| Provider | On-Demand $/hr | Spot $/hr | vCPUs | RAM | Storage |
|----------|----------------|-----------|-------|-----|---------|
| CoreWeave | $4.76 | N/A | 24 | 180GB | 256GB |
| Lambda Labs | $2.49 | N/A | 26 | 200GB | 512GB |
| RunPod | $3.89 | $2.39 | 20 | 200GB | 100GB |

### A100 80GB

- **VRAM:** 80 GB
- **FP16 Performance:** 312 TFLOPS
- **Memory Bandwidth:** 2039 GB/s
- **TDP:** 400 W

| Provider | On-Demand $/hr | Spot $/hr | vCPUs | RAM | Storage |
|----------|----------------|-----------|-------|-----|---------|
| CoreWeave | $2.21 | N/A | 16 | 128GB | 256GB |
| Lambda Labs | $1.29 | N/A | 30 | 200GB | 512GB |
| RunPod | $1.89 | $0.89 | 16 | 125GB | 100GB |
| Vast.ai | $1.50 | $0.70 | 16 | 128GB | 100GB |

### A100 40GB

- **VRAM:** 40 GB
- **FP16 Performance:** 312 TFLOPS
- **Memory Bandwidth:** 1555 GB/s
- **TDP:** 400 W

| Provider | On-Demand $/hr | Spot $/hr | vCPUs | RAM | Storage |
|----------|----------------|-----------|-------|-----|---------|
| CoreWeave | $2.06 | N/A | 16 | 128GB | 256GB |
| Lambda Labs | $1.10 | N/A | 30 | 200GB | 512GB |
| RunPod | $1.64 | $0.79 | 16 | 125GB | 100GB |
| Vast.ai | $1.20 | $0.55 | 16 | 128GB | 100GB |

### L40S

- **VRAM:** 48 GB
- **FP16 Performance:** 362 TFLOPS
- **Memory Bandwidth:** 864 GB/s
- **TDP:** 350 W

| Provider | On-Demand $/hr | Spot $/hr | vCPUs | RAM | Storage |
|----------|----------------|-----------|-------|-----|---------|
| *No providers currently offer this GPU* | - | - | - | - | - |

### A10

- **VRAM:** 24 GB
- **FP16 Performance:** 125 TFLOPS
- **Memory Bandwidth:** 600 GB/s
- **TDP:** 150 W

| Provider | On-Demand $/hr | Spot $/hr | vCPUs | RAM | Storage |
|----------|----------------|-----------|-------|-----|---------|
| CoreWeave | $0.75 | N/A | 8 | 32GB | 128GB |
| Lambda Labs | $0.60 | N/A | 30 | 200GB | 512GB |

### RTX 4090

- **VRAM:** 24 GB
- **FP16 Performance:** 330 TFLOPS
- **Memory Bandwidth:** 1008 GB/s
- **TDP:** 450 W

| Provider | On-Demand $/hr | Spot $/hr | vCPUs | RAM | Storage |
|----------|----------------|-----------|-------|-----|---------|
| CoreWeave | $1.24 | N/A | 8 | 32GB | 128GB |
| RunPod | $0.74 | $0.34 | 16 | 62GB | 100GB |
| Vast.ai | $0.45 | $0.25 | 16 | 64GB | 100GB |

### RTX 3090

- **VRAM:** 24 GB
- **FP16 Performance:** 142 TFLOPS
- **Memory Bandwidth:** 936 GB/s
- **TDP:** 350 W

| Provider | On-Demand $/hr | Spot $/hr | vCPUs | RAM | Storage |
|----------|----------------|-----------|-------|-----|---------|
| RunPod | $0.44 | $0.19 | 16 | 62GB | 100GB |
| Vast.ai | $0.25 | $0.12 | 16 | 64GB | 100GB |

### V100

- **VRAM:** 16 GB
- **FP16 Performance:** 125 TFLOPS
- **Memory Bandwidth:** 900 GB/s
- **TDP:** 300 W

| Provider | On-Demand $/hr | Spot $/hr | vCPUs | RAM | Storage |
|----------|----------------|-----------|-------|-----|---------|
| *No providers currently offer this GPU* | - | - | - | - | - |

## Provider Details

### CoreWeave

- **Reliability Score:** 95.0%
- **Spot Instances:** Yes
- **Regions:** ORD1, LAS1, LGA1
- **Min Billing:** 60 seconds
- **Notes:** Enterprise-grade, best reliability. Uses Kubernetes. Higher prices but excellent support.

### Lambda Labs

- **Reliability Score:** 92.0%
- **Spot Instances:** No
- **Regions:** us-west-1, us-east-1, us-south-1, europe-central-1
- **Min Billing:** 60 seconds
- **Notes:** High reliability, good for production workloads. Often has availability issues for A100s.

### RunPod

- **Reliability Score:** 85.0%
- **Spot Instances:** Yes
- **Regions:** US, EU, CA
- **Min Billing:** 1 seconds
- **Notes:** Great spot prices, community cloud option. Good for experimentation.

### Vast.ai

- **Reliability Score:** 75.0%
- **Spot Instances:** Yes
- **Regions:** US, EU, ASIA
- **Min Billing:** 60 seconds
- **Notes:** Cheapest option, marketplace model. Variable reliability depending on host.

## Cost Optimization Tips

1. **Use spot instances** for fault-tolerant workloads (training with checkpoints)
2. **Lambda Labs** offers best value for on-demand A100s when available
3. **Vast.ai** has cheapest spot prices but variable reliability
4. **CoreWeave** best for production workloads requiring high uptime
5. **Consider H100** for large models - 2-3x faster than A100 for ~2x price

## Updating This Document

Run the update script to refresh pricing:

```bash
python -m ags.gpu_infra.scripts.update_pricing --output ags/gpu_infra/PRICING.md
```

Or fetch live pricing programmatically:

```python
from ags.gpu_infra import GPUInfraAnalyzer, GPUType

analyzer = GPUInfraAnalyzer()
print(analyzer.print_comparison_table(GPUType.A100_40GB))
recs = analyzer.get_recommendations(GPUType.A100_40GB)
```
