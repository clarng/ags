"""
Lambda Labs GPU Cloud provider implementation.
"""

import os
import requests
from typing import Optional
from datetime import datetime

from .base import BaseProvider
from ..types import Instance, GPUType, ProviderInfo, PricingTier, InstanceStatus


class LambdaLabsProvider(BaseProvider):
    """Lambda Labs GPU Cloud provider."""

    API_BASE = "https://cloud.lambdalabs.com/api/v1"

    def _get_api_key_from_env(self) -> Optional[str]:
        return os.environ.get("LAMBDA_API_KEY")

    @property
    def info(self) -> ProviderInfo:
        return ProviderInfo(
            name="Lambda Labs",
            api_base_url=self.API_BASE,
            pricing=[
                PricingTier(gpu_type=GPUType.A100_40GB, hourly_cost=1.10, vcpus=30, ram_gb=200, storage_gb=512),
                PricingTier(gpu_type=GPUType.A100_80GB, hourly_cost=1.29, vcpus=30, ram_gb=200, storage_gb=512),
                PricingTier(gpu_type=GPUType.H100, hourly_cost=2.49, vcpus=26, ram_gb=200, storage_gb=512),
                PricingTier(gpu_type=GPUType.A10, hourly_cost=0.60, vcpus=30, ram_gb=200, storage_gb=512),
            ],
            reliability_score=92.0,
            regions=["us-west-1", "us-east-1", "us-south-1", "europe-central-1"],
            supports_spot=False,
            min_billing_increment=60,
            notes="High reliability, good for production workloads. Often has availability issues for A100s.",
        )

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}"}

    def _gpu_type_to_instance_type(self, gpu_type: GPUType) -> str:
        mapping = {
            GPUType.A100_40GB: "gpu_1x_a100",
            GPUType.A100_80GB: "gpu_1x_a100_sxm4",
            GPUType.H100: "gpu_1x_h100_pcie",
            GPUType.A10: "gpu_1x_a10",
        }
        return mapping.get(gpu_type, "gpu_1x_a100")

    def _parse_instance(self, data: dict) -> Instance:
        gpu_type = GPUType.A100_40GB  # default
        instance_type = data.get("instance_type", {})
        if "a100_sxm4" in instance_type.get("name", "").lower():
            gpu_type = GPUType.A100_80GB
        elif "h100" in instance_type.get("name", "").lower():
            gpu_type = GPUType.H100
        elif "a10" in instance_type.get("name", "").lower():
            gpu_type = GPUType.A10

        status_map = {
            "active": InstanceStatus.RUNNING,
            "booting": InstanceStatus.PENDING,
            "terminated": InstanceStatus.TERMINATED,
            "unhealthy": InstanceStatus.ERROR,
        }

        return Instance(
            id=data["id"],
            provider="lambda",
            gpu_type=gpu_type,
            gpu_count=instance_type.get("specs", {}).get("gpus", 1),
            status=status_map.get(data.get("status", ""), InstanceStatus.RUNNING),
            ip_address=data.get("ip"),
            ssh_port=22,
            ssh_user="ubuntu",
            region=data.get("region", {}).get("name", ""),
            hourly_cost=self.get_pricing(gpu_type) or 0.0,
            metadata=data,
        )

    def list_instances(self) -> list[Instance]:
        if not self.api_key:
            return []
        resp = requests.get(f"{self.API_BASE}/instances", headers=self._headers())
        resp.raise_for_status()
        data = resp.json().get("data", [])
        return [self._parse_instance(inst) for inst in data]

    def create_instance(
        self,
        gpu_type: GPUType,
        gpu_count: int = 1,
        region: Optional[str] = None,
        ssh_key_name: Optional[str] = None,
        name: Optional[str] = None,
    ) -> Instance:
        if not self.api_key:
            raise ValueError("API key required to create instance")

        instance_type = self._gpu_type_to_instance_type(gpu_type)
        if gpu_count > 1:
            instance_type = instance_type.replace("1x", f"{gpu_count}x")

        payload = {
            "instance_type_name": instance_type,
            "region_name": region or "us-west-1",
            "ssh_key_names": [ssh_key_name] if ssh_key_name else [],
            "quantity": 1,
        }
        if name:
            payload["name"] = name

        resp = requests.post(
            f"{self.API_BASE}/instance-operations/launch",
            headers=self._headers(),
            json=payload,
        )
        resp.raise_for_status()
        instance_ids = resp.json().get("data", {}).get("instance_ids", [])
        if not instance_ids:
            raise RuntimeError("No instance ID returned")

        # Fetch the created instance
        inst = self.get_instance(instance_ids[0])
        if inst:
            return inst
        raise RuntimeError("Failed to fetch created instance")

    def terminate_instance(self, instance_id: str) -> bool:
        if not self.api_key:
            return False
        resp = requests.post(
            f"{self.API_BASE}/instance-operations/terminate",
            headers=self._headers(),
            json={"instance_ids": [instance_id]},
        )
        return resp.status_code == 200

    def get_instance(self, instance_id: str) -> Optional[Instance]:
        if not self.api_key:
            return None
        resp = requests.get(f"{self.API_BASE}/instances/{instance_id}", headers=self._headers())
        if resp.status_code != 200:
            return None
        data = resp.json().get("data")
        if data:
            return self._parse_instance(data)
        return None

    def check_availability(self, gpu_type: GPUType, region: Optional[str] = None) -> bool:
        """Check if a GPU type is currently available."""
        if not self.api_key:
            return False
        resp = requests.get(f"{self.API_BASE}/instance-types", headers=self._headers())
        resp.raise_for_status()
        data = resp.json().get("data", {})
        instance_type = self._gpu_type_to_instance_type(gpu_type)
        type_info = data.get(instance_type, {})
        regions = type_info.get("regions_with_capacity_available", [])
        if region:
            return any(r.get("name") == region for r in regions)
        return len(regions) > 0
