#!/usr/bin/env python3

import sys

from github_actions.common import AllowEnvironments
from github_actions.common import Credentials
from github_actions.common import ExtendedEnvironmentSelector
from github_actions.common import GitHubContext
from github_actions.common import ProjectInitializer, GETTenant
from github_actions.common import RMKInstaller

from src.actions.actions import RMKCLIExecutor
from src.input_output.input import GitLabflowCDArgumentParser

if __name__ == "__main__":
    try:
        """Parse command-line arguments"""
        args = GitLabflowCDArgumentParser().parse_args()

        """Retrieve GitHub Action environment variables"""
        github_context = GitHubContext.from_env(
            github_custom_ref=args.github_custom_ref,
            github_custom_ref_name=args.github_custom_ref_name)

        """Determine the project environment based on the repository branch"""
        environment = ExtendedEnvironmentSelector().select_environment(github_context)
        print(f"Current branch: {github_context.ref_name}")
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
