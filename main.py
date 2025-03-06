#!/usr/bin/env python3

import os
import sys

from src.actions.actions import RMKCLIExecutor
from src.actions.init_project import ProjectInitializer, GETTenant
from src.credentials.cluster_provider_credentials import Credentials
from src.input_output.input import ArgumentParser
from src.select_environment.select_environment import EnvironmentSelector, ExtendedEnvironmentSelector
from src.utils.github_environment_variables import GitHubContext
from src.utils.install_rmk import RMKInstaller

if __name__ == "__main__":
    try:
        args = ArgumentParser().parse_args()

        github_context = GitHubContext.from_env()
        print(f"Current branch: {github_context.ref_name}")

        environment = ExtendedEnvironmentSelector().select_environment(github_context.ref_name)
        print(f"Current environment: {environment}")

        Credentials(args.cluster_provider_credentials).set_env_variables(environment, args.rmk_cluster_provider)

        RMKInstaller(args)
        ProjectInitializer(environment).configure_rmk_init(args)
        tenant = GETTenant(environment).execute()

        RMKCLIExecutor(github_context, args, environment, tenant).execute()

    except Exception as err:
        print(f"Error: {err}", file=sys.stderr)
        sys.exit(1)
