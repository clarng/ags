#!/usr/bin/env python3
"""
GPU Infrastructure CLI - Command line tool for managing GPU instances.

Usage:
    gpu-infra compare [--gpu=<type>]
    gpu-infra recommend [--gpu=<type>]
    gpu-infra list [--provider=<name>]
    gpu-infra create <provider> [--gpu=<type>] [--count=<n>] [--region=<region>] [--name=<name>] [--ssh-key=<name>] [--ssh-key-path=<path>]
    gpu-infra terminate <provider> <instance_id>
    gpu-infra ssh <provider> <instance_id> [--key=<path>]
    gpu-infra status <provider> <instance_id>
    gpu-infra providers
    gpu-infra prices [--gpu=<type>]
"""

import argparse
import os
import subprocess
import sys

from .types import GPUType, InstanceStatus
from .manager import GPUInstanceManager
from .analyzer import GPUInfraAnalyzer


def parse_gpu_type(gpu_str: str) -> GPUType:
    """Parse GPU type from string."""
    mapping = {
        "a100": GPUType.A100_40GB,
        "a100-40": GPUType.A100_40GB,
        "a100_40gb": GPUType.A100_40GB,
        "a100-80": GPUType.A100_80GB,
        "a100_80gb": GPUType.A100_80GB,
        "h100": GPUType.H100,
        "a10": GPUType.A10,
        "4090": GPUType.RTX_4090,
        "rtx4090": GPUType.RTX_4090,
        "rtx_4090": GPUType.RTX_4090,
        "3090": GPUType.RTX_3090,
        "rtx3090": GPUType.RTX_3090,
        "rtx_3090": GPUType.RTX_3090,
        "v100": GPUType.V100,
    }
    return mapping.get(gpu_str.lower(), GPUType.A100_40GB)


def cmd_compare(args):
    """Compare providers for a GPU type."""
    analyzer = GPUInfraAnalyzer()
    gpu_type = parse_gpu_type(args.gpu) if args.gpu else GPUType.A100_40GB
    print(analyzer.print_comparison_table(gpu_type))


def cmd_recommend(args):
    """Get recommendations for different use cases."""
    analyzer = GPUInfraAnalyzer()
    gpu_type = parse_gpu_type(args.gpu) if args.gpu else GPUType.A100_40GB
    recs = analyzer.get_recommendations(gpu_type)

    print(f"\n{'='*60}")
    print(f"Recommendations for {gpu_type.value.upper()}")
    print(f"{'='*60}\n")

    for use_case, rec in recs.items():
        if use_case == "gpu_type":
            continue
        if rec:
            label = use_case.replace("for_", "").replace("_", " ").title()
            print(f"{label}:")
            print(f"  Provider: {rec['provider']}")
            print(f"  Reason:   {rec['reason']}")
            print(f"  Cost:     ${rec['cost']:.2f}/hr")
            print()


def cmd_list(args):
    """List running instances."""
    manager = GPUInstanceManager()
    instances = manager.list_instances(provider=args.provider)

    if not instances:
        print("No running instances found.")
        return

    print(f"\n{'ID':<25} {'Provider':<12} {'GPU':<15} {'Status':<10} {'IP':<15} {'$/hr':<8}")
    print("-" * 90)

    for inst in instances:
        print(
            f"{inst.id:<25} "
            f"{inst.provider:<12} "
            f"{inst.gpu_type.value:<15} "
            f"{inst.status.value:<10} "
            f"{inst.ip_address or 'pending':<15} "
            f"${inst.hourly_cost:.2f}"
        )


def cmd_create(args):
    """Create a new GPU instance."""
    manager = GPUInstanceManager()
    gpu_type = parse_gpu_type(args.gpu) if args.gpu else GPUType.A100_40GB

    print(f"Creating {gpu_type.value} instance on {args.provider}...")

    try:
        instance = manager.create_instance(
            provider=args.provider,
            gpu_type=gpu_type,
            gpu_count=args.count,
            region=args.region,
            ssh_key_name=args.ssh_key,
            ssh_key_path=args.ssh_key_path,
            name=args.name,
        )

        print(f"\nInstance created!")
        print(f"  ID:       {instance.id}")
        print(f"  Provider: {instance.provider}")
        print(f"  GPU:      {instance.gpu_type.value} x{instance.gpu_count}")
        print(f"  Status:   {instance.status.value}")
        print(f"  Cost:     ${instance.hourly_cost:.2f}/hr")

        if instance.ip_address:
            print(f"  IP:       {instance.ip_address}")
            print(f"\nSSH command:")
            print(f"  {instance.ssh_command()}")
        else:
            print("\nInstance is starting. Use 'gpu-infra status' to check when ready.")

    except Exception as e:
        print(f"Error creating instance: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_terminate(args):
    """Terminate an instance."""
    manager = GPUInstanceManager()

    print(f"Terminating {args.instance_id} on {args.provider}...")

    if manager.terminate_instance(args.provider, args.instance_id):
        print("Instance terminated successfully.")
    else:
        print("Failed to terminate instance.", file=sys.stderr)
        sys.exit(1)


def cmd_ssh(args):
    """SSH into an instance."""
    manager = GPUInstanceManager()

    # Get instance details
    instance = manager.get_instance(args.provider, args.instance_id)

    if not instance:
        print(f"Instance {args.instance_id} not found.", file=sys.stderr)
        sys.exit(1)

    if instance.status != InstanceStatus.RUNNING:
        print(f"Instance is not running (status: {instance.status.value})", file=sys.stderr)
        sys.exit(1)

    if not instance.ip_address:
        print("Instance does not have an IP address yet.", file=sys.stderr)
        sys.exit(1)

    # Build SSH command
    ssh_cmd = ["ssh", "-p", str(instance.ssh_port)]

    # Use provided key or try to get from local cache
    key_path = args.key
    if not key_path:
        # Try to get from local cache
        cmd_str = manager.get_ssh_command(args.provider, args.instance_id)
        if cmd_str and "-i " in cmd_str:
            key_path = cmd_str.split("-i ")[1].split()[0]

    if key_path:
        ssh_cmd.extend(["-i", key_path])

    ssh_cmd.append(f"{instance.ssh_user}@{instance.ip_address}")

    print(f"Connecting to {instance.ip_address}...")
    print(f"Command: {' '.join(ssh_cmd)}\n")

    # Execute SSH
    os.execvp("ssh", ssh_cmd)


def cmd_status(args):
    """Get status of an instance."""
    manager = GPUInstanceManager()
    instance = manager.get_instance(args.provider, args.instance_id)

    if not instance:
        print(f"Instance {args.instance_id} not found.", file=sys.stderr)
        sys.exit(1)

    print(f"\nInstance: {instance.id}")
    print(f"  Provider:   {instance.provider}")
    print(f"  GPU:        {instance.gpu_type.value} x{instance.gpu_count}")
    print(f"  Status:     {instance.status.value}")
    print(f"  IP:         {instance.ip_address or 'pending'}")
    print(f"  SSH Port:   {instance.ssh_port}")
    print(f"  SSH User:   {instance.ssh_user}")
    print(f"  Cost:       ${instance.hourly_cost:.2f}/hr")

    if instance.ip_address and instance.status == InstanceStatus.RUNNING:
        print(f"\nSSH command:")
        print(f"  {instance.ssh_command()}")


def cmd_providers(args):
    """List available providers."""
    analyzer = GPUInfraAnalyzer()
    providers = analyzer.get_all_providers()

    print(f"\n{'Provider':<15} {'Reliability':<12} {'Spot':<6} {'Regions':<30}")
    print("-" * 70)

    for prov in providers:
        regions = ", ".join(prov.regions[:3])
        if len(prov.regions) > 3:
            regions += f" +{len(prov.regions) - 3}"

        print(
            f"{prov.name:<15} "
            f"{prov.reliability_score:<12.1f} "
            f"{'Yes' if prov.supports_spot else 'No':<6} "
            f"{regions:<30}"
        )

    print("\nNotes:")
    for prov in providers:
        if prov.notes:
            print(f"  {prov.name}: {prov.notes}")


def cmd_prices(args):
    """Show prices for all providers."""
    analyzer = GPUInfraAnalyzer()

    if args.gpu:
        gpu_types = [parse_gpu_type(args.gpu)]
    else:
        gpu_types = [GPUType.A100_40GB, GPUType.A100_80GB, GPUType.H100]

    for gpu_type in gpu_types:
        print(analyzer.print_comparison_table(gpu_type))


def main():
    parser = argparse.ArgumentParser(
        description="GPU Infrastructure CLI - Manage GPU cloud instances",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Compare command
    compare_parser = subparsers.add_parser("compare", help="Compare providers")
    compare_parser.add_argument("--gpu", "-g", help="GPU type (e.g., a100, h100, 4090)")

    # Recommend command
    rec_parser = subparsers.add_parser("recommend", help="Get recommendations")
    rec_parser.add_argument("--gpu", "-g", help="GPU type")

    # List command
    list_parser = subparsers.add_parser("list", help="List instances")
    list_parser.add_argument("--provider", "-p", help="Filter by provider")

    # Create command
    create_parser = subparsers.add_parser("create", help="Create instance")
    create_parser.add_argument("provider", help="Provider name")
    create_parser.add_argument("--gpu", "-g", default="a100", help="GPU type")
    create_parser.add_argument("--count", "-c", type=int, default=1, help="Number of GPUs")
    create_parser.add_argument("--region", "-r", help="Region")
    create_parser.add_argument("--name", "-n", help="Instance name")
    create_parser.add_argument("--ssh-key", help="SSH key name (registered with provider)")
    create_parser.add_argument("--ssh-key-path", help="Local SSH private key path")

    # Terminate command
    term_parser = subparsers.add_parser("terminate", help="Terminate instance")
    term_parser.add_argument("provider", help="Provider name")
    term_parser.add_argument("instance_id", help="Instance ID")

    # SSH command
    ssh_parser = subparsers.add_parser("ssh", help="SSH into instance")
    ssh_parser.add_argument("provider", help="Provider name")
    ssh_parser.add_argument("instance_id", help="Instance ID")
    ssh_parser.add_argument("--key", "-k", help="SSH private key path")

    # Status command
    status_parser = subparsers.add_parser("status", help="Get instance status")
    status_parser.add_argument("provider", help="Provider name")
    status_parser.add_argument("instance_id", help="Instance ID")

    # Providers command
    subparsers.add_parser("providers", help="List providers")

    # Prices command
    prices_parser = subparsers.add_parser("prices", help="Show prices")
    prices_parser.add_argument("--gpu", "-g", help="GPU type")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "compare": cmd_compare,
        "recommend": cmd_recommend,
        "list": cmd_list,
        "create": cmd_create,
        "terminate": cmd_terminate,
        "ssh": cmd_ssh,
        "status": cmd_status,
        "providers": cmd_providers,
        "prices": cmd_prices,
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
