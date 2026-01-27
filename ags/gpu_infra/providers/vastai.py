"""
Vast.ai GPU marketplace provider implementation.
"""

import os
import requests
from typing import Optional

from .base import BaseProvider
from ..types import Instance, GPUType, ProviderInfo, PricingTier, InstanceStatus


class VastAIProvider(BaseProvider):
    """Vast.ai GPU marketplace provider."""

    API_BASE = "https://console.vast.ai/api/v0"

    def _get_api_key_from_env(self) -> Optional[str]:
        return os.environ.get("VASTAI_API_KEY")

    @property
    def info(self) -> ProviderInfo:
        return ProviderInfo(
            name="Vast.ai",
            api_base_url=self.API_BASE,
            pricing=[
                # Prices are approximate market rates, actual prices vary
                PricingTier(gpu_type=GPUType.A100_80GB, hourly_cost=1.50, spot_price=0.70, vcpus=16, ram_gb=128, storage_gb=100),
                PricingTier(gpu_type=GPUType.A100_40GB, hourly_cost=1.20, spot_price=0.55, vcpus=16, ram_gb=128, storage_gb=100),
                PricingTier(gpu_type=GPUType.RTX_4090, hourly_cost=0.45, spot_price=0.25, vcpus=16, ram_gb=64, storage_gb=100),
                PricingTier(gpu_type=GPUType.RTX_3090, hourly_cost=0.25, spot_price=0.12, vcpus=16, ram_gb=64, storage_gb=100),
            ],
            reliability_score=75.0,
            regions=["US", "EU", "ASIA"],
            supports_spot=True,
            min_billing_increment=60,
            notes="Cheapest option, marketplace model. Variable reliability depending on host.",
        )

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}"}

    def _gpu_name_to_type(self, gpu_name: str) -> GPUType:
        gpu_name = gpu_name.lower()
        if "a100" in gpu_name and "80" in gpu_name:
            return GPUType.A100_80GB
        elif "a100" in gpu_name:
            return GPUType.A100_40GB
        elif "h100" in gpu_name:
            return GPUType.H100
        elif "4090" in gpu_name:
            return GPUType.RTX_4090
        elif "3090" in gpu_name:
            return GPUType.RTX_3090
        return GPUType.A100_40GB

    def _parse_instance(self, data: dict) -> Instance:
        gpu_name = data.get("gpu_name", "")
        gpu_type = self._gpu_name_to_type(gpu_name)

        status_map = {
            "running": InstanceStatus.RUNNING,
            "loading": InstanceStatus.PENDING,
            "exited": InstanceStatus.STOPPED,
        }

        return Instance(
            id=str(data.get("id", "")),
            provider="vastai",
            gpu_type=gpu_type,
            gpu_count=data.get("num_gpus", 1),
            status=status_map.get(data.get("actual_status", ""), InstanceStatus.RUNNING),
            ip_address=data.get("public_ipaddr"),
            ssh_port=data.get("ssh_port", 22),
            ssh_user="root",
            hourly_cost=data.get("dph_total", 0.0),
            metadata=data,
        )

    def list_instances(self) -> list[Instance]:
        if not self.api_key:
            return []
        try:
            resp = requests.get(f"{self.API_BASE}/instances", headers=self._headers())
            resp.raise_for_status()
            instances = resp.json().get("instances", [])
            return [self._parse_instance(inst) for inst in instances]
        except requests.RequestException:
            return []

    def search_offers(
        self,
        gpu_type: GPUType,
        min_gpu_count: int = 1,
        max_price: Optional[float] = None,
        verified_only: bool = True,
    ) -> list[dict]:
        """Search for available GPU offers on the marketplace."""
        if not self.api_key:
            return []

        gpu_name_map = {
            GPUType.A100_80GB: "A100_SXM4",
            GPUType.A100_40GB: "A100_PCIE",
            GPUType.H100: "H100",
            GPUType.RTX_4090: "RTX_4090",
            GPUType.RTX_3090: "RTX_3090",
        }

        query = {
            "gpu_name": gpu_name_map.get(gpu_type, "A100"),
            "num_gpus": {"gte": min_gpu_count},
            "rentable": True,
            "verified": {"eq": verified_only},
            "order": [["dph_total", "asc"]],
        }
        if max_price:
            query["dph_total"] = {"lte": max_price}

        try:
            resp = requests.get(
                f"{self.API_BASE}/bundles",
                headers=self._headers(),
                params={"q": str(query)},
            )
            resp.raise_for_status()
            return resp.json().get("offers", [])
        except requests.RequestException:
            return []

    def create_instance(
        self,
        gpu_type: GPUType,
        gpu_count: int = 1,
        region: Optional[str] = None,
        ssh_key_name: Optional[str] = None,
        name: Optional[str] = None,
        offer_id: Optional[int] = None,
    ) -> Instance:
        if not self.api_key:
            raise ValueError("API key required")

        # If no offer_id specified, find the cheapest one
        if not offer_id:
            offers = self.search_offers(gpu_type, min_gpu_count=gpu_count)
            if not offers:
                raise RuntimeError(f"No available offers for {gpu_type.value}")
            offer_id = offers[0]["id"]

        payload = {
            "client_id": "me",
            "image": "pytorch/pytorch:2.1.0-cuda11.8-cudnn8-devel",
            "disk": 50,
            "onstart": "#!/bin/bash\necho 'Instance started'",
        }

        resp = requests.put(
            f"{self.API_BASE}/asks/{offer_id}/",
            headers=self._headers(),
            json=payload,
        )
        resp.raise_for_status()
        result = resp.json()

        if not result.get("success"):
            raise RuntimeError(f"Failed to create instance: {result}")

        # Get the new instance
        new_id = result.get("new_contract")
        if new_id:
            inst = self.get_instance(str(new_id))
            if inst:
                return inst

        raise RuntimeError("Instance created but could not retrieve details")

    def terminate_instance(self, instance_id: str) -> bool:
        if not self.api_key:
            return False
        try:
            resp = requests.delete(
                f"{self.API_BASE}/instances/{instance_id}/",
                headers=self._headers(),
            )
            return resp.status_code == 200
        except requests.RequestException:
            return False

    def get_instance(self, instance_id: str) -> Optional[Instance]:
        if not self.api_key:
            return None
        try:
            resp = requests.get(
                f"{self.API_BASE}/instances/{instance_id}",
                headers=self._headers(),
            )
            if resp.status_code == 200:
                return self._parse_instance(resp.json())
        except requests.RequestException:
            pass
        return None
