"""
RunPod GPU Cloud provider implementation.
"""

import os
import requests
from typing import Optional

from .base import BaseProvider
from ..types import Instance, GPUType, ProviderInfo, PricingTier, InstanceStatus


class RunPodProvider(BaseProvider):
    """RunPod GPU Cloud provider."""

    API_BASE = "https://api.runpod.io/graphql"

    def _get_api_key_from_env(self) -> Optional[str]:
        return os.environ.get("RUNPOD_API_KEY")

    @property
    def info(self) -> ProviderInfo:
        return ProviderInfo(
            name="RunPod",
            api_base_url=self.API_BASE,
            pricing=[
                PricingTier(gpu_type=GPUType.A100_80GB, hourly_cost=1.89, spot_price=0.89, vcpus=16, ram_gb=125, storage_gb=100),
                PricingTier(gpu_type=GPUType.A100_40GB, hourly_cost=1.64, spot_price=0.79, vcpus=16, ram_gb=125, storage_gb=100),
                PricingTier(gpu_type=GPUType.H100, hourly_cost=3.89, spot_price=2.39, vcpus=20, ram_gb=200, storage_gb=100),
                PricingTier(gpu_type=GPUType.RTX_4090, hourly_cost=0.74, spot_price=0.34, vcpus=16, ram_gb=62, storage_gb=100),
                PricingTier(gpu_type=GPUType.RTX_3090, hourly_cost=0.44, spot_price=0.19, vcpus=16, ram_gb=62, storage_gb=100),
            ],
            reliability_score=85.0,
            regions=["US", "EU", "CA"],
            supports_spot=True,
            min_billing_increment=1,  # Per-second billing
            notes="Great spot prices, community cloud option. Good for experimentation.",
        )

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def _gpu_type_to_id(self, gpu_type: GPUType) -> str:
        mapping = {
            GPUType.A100_40GB: "NVIDIA A100 40GB",
            GPUType.A100_80GB: "NVIDIA A100 80GB",
            GPUType.H100: "NVIDIA H100 80GB HBM3",
            GPUType.RTX_4090: "NVIDIA GeForce RTX 4090",
            GPUType.RTX_3090: "NVIDIA GeForce RTX 3090",
        }
        return mapping.get(gpu_type, "NVIDIA A100 40GB")

    def _graphql_request(self, query: str, variables: Optional[dict] = None) -> dict:
        if not self.api_key:
            raise ValueError("API key required")
        payload = {"query": query}
        if variables:
            payload["variables"] = variables
        resp = requests.post(self.API_BASE, headers=self._headers(), json=payload)
        resp.raise_for_status()
        return resp.json()

    def _parse_instance(self, data: dict) -> Instance:
        gpu_name = data.get("machine", {}).get("gpuDisplayName", "")
        gpu_type = GPUType.A100_40GB
        if "80GB" in gpu_name and "A100" in gpu_name:
            gpu_type = GPUType.A100_80GB
        elif "H100" in gpu_name:
            gpu_type = GPUType.H100
        elif "4090" in gpu_name:
            gpu_type = GPUType.RTX_4090
        elif "3090" in gpu_name:
            gpu_type = GPUType.RTX_3090

        status_map = {
            "RUNNING": InstanceStatus.RUNNING,
            "CREATED": InstanceStatus.PENDING,
            "EXITED": InstanceStatus.STOPPED,
        }

        runtime = data.get("runtime", {}) or {}

        return Instance(
            id=data["id"],
            provider="runpod",
            gpu_type=gpu_type,
            gpu_count=data.get("gpuCount", 1),
            status=status_map.get(data.get("desiredStatus", ""), InstanceStatus.RUNNING),
            ip_address=runtime.get("gpus", [{}])[0].get("publicIp") if runtime.get("gpus") else None,
            ssh_port=runtime.get("ports", [{}])[0].get("publicPort", 22) if runtime.get("ports") else 22,
            ssh_user="root",
            hourly_cost=self.get_pricing(gpu_type) or 0.0,
            metadata=data,
        )

    def list_instances(self) -> list[Instance]:
        query = """
        query {
            myself {
                pods {
                    id
                    name
                    desiredStatus
                    gpuCount
                    machine {
                        gpuDisplayName
                    }
                    runtime {
                        gpus {
                            publicIp
                        }
                        ports {
                            publicPort
                            privatePort
                        }
                    }
                }
            }
        }
        """
        try:
            result = self._graphql_request(query)
            pods = result.get("data", {}).get("myself", {}).get("pods", [])
            return [self._parse_instance(pod) for pod in pods]
        except (ValueError, requests.RequestException):
            return []

    def create_instance(
        self,
        gpu_type: GPUType,
        gpu_count: int = 1,
        region: Optional[str] = None,
        ssh_key_name: Optional[str] = None,
        name: Optional[str] = None,
        spot: bool = False,
    ) -> Instance:
        gpu_id = self._gpu_type_to_id(gpu_type)
        cloud_type = "COMMUNITY" if spot else "SECURE"

        query = """
        mutation ($input: PodFindAndDeployOnDemandInput!) {
            podFindAndDeployOnDemand(input: $input) {
                id
                name
                desiredStatus
                gpuCount
                machine {
                    gpuDisplayName
                }
            }
        }
        """

        variables = {
            "input": {
                "cloudType": cloud_type,
                "gpuCount": gpu_count,
                "gpuTypeId": gpu_id,
                "name": name or f"gpu-instance-{gpu_type.value}",
                "imageName": "runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel-ubuntu22.04",
                "dockerArgs": "",
                "volumeInGb": 50,
                "containerDiskInGb": 20,
                "minVcpuCount": 4,
                "minMemoryInGb": 16,
            }
        }

        result = self._graphql_request(query, variables)
        pod = result.get("data", {}).get("podFindAndDeployOnDemand")
        if not pod:
            raise RuntimeError(f"Failed to create instance: {result}")
        return self._parse_instance(pod)

    def terminate_instance(self, instance_id: str) -> bool:
        query = """
        mutation ($input: PodTerminateInput!) {
            podTerminate(input: $input)
        }
        """
        try:
            self._graphql_request(query, {"input": {"podId": instance_id}})
            return True
        except (ValueError, requests.RequestException):
            return False

    def get_instance(self, instance_id: str) -> Optional[Instance]:
        query = """
        query ($podId: String!) {
            pod(input: {podId: $podId}) {
                id
                name
                desiredStatus
                gpuCount
                machine {
                    gpuDisplayName
                }
                runtime {
                    gpus {
                        publicIp
                    }
                    ports {
                        publicPort
                        privatePort
                    }
                }
            }
        }
        """
        try:
            result = self._graphql_request(query, {"podId": instance_id})
            pod = result.get("data", {}).get("pod")
            if pod:
                return self._parse_instance(pod)
        except (ValueError, requests.RequestException):
            pass
        return None
