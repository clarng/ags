"""
GPU Instance Manager - Manage instances across multiple providers.
"""

from typing import Optional
import json
import os
from pathlib import Path

from .types import Instance, GPUType, InstanceStatus
from .providers import PROVIDERS, BaseProvider


class GPUInstanceManager:
    """Unified manager for GPU instances across providers."""

    def __init__(self, config_dir: Optional[str] = None):
        self._providers: dict[str, BaseProvider] = {}
        self._config_dir = Path(config_dir or os.path.expanduser("~/.gpu_infra"))
        self._config_dir.mkdir(parents=True, exist_ok=True)
        self._instances_file = self._config_dir / "instances.json"
        self._load_providers()

    def _load_providers(self):
        """Initialize available providers."""
        for name, provider_class in PROVIDERS.items():
            try:
                self._providers[name] = provider_class()
            except Exception:
                pass

    def _save_instance_locally(self, instance: Instance):
        """Save instance info locally for tracking."""
        instances = self._load_local_instances()
        instances[f"{instance.provider}:{instance.id}"] = {
            "id": instance.id,
            "provider": instance.provider,
            "gpu_type": instance.gpu_type.value,
            "gpu_count": instance.gpu_count,
            "status": instance.status.value,
            "ip_address": instance.ip_address,
            "ssh_port": instance.ssh_port,
            "ssh_user": instance.ssh_user,
            "ssh_key_path": instance.ssh_key_path,
            "region": instance.region,
            "hourly_cost": instance.hourly_cost,
        }
        with open(self._instances_file, "w") as f:
            json.dump(instances, f, indent=2)

    def _load_local_instances(self) -> dict:
        """Load locally tracked instances."""
        if self._instances_file.exists():
            with open(self._instances_file) as f:
                return json.load(f)
        return {}

    def _remove_local_instance(self, provider: str, instance_id: str):
        """Remove instance from local tracking."""
        instances = self._load_local_instances()
        key = f"{provider}:{instance_id}"
        if key in instances:
            del instances[key]
            with open(self._instances_file, "w") as f:
                json.dump(instances, f, indent=2)

    def get_provider(self, name: str) -> Optional[BaseProvider]:
        """Get a specific provider."""
        return self._providers.get(name)

    def list_providers(self) -> list[str]:
        """List available providers."""
        return list(self._providers.keys())

    def list_instances(self, provider: Optional[str] = None) -> list[Instance]:
        """
        List all running instances, optionally filtered by provider.

        Args:
            provider: Optional provider name to filter by
        """
        instances = []

        if provider:
            if provider in self._providers:
                instances.extend(self._providers[provider].list_instances())
        else:
            for prov in self._providers.values():
                try:
                    instances.extend(prov.list_instances())
                except Exception:
                    pass

        return instances

    def create_instance(
        self,
        provider: str,
        gpu_type: GPUType,
        gpu_count: int = 1,
        region: Optional[str] = None,
        ssh_key_name: Optional[str] = None,
        ssh_key_path: Optional[str] = None,
        name: Optional[str] = None,
        **kwargs,
    ) -> Instance:
        """
        Create a new GPU instance.

        Args:
            provider: Provider name (lambda, runpod, vastai, coreweave)
            gpu_type: Type of GPU to provision
            gpu_count: Number of GPUs
            region: Optional region/zone
            ssh_key_name: Name of SSH key registered with provider
            ssh_key_path: Local path to SSH private key (for SSH command)
            name: Optional instance name
            **kwargs: Provider-specific options
        """
        if provider not in self._providers:
            raise ValueError(f"Unknown provider: {provider}. Available: {list(self._providers.keys())}")

        prov = self._providers[provider]
        instance = prov.create_instance(
            gpu_type=gpu_type,
            gpu_count=gpu_count,
            region=region,
            ssh_key_name=ssh_key_name,
            name=name,
            **kwargs,
        )

        # Set local SSH key path
        if ssh_key_path:
            instance.ssh_key_path = ssh_key_path

        # Track locally
        self._save_instance_locally(instance)

        return instance

    def terminate_instance(self, provider: str, instance_id: str) -> bool:
        """
        Terminate an instance.

        Args:
            provider: Provider name
            instance_id: Instance ID
        """
        if provider not in self._providers:
            return False

        success = self._providers[provider].terminate_instance(instance_id)
        if success:
            self._remove_local_instance(provider, instance_id)

        return success

    def get_instance(self, provider: str, instance_id: str) -> Optional[Instance]:
        """Get details of a specific instance."""
        if provider not in self._providers:
            return None
        return self._providers[provider].get_instance(instance_id)

    def refresh_instance(self, instance: Instance) -> Optional[Instance]:
        """Refresh instance status from provider."""
        return self.get_instance(instance.provider, instance.id)

    def set_ssh_key(self, provider: str, instance_id: str, ssh_key_path: str):
        """Set the SSH key path for an instance (for local tracking)."""
        instances = self._load_local_instances()
        key = f"{provider}:{instance_id}"
        if key in instances:
            instances[key]["ssh_key_path"] = ssh_key_path
            with open(self._instances_file, "w") as f:
                json.dump(instances, f, indent=2)

    def get_ssh_command(self, provider: str, instance_id: str) -> Optional[str]:
        """Get the SSH command for an instance."""
        # First try to get from local cache (has SSH key path)
        instances = self._load_local_instances()
        key = f"{provider}:{instance_id}"

        if key in instances:
            data = instances[key]
            if data.get("ip_address"):
                cmd = f"ssh -p {data.get('ssh_port', 22)}"
                if data.get("ssh_key_path"):
                    cmd += f" -i {data['ssh_key_path']}"
                cmd += f" {data.get('ssh_user', 'root')}@{data['ip_address']}"
                return cmd

        # Otherwise get from provider
        instance = self.get_instance(provider, instance_id)
        if instance:
            return instance.ssh_command()

        return None

    def wait_for_ready(
        self,
        provider: str,
        instance_id: str,
        timeout: int = 300,
        poll_interval: int = 10,
    ) -> Optional[Instance]:
        """
        Wait for an instance to be ready (running with IP).

        Args:
            provider: Provider name
            instance_id: Instance ID
            timeout: Maximum seconds to wait
            poll_interval: Seconds between status checks
        """
        import time

        start = time.time()

        while time.time() - start < timeout:
            instance = self.get_instance(provider, instance_id)
            if instance and instance.status == InstanceStatus.RUNNING and instance.ip_address:
                self._save_instance_locally(instance)
                return instance

            if instance and instance.status == InstanceStatus.ERROR:
                return instance

            time.sleep(poll_interval)

        return self.get_instance(provider, instance_id)
