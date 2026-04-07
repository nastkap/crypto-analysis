#!/usr/bin/env python3
"""
ECIES Multi-Architecture Docker Build & Push Tool
Builds images for linux/amd64 and linux/arm64 with CycloneDX SBOM
"""

import subprocess
import json
import sys
from pathlib import Path
from datetime import datetime
import argparse

class ECIESBuilder:
    DOCKERHUB_USER = "nastap"
    PLATFORMS = "linux/amd64,linux/arm64"
    SBOM_FORMAT = "cyclonedx"
    
    SERVICES = {
        "benchmark-controller": "controller",
        "node-py-crypto": "crypto",
        "node-py-pycryptodome": "pycryptodome",
        "node-cpp-openssl": "openssl",
        "node-cpp-cryptopp": "cryptopp",
    }
    
    def __init__(self, dry_run=False, push=False, no_cache=False):
        self.workspace = Path(__file__).parent
        self.dry_run = dry_run
        self.push = push
        self.no_cache = no_cache
        self.results = {"success": [], "failed": []}
    
    def run_cmd(self, cmd, description):
        """Wykonywanie komendy"""
        if self.dry_run:
            print(f"[DRY-RUN] {description}")
            print(f"  Command: {' '.join(cmd)}")
            return True
        
        try:
            print(f"▶ {description}")
            result = subprocess.run(
                cmd,
                capture_output=False,
                text=True,
                timeout=1800,
                env={**subprocess.os.environ, "PYTHONIOENCODING": "utf-8"}
            )
            
            if result.returncode == 0:
                print(f"  Success")
                return True
            else:
                print(f"  Failed with exit code {result.returncode}")
                return False
                
        except subprocess.TimeoutExpired:
            print(f"  Timeout")
            return False
        except Exception as e:
            print(f"  Error: {e}")
            return False
    
    def check_prerequisites(self):
        """Sprawdzenie wymagań"""
        print(" Checking prerequisites...\n")
        
        # Docker
        if not self.run_cmd(["docker", "--version"], "Checking Docker"):
            print("Docker not found!")
            return False
        
        # Buildx
        if not self.run_cmd(["docker", "buildx", "version"], "Checking docker buildx"):
            print("docker buildx may not be available")
        
        print()
        return True
    
    def build_image(self, service_name, repo_name):
        """Budowanie pojedynczego obrazu"""
        image = f"{self.DOCKERHUB_USER}/{repo_name}:latest"
        service_path = self.workspace / service_name
        
        print(f"\n Building: {service_name} → {image}")
        print("=" * 70)
        
        if not service_path.exists():
            print(f"✗ Service not found: {service_path}")
            return False
        
        # Build command
        cmd = [
            "docker", "buildx", "build",
            "--platform", self.PLATFORMS,
            "--tag", image,
            "--build-arg", f"BUILDKIT_SBOM_FORMAT={self.SBOM_FORMAT}",
        ]
        
        if self.no_cache:
            cmd.append("--no-cache")
        
        if self.push:
            cmd.append("--push")
        else:
            cmd.extend(["--output", "type=oci"])
        
        cmd.append(str(service_path))
        
        # Add metadata annotation
        timestamp = datetime.now().isoformat()
        cmd.insert(-1, "--label")
        cmd.insert(-1, f"org.opencontainers.image.created={timestamp}")
        cmd.insert(-1, "--label")
        cmd.insert(-1, f"org.opencontainers.image.source=https://github.com/")
        
        success = self.run_cmd(cmd, f"Building for {self.PLATFORMS}")
        
        if success:
            self.results["success"].append((service_name, repo_name))
            if self.push:
                print(f" Pushed to: https://hub.docker.com/r/{image}")
        else:
            self.results["failed"].append((service_name, repo_name))
        
        return success
    
    def build_all(self):
        """Budowanie wszystkich serwisów"""
        print("\n" + "="*70)
        print(" ECIES Multi-Architecture Docker Builder")
        print("="*70)
        print(f"DockerHub User: {self.DOCKERHUB_USER}")
        print(f"Platforms: {self.PLATFORMS}")
        print(f"SBOM Format: {self.SBOM_FORMAT}")
        print(f"Push: {'Yes' if self.push else 'No'}")
        print(f"No-Cache: {'Yes' if self.no_cache else 'No'}")
        print(f"Dry-Run: {'Yes' if self.dry_run else 'No'}")
        print("="*70)
        
        if not self.check_prerequisites():
            return False
        
        for service, repo in self.SERVICES.items():
            self.build_image(service, repo)
        
        self.print_summary()
        return len(self.results["failed"]) == 0
    
    def print_summary(self):
        """Podsumowanie"""
        print("\n" + "="*70)
        print(" BUILD SUMMARY")
        print("="*70)
        
        if self.results["success"]:
            print(f"\n Successful ({len(self.results['success'])}):")
            for service, repo in self.results["success"]:
                img = f"{self.DOCKERHUB_USER}/{repo}:latest"
                print(f"  • {service:30} → {img}")
        
        if self.results["failed"]:
            print(f"\n Failed ({len(self.results['failed'])}):")
            for service, repo in self.results["failed"]:
                img = f"{self.DOCKERHUB_USER}/{repo}:latest"
                print(f"  • {service:30} → {img}")
        
        print("\n" + "="*70)
        print(" View on DockerHub: https://hub.docker.com/u/nastap")
        print("="*70)


def main():
    parser = argparse.ArgumentParser(
        description="Build and push ECIES multi-arch Docker images"
    )
    parser.add_argument(
        "--push",
        action="store_true",
        help="Push images to DockerHub"
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Build without using cache"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show commands without executing"
    )
    
    args = parser.parse_args()
    
    builder = ECIESBuilder(dry_run=args.dry_run, push=args.push, no_cache=args.no_cache)
    success = builder.build_all()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
