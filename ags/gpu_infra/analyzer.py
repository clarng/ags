"""
GPU Infrastructure Analyzer - Compare costs and reliability across providers.
"""

from dataclasses import dataclass
from typing import Optional

from .types import GPUType, ProviderInfo, PricingTier
from .providers import PROVIDERS


@dataclass
class ProviderComparison:
    """Comparison result for a specific GPU type across providers."""
    gpu_type: GPUType
    comparisons: list[dict]  # List of {provider, hourly_cost, spot_price, reliability, score}
    best_cost: str  # Provider name
    best_reliability: str  # Provider name
    best_overall: str  # Provider name (balanced score)


@dataclass
class CostEstimate:
    """Cost estimate for running GPU instances."""
    provider: str
    gpu_type: GPUType
    gpu_count: int
    hours: float
    on_demand_cost: float
    spot_cost: Optional[float]
    monthly_on_demand: float
    monthly_spot: Optional[float]


class GPUInfraAnalyzer:
    """Analyze and compare GPU infrastructure across providers."""

    def __init__(self):
        self._providers: dict[str, ProviderInfo] = {}
        self._load_provider_info()

    def _load_provider_info(self):
        """Load provider info from all providers."""
        for name, provider_class in PROVIDERS.items():
            try:
                provider = provider_class()
                self._providers[name] = provider.info
            except Exception:
                pass

    def get_all_providers(self) -> list[ProviderInfo]:
        """Get information about all providers."""
        return list(self._providers.values())

    def get_provider(self, name: str) -> Optional[ProviderInfo]:
        """Get information about a specific provider."""
        return self._providers.get(name)

    def find_cheapest(
        self,
        gpu_type: GPUType,
        include_spot: bool = True,
    ) -> list[tuple[str, float, bool]]:
        """
        Find the cheapest providers for a GPU type.
        Returns list of (provider_name, price, is_spot) sorted by price.
        """
        results = []

        for name, info in self._providers.items():
            for tier in info.pricing:
                if tier.gpu_type == gpu_type:
                    results.append((name, tier.hourly_cost, False))
                    if include_spot and tier.spot_price:
                        results.append((name, tier.spot_price, True))
                    break

        return sorted(results, key=lambda x: x[1])

    def compare_providers(
        self,
        gpu_type: GPUType,
        weight_cost: float = 0.5,
        weight_reliability: float = 0.5,
    ) -> ProviderComparison:
        """
        Compare all providers for a specific GPU type.

        Args:
            gpu_type: The GPU type to compare
            weight_cost: Weight for cost in scoring (0-1)
            weight_reliability: Weight for reliability in scoring (0-1)
        """
        comparisons = []
        min_cost = float("inf")
        max_reliability = 0.0
        best_cost_provider = ""
        best_reliability_provider = ""

        # First pass: collect data and find mins/maxes
        for name, info in self._providers.items():
            for tier in info.pricing:
                if tier.gpu_type == gpu_type:
                    cost = tier.hourly_cost
                    if cost < min_cost:
                        min_cost = cost
                        best_cost_provider = name
                    if info.reliability_score > max_reliability:
                        max_reliability = info.reliability_score
                        best_reliability_provider = name

                    comparisons.append({
                        "provider": name,
                        "provider_name": info.name,
                        "hourly_cost": tier.hourly_cost,
                        "spot_price": tier.spot_price,
                        "reliability": info.reliability_score,
                        "vcpus": tier.vcpus,
                        "ram_gb": tier.ram_gb,
                        "supports_spot": info.supports_spot,
                        "regions": info.regions,
                        "notes": info.notes,
                    })
                    break

        if not comparisons:
            return ProviderComparison(
                gpu_type=gpu_type,
                comparisons=[],
                best_cost="",
                best_reliability="",
                best_overall="",
            )

        # Second pass: calculate normalized scores
        max_cost = max(c["hourly_cost"] for c in comparisons)
        cost_range = max_cost - min_cost if max_cost != min_cost else 1
        reliability_range = max_reliability - min(c["reliability"] for c in comparisons)
        reliability_range = reliability_range if reliability_range > 0 else 1

        best_score = -1
        best_overall = ""

        for comp in comparisons:
            # Normalize cost (lower is better, so invert)
            cost_score = 1 - (comp["hourly_cost"] - min_cost) / cost_range
            # Normalize reliability
            rel_score = comp["reliability"] / 100

            # Combined score
            comp["cost_score"] = cost_score
            comp["reliability_score_normalized"] = rel_score
            comp["overall_score"] = weight_cost * cost_score + weight_reliability * rel_score

            if comp["overall_score"] > best_score:
                best_score = comp["overall_score"]
                best_overall = comp["provider"]

        # Sort by overall score
        comparisons.sort(key=lambda x: x["overall_score"], reverse=True)

        return ProviderComparison(
            gpu_type=gpu_type,
            comparisons=comparisons,
            best_cost=best_cost_provider,
            best_reliability=best_reliability_provider,
            best_overall=best_overall,
        )

    def estimate_cost(
        self,
        provider: str,
        gpu_type: GPUType,
        gpu_count: int = 1,
        hours: float = 1.0,
    ) -> Optional[CostEstimate]:
        """Estimate the cost of running instances."""
        info = self._providers.get(provider)
        if not info:
            return None

        for tier in info.pricing:
            if tier.gpu_type == gpu_type:
                on_demand = tier.hourly_cost * gpu_count * hours
                spot = tier.spot_price * gpu_count * hours if tier.spot_price else None

                return CostEstimate(
                    provider=provider,
                    gpu_type=gpu_type,
                    gpu_count=gpu_count,
                    hours=hours,
                    on_demand_cost=on_demand,
                    spot_cost=spot,
                    monthly_on_demand=on_demand * 730 / hours,  # ~730 hours/month
                    monthly_spot=spot * 730 / hours if spot else None,
                )

        return None

    def print_comparison_table(self, gpu_type: GPUType) -> str:
        """Generate a formatted comparison table."""
        comparison = self.compare_providers(gpu_type)

        if not comparison.comparisons:
            return f"No providers found offering {gpu_type.value}"

        lines = []
        lines.append(f"\n{'='*80}")
        lines.append(f"GPU Type: {gpu_type.value.upper()}")
        lines.append(f"{'='*80}\n")

        # Header
        lines.append(f"{'Provider':<15} {'$/hr':<10} {'Spot $/hr':<12} {'Reliability':<12} {'Score':<10}")
        lines.append("-" * 70)

        for comp in comparison.comparisons:
            spot_str = f"${comp['spot_price']:.2f}" if comp['spot_price'] else "N/A"
            lines.append(
                f"{comp['provider_name']:<15} "
                f"${comp['hourly_cost']:<9.2f} "
                f"{spot_str:<12} "
                f"{comp['reliability']:<12.1f} "
                f"{comp['overall_score']:.2f}"
            )

        lines.append("")
        lines.append(f"Best for Cost:       {comparison.best_cost}")
        lines.append(f"Best for Reliability: {comparison.best_reliability}")
        lines.append(f"Best Overall:        {comparison.best_overall}")

        return "\n".join(lines)

    def get_recommendations(self, gpu_type: GPUType = GPUType.A100_40GB) -> dict:
        """Get recommendations for different use cases."""
        comparison = self.compare_providers(gpu_type)

        recommendations = {
            "gpu_type": gpu_type.value,
            "for_production": None,
            "for_experimentation": None,
            "for_budget": None,
            "for_spot_workloads": None,
        }

        if not comparison.comparisons:
            return recommendations

        # Production: highest reliability
        for_prod = max(comparison.comparisons, key=lambda x: x["reliability"])
        recommendations["for_production"] = {
            "provider": for_prod["provider"],
            "reason": f"Highest reliability ({for_prod['reliability']}%)",
            "cost": for_prod["hourly_cost"],
        }

        # Budget: lowest cost
        for_budget = min(comparison.comparisons, key=lambda x: x["hourly_cost"])
        recommendations["for_budget"] = {
            "provider": for_budget["provider"],
            "reason": f"Lowest on-demand price (${for_budget['hourly_cost']}/hr)",
            "cost": for_budget["hourly_cost"],
        }

        # Experimentation: best balance
        recommendations["for_experimentation"] = {
            "provider": comparison.best_overall,
            "reason": "Best balance of cost and reliability",
            "cost": next(
                c["hourly_cost"]
                for c in comparison.comparisons
                if c["provider"] == comparison.best_overall
            ),
        }

        # Spot workloads: cheapest spot price
        spot_options = [c for c in comparison.comparisons if c["spot_price"]]
        if spot_options:
            for_spot = min(spot_options, key=lambda x: x["spot_price"])
            recommendations["for_spot_workloads"] = {
                "provider": for_spot["provider"],
                "reason": f"Cheapest spot price (${for_spot['spot_price']}/hr)",
                "cost": for_spot["spot_price"],
            }

        return recommendations
