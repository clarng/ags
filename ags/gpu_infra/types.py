"""
Type definitions for GPU infrastructure management.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from datetime import datetime


class GPUType(Enum):
    """Supported GPU types."""
    A100_40GB = "a100_40gb"
    A100_80GB = "a100_80gb"
    H100 = "h100"
    H200 = "h200"
    A10 = "a10"
    L40S = "l40s"
    RTX_4090 = "rtx_4090"
    RTX_3090 = "rtx_3090"
    V100 = "v100"


class InstanceStatus(Enum):
    """Instance status."""
    PENDING = "pending"
    RUNNING = "running"
    STOPPED = "stopped"
    TERMINATED = "terminated"
    ERROR = "error"


@dataclass
class PricingTier:
    """Pricing information for a GPU instance type."""
    gpu_type: GPUType
    hourly_cost: float  # USD per hour
    gpu_count: int = 1
    vcpus: int = 8
    ram_gb: int = 64
    storage_gb: int = 100
    spot_cost: Optional[float] = None  # Spot/preemptible price if available


@dataclass
class ProviderInfo:
    """Information about a GPU cloud provider."""
    name: str
    api_base_url: str
    pricing: list[PricingTier]
    reliability_score: float  # 0-100, based on uptime and availability
    regions: list[str]
    supports_spot: bool = False
    min_billing_increment: int = 60  # seconds
    notes: str = ""


@dataclass
class Instance:
    """Represents a GPU instance."""
    id: str
    provider: str
    gpu_type: GPUType
    gpu_count: int
    status: InstanceStatus
    ip_address: Optional[str] = None
    ssh_port: int = 22
    ssh_user: str = "root"
    ssh_key_path: Optional[str] = None
    region: str = ""
    hourly_cost: float = 0.0
    created_at: Optional[datetime] = None
    metadata: dict = field(default_factory=dict)

    def ssh_command(self) -> str:
        """Generate SSH command for this instance."""
        if not self.ip_address:
            raise ValueError("Instance has no IP address")

        cmd = f"ssh -p {self.ssh_port}"
        if self.ssh_key_path:
            cmd += f" -i {self.ssh_key_path}"
        cmd += f" {self.ssh_user}@{self.ip_address}"
        return cmd
