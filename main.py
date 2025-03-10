#!/usr/bin/env python3

import os
import sys

from src.actions.actions import RMKCLIExecutor
from src.actions.init_project import ProjectInitializer, GETTenant
from src.credentials.cluster_provider_credentials import Credentials
from src.input_output.input import ArgumentParser
from src.select_environment.allowed_environments import AllowEnvironments
from src.select_environment.select_environment import EnvironmentSelector, ExtendedEnvironmentSelector
from src.utils.github_environment_variables import GitHubContext
from src.utils.install_rmk import RMKInstaller

if __name__ == "__main__":
    try:
        """Parse command-line arguments"""
        args = ArgumentParser().parse_args()

        """Retrieve GitHub Action environment variables"""
        github_context = GitHubContext.from_env()
        print(f"Current branch: {github_context.ref_name}")

        """Determine the project environment based on the repository branch"""
        environment = ExtendedEnvironmentSelector().select_environment(github_context.ref_name)
        print(f"Current environment: {environment}")

        """Validate environment-specific constraints"""
        AllowEnvironments(args, environment).validate()

        """Retrieve cloud provider credentials"""
        Credentials(args.cluster_provider_credentials).set_env_variables(environment, args.rmk_cluster_provider)

        """Install RMK"""
        RMKInstaller(args)

        """Initialize the project"""
        ProjectInitializer(environment).configure_rmk_init(args)
        tenant = GETTenant(environment).execute()

        """Execute the RMK command"""
        RMKCLIExecutor(github_context, args, environment, tenant).execute()
    except Exception as err:
        print(f"Error: {err}", file=sys.stderr)
        sys.exit(1)
