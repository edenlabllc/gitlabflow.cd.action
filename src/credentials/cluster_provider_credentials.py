import json
import os

from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class AWSConfig:
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    AWS_REGION: str


@dataclass
class AzureConfig:
    AZURE_CLIENT_ID: str
    AZURE_CLIENT_SECRET: str
    AZURE_LOCATION: str
    AZURE_SUBSCRIPTION_ID: str
    AZURE_TENANT_ID: str


@dataclass
class GCPConfig:
    GOOGLE_APPLICATION_CREDENTIALS: str
    GCP_REGION: str


@dataclass
class ClusterProviders:
    aws: Optional[AWSConfig] = field(default=None)
    azure: Optional[AzureConfig] = field(default=None)
    gcp: Optional[GCPConfig] = field(default=None)


@dataclass
class EnvironmentConfig:
    cluster_providers: ClusterProviders


class Credentials:
    def __init__(self, json_data: str):
        self.environments: Dict[str, EnvironmentConfig] = self._parse_json(json_data)

    @staticmethod
    def _parse_json(json_data: str) -> Dict[str, EnvironmentConfig]:
        """Parses the JSON input and validates required fields."""
        try:
            data = json.loads(json_data)
            if not isinstance(data, dict):
                raise ValueError("Invalid JSON format: Expected a dictionary.")
        except json.JSONDecodeError as err:
            raise ValueError(f"Failed to parse JSON: {err}")

        environments = {}
        for env_name, env_data in data.items():
            try:
                cluster_providers = env_data.get("cluster_providers", {})

                environments[env_name] = EnvironmentConfig(
                    cluster_providers=ClusterProviders(
                        aws=AWSConfig(**cluster_providers["aws"]) if "aws" in cluster_providers else None,
                        azure=AzureConfig(**cluster_providers["azure"]) if "azure" in cluster_providers else None,
                        gcp=GCPConfig(**cluster_providers["gcp"]) if "gcp" in cluster_providers else None,
                    )
                )
            except TypeError as err:
                raise ValueError(f"Invalid structure for environment '{env_name}': {err}")

        return environments

    def get_environment(self, env_name: str) -> Optional[EnvironmentConfig]:
        return self.environments.get(env_name, None)

    def list_environments(self) -> list:
        return list(self.environments.keys())

    @staticmethod
    def save_gcp_credentials(credentials_content: str) -> str:
        """Save GCP credentials content to a file and return its path with validation."""
        if not credentials_content:
            raise ValueError("GCP credentials content is empty or invalid.")

        if isinstance(credentials_content, dict):
            credentials_json = credentials_content
        else:
            try:
                credentials_json = json.loads(json.dumps(credentials_content))
                if not isinstance(credentials_json, dict):
                    raise ValueError("Invalid GCP credentials format. Expected a JSON object.")
            except json.JSONDecodeError as err:
                raise ValueError(f"Failed to parse GCP credentials JSON: {err}")

        file_path = "gcp-credentials.json"
        try:
            with open(file_path, "w") as cred_file:
                json.dump(credentials_json, cred_file, indent=4)
        except IOError as err:
            raise IOError(f"Failed to write GCP credentials file: {err}")

        return os.path.abspath(file_path)

    def set_env_variables(self, env_name: str, provider: str):
        """Set environment variables based on the selected cluster provider."""
        env_config = self.get_environment(env_name)
        if not env_config:
            raise ValueError(f"Environment '{env_name}' not found in credentials values.")

        providers = env_config.cluster_providers

        match provider.lower():
            case "aws":
                os.environ.update({
                    "AWS_ACCESS_KEY_ID": providers.aws.AWS_ACCESS_KEY_ID,
                    "AWS_SECRET_ACCESS_KEY": providers.aws.AWS_SECRET_ACCESS_KEY,
                    "AWS_REGION": providers.aws.AWS_REGION,
                })
            case "azure":
                os.environ.update({
                    "AZURE_CLIENT_ID": providers.azure.AZURE_CLIENT_ID,
                    "AZURE_CLIENT_SECRET": providers.azure.AZURE_CLIENT_SECRET,
                    "AZURE_LOCATION": providers.azure.AZURE_LOCATION,
                    "AZURE_SUBSCRIPTION_ID": providers.azure.AZURE_SUBSCRIPTION_ID,
                    "AZURE_TENANT_ID": providers.azure.AZURE_TENANT_ID,
                })
            case "gcp":
                credentials_path = self.save_gcp_credentials(providers.gcp.GOOGLE_APPLICATION_CREDENTIALS)
                os.environ.update({
                    "GOOGLE_APPLICATION_CREDENTIALS": credentials_path,
                    "GCP_REGION": providers.gcp.GCP_REGION,
                })
            case _:
                raise ValueError(f"Invalid provider '{provider}'. Supported providers: aws, azure, gcp")

        print(f"Credentials as environment variables set for {env_name} with cluster provider: {provider}.")

    def __repr__(self):
        return f"Credentials(environments={self.environments})"
