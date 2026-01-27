"""
Base provider class for GPU cloud providers.
"""

from abc import ABC, abstractmethod
from typing import Optional
import os

from ..types import Instance, GPUType, ProviderInfo, InstanceStatus


class BaseProvider(ABC):
    """Abstract base class for GPU cloud providers."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or self._get_api_key_from_env()

    @abstractmethod
    def _get_api_key_from_env(self) -> Optional[str]:
        """Get API key from environment variable."""
        pass

    @property
    @abstractmethod
    def info(self) -> ProviderInfo:
        """Return provider information including pricing and reliability."""
        pass

    @abstractmethod
    def list_instances(self) -> list[Instance]:
        """List all running instances."""
        pass

    @abstractmethod
    def create_instance(
        self,
        gpu_type: GPUType,
        gpu_count: int = 1,
        region: Optional[str] = None,
        ssh_key_name: Optional[str] = None,
        name: Optional[str] = None,
    ) -> Instance:
        """Create a new GPU instance."""
        pass

    @abstractmethod
    def terminate_instance(self, instance_id: str) -> bool:
        """Terminate an instance. Returns True if successful."""
        pass

    @abstractmethod
    def get_instance(self, instance_id: str) -> Optional[Instance]:
        """Get details of a specific instance."""
        pass

    def get_available_gpus(self) -> list[GPUType]:
        """Get list of available GPU types from this provider."""
        return [tier.gpu_type for tier in self.info.pricing]

    def get_pricing(self, gpu_type: GPUType) -> Optional[float]:
        """Get hourly price for a GPU type."""
        for tier in self.info.pricing:
            if tier.gpu_type == gpu_type:
                return tier.hourly_cost
        return None
