"""
CoreWeave GPU Cloud provider implementation.

Note: CoreWeave uses Kubernetes for instance management.
This is a simplified implementation for basic operations.
"""

import os
import subprocess
import json
from typing import Optional

from .base import BaseProvider
from ..types import Instance, GPUType, ProviderInfo, PricingTier, InstanceStatus


class CoreWeaveProvider(BaseProvider):
    """CoreWeave GPU Cloud provider (Kubernetes-based)."""

    API_BASE = "https://api.coreweave.com"

    def __init__(self, api_key: Optional[str] = None, kubeconfig: Optional[str] = None):
        super().__init__(api_key)
        self.kubeconfig = kubeconfig or os.environ.get("COREWEAVE_KUBECONFIG")

    def _get_api_key_from_env(self) -> Optional[str]:
        return os.environ.get("COREWEAVE_API_KEY")

    @property
    def info(self) -> ProviderInfo:
        return ProviderInfo(
            name="CoreWeave",
            api_base_url=self.API_BASE,
            pricing=[
                PricingTier(gpu_type=GPUType.A100_80GB, hourly_cost=2.21, vcpus=16, ram_gb=128, storage_gb=256),
                PricingTier(gpu_type=GPUType.A100_40GB, hourly_cost=2.06, vcpus=16, ram_gb=128, storage_gb=256),
                PricingTier(gpu_type=GPUType.H100, hourly_cost=4.76, vcpus=24, ram_gb=180, storage_gb=256),
                PricingTier(gpu_type=GPUType.A10, hourly_cost=0.75, vcpus=8, ram_gb=32, storage_gb=128),
                PricingTier(gpu_type=GPUType.RTX_4090, hourly_cost=1.24, vcpus=8, ram_gb=32, storage_gb=128),
            ],
            reliability_score=95.0,
            regions=["ORD1", "LAS1", "LGA1"],
            supports_spot=True,
            min_billing_increment=60,
            notes="Enterprise-grade, best reliability. Uses Kubernetes. Higher prices but excellent support.",
        )

    def _kubectl(self, args: list[str]) -> tuple[int, str, str]:
        """Execute kubectl command."""
        cmd = ["kubectl"]
        if self.kubeconfig:
            cmd.extend(["--kubeconfig", self.kubeconfig])
        cmd.extend(args)

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return 1, "", "Command timed out"
        except FileNotFoundError:
            return 1, "", "kubectl not found"

    def _gpu_type_to_resource(self, gpu_type: GPUType) -> str:
        mapping = {
            GPUType.A100_40GB: "A100_PCIE_40GB",
            GPUType.A100_80GB: "A100_NVLINK_80GB",
            GPUType.H100: "H100_NVLINK_80GB",
            GPUType.A10: "A10",
            GPUType.RTX_4090: "RTX_4090",
        }
        return mapping.get(gpu_type, "A100_PCIE_40GB")

    def _parse_pod(self, pod: dict) -> Instance:
        metadata = pod.get("metadata", {})
        spec = pod.get("spec", {})
        status = pod.get("status", {})

        # Determine GPU type from resources
        containers = spec.get("containers", [{}])
        resources = containers[0].get("resources", {}).get("limits", {}) if containers else {}

        gpu_type = GPUType.A100_40GB
        for key in resources:
            if "nvidia.com" in key:
                if "A100_80" in key or "NVLINK" in key:
                    gpu_type = GPUType.A100_80GB
                elif "H100" in key:
                    gpu_type = GPUType.H100
                elif "A10" in key:
                    gpu_type = GPUType.A10
                break

        phase = status.get("phase", "").lower()
        status_map = {
            "running": InstanceStatus.RUNNING,
            "pending": InstanceStatus.PENDING,
            "succeeded": InstanceStatus.STOPPED,
            "failed": InstanceStatus.ERROR,
        }

        return Instance(
            id=metadata.get("name", ""),
            provider="coreweave",
            gpu_type=gpu_type,
            gpu_count=1,
            status=status_map.get(phase, InstanceStatus.RUNNING),
            ip_address=status.get("podIP"),
            ssh_port=22,
            ssh_user="root",
            hourly_cost=self.get_pricing(gpu_type) or 0.0,
            metadata=pod,
        )

    def list_instances(self) -> list[Instance]:
        if not self.kubeconfig:
            return []

        rc, stdout, _ = self._kubectl(["get", "pods", "-o", "json", "-l", "gpu-workload=true"])
        if rc != 0:
            return []

        try:
            data = json.loads(stdout)
            pods = data.get("items", [])
            return [self._parse_pod(pod) for pod in pods]
        except json.JSONDecodeError:
            return []

    def create_instance(
        self,
        gpu_type: GPUType,
        gpu_count: int = 1,
        region: Optional[str] = None,
        ssh_key_name: Optional[str] = None,
        name: Optional[str] = None,
    ) -> Instance:
        if not self.kubeconfig:
            raise ValueError("Kubeconfig required for CoreWeave")

        gpu_resource = self._gpu_type_to_resource(gpu_type)
        pod_name = name or f"gpu-workload-{gpu_type.value.replace('_', '-')}"

        pod_spec = {
            "apiVersion": "v1",
            "kind": "Pod",
            "metadata": {
                "name": pod_name,
                "labels": {"gpu-workload": "true"},
            },
            "spec": {
                "restartPolicy": "Never",
                "containers": [
                    {
                        "name": "main",
                        "image": "pytorch/pytorch:2.1.0-cuda11.8-cudnn8-devel",
                        "command": ["/bin/bash", "-c", "sleep infinity"],
                        "resources": {
                            "limits": {
                                f"nvidia.com/gpu.{gpu_resource}": str(gpu_count),
                            }
                        },
                    }
                ],
            },
        }

        if region:
            pod_spec["spec"]["nodeSelector"] = {"topology.kubernetes.io/region": region}

        # Write spec to temp file and apply
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(pod_spec, f)
            temp_path = f.name

        try:
            rc, stdout, stderr = self._kubectl(["apply", "-f", temp_path])
            if rc != 0:
                raise RuntimeError(f"Failed to create pod: {stderr}")

            # Get the created pod
            inst = self.get_instance(pod_name)
            if inst:
                return inst
            raise RuntimeError("Pod created but could not retrieve details")
        finally:
            os.unlink(temp_path)

    def terminate_instance(self, instance_id: str) -> bool:
        if not self.kubeconfig:
            return False
        rc, _, _ = self._kubectl(["delete", "pod", instance_id])
        return rc == 0

    def get_instance(self, instance_id: str) -> Optional[Instance]:
        if not self.kubeconfig:
            return None

        rc, stdout, _ = self._kubectl(["get", "pod", instance_id, "-o", "json"])
        if rc != 0:
            return None

        try:
            pod = json.loads(stdout)
            return self._parse_pod(pod)
        except json.JSONDecodeError:
            return None
