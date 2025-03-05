#!/usr/bin/env python3

import os
import sys

from src.credentials.cluster_provider_credentials import Credentials
from src.input_output.input import ArgumentParser
from src.select_environment.select_environment import EnvironmentSelector, ExtendedEnvironmentSelector
from src.utils.github_environment_variables import GitHubContext


if __name__ == "__main__":
    try:
        args = ArgumentParser().parse_args()
        # print(args)
        # RMKInstaller(args)

        github_context = GitHubContext.from_env()
        print(f"Current branch: {github_context.ref_name}")

        selector = ExtendedEnvironmentSelector()
        environment = selector.select_environment(github_context.ref_name)
        print(f"Current environment: {environment}")

        creds = Credentials(args.cluster_provider_credentials)
        print(f"Current credentials for different cluster providers: {creds.get_environment(environment).cluster_providers}")

        creds.set_env_variables(selector.select_environment(github_context.ref_name), args.rmk_cluster_provider)
        print("Check current env credentials:", os.getenv("AWS_REGION"))
    except Exception as err:
        print(f"Error: {err}", file=sys.stderr)
        sys.exit(1)
