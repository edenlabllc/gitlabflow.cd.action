from argparse import Namespace

from git import Repo

from ..input_output.output import GitHubOutput
from ..utils.cmd import BaseCommand, CMDInterface
from ..utils.github_environment_variables import GitHubContext


class DestroyCommand(BaseCommand):
    def __init__(self, github_context: GitHubContext, args: Namespace, environment: str, tenant: str):
        super().__init__(environment)
        self.github_context = github_context
        self.args = args
        self.tenant = tenant

    @staticmethod
    def should_skip_destroy() -> bool:
        try:
            message = Repo(".").head.commit.message.lower()
            return "[skip cluster destroy]" in message
        except Exception as err:
            print(f"failed to inspect git commit message: {err}")
            return False  # don't skip if we can't verify

    def run(self):
        if self.should_skip_destroy():
            message = (f"Cluster destroy was skipped for branch `{self.github_context.ref_name}`"
                       f" in environment `{self.environment}` due to `[skip cluster destroy]` tag in commit message.")
            print(f"{message}")
            self.notify_slack(
                self.github_context,
                self.args,
                status="Skip",
                message=message,
                tenant=self.tenant
            )
            return

        print(f"Destroying cluster for branch {self.github_context.ref_name}, environment {self.environment}")
        try:
            self.run_command("rmk release list")
            self.run_command("rmk release destroy")
            self.run_command("rmk cluster capi create")
            self.run_command("rmk cluster capi provision")
            self.run_command("rmk cluster capi destroy")
            self.run_command("rmk cluster capi delete")
        except Exception as err:
            self.notify_slack(self.github_context, self.args,
                              "Failure", f"{err}", tenant=self.tenant)
            raise ValueError(f"{err}")

        print(f"Cluster has been destroyed for branch {self.github_context.ref_name}, environment {self.environment}")
        self.notify_slack(self.github_context, self.args,
                          "Success", "Cluster has been destroyed", tenant=self.tenant)


class ProvisionCommand(BaseCommand):
    def __init__(self, github_context: GitHubContext, args: Namespace, environment: str, tenant: str):
        super().__init__(environment)
        self.github_context = github_context
        self.args = args
        self.tenant = tenant

    def run(self):
        print(f"Provisioning cluster for branch {self.github_context.ref_name}, environment {self.environment}")
        try:
            self.run_command("rmk cluster capi create")
            self.run_command("rmk cluster capi provision")
            self.run_command("rmk release sync")
        except Exception as err:
            self.notify_slack(self.github_context, self.args,
                              "Failure", f"{err}", tenant=self.tenant)
            raise ValueError(f"{err}")

        self.notify_slack(self.github_context, self.args,
                          "Success", "Cluster has been provisioned", tenant=self.tenant)


class ReleaseSyncCommand(BaseCommand):
    def __init__(self, github_context: GitHubContext, args: Namespace, environment: str, tenant: str):
        super().__init__(environment)
        self.github_context = github_context
        self.args = args
        self.tenant = tenant

    def run(self):
        try:
            sync_labels = self.args.rmk_sync_labels
            flags_labels = "".join([f" --selector {label}" for label in sync_labels.split()])
            self.run_command(f"rmk release sync {flags_labels}")
        except Exception as err:
            raise ValueError(f"{err}")


class ReleaseUpdateCommand(BaseCommand):
    def __init__(self, github_context: GitHubContext, args: Namespace, environment: str, tenant: str):
        super().__init__(environment)
        self.github_context = github_context
        self.args = args
        self.tenant = tenant

    def run(self):
        try:
            release_repository = self.args.rmk_release_repository_full_name
            release_version = self.args.rmk_release_version
            if not release_repository or not release_version:
                raise ValueError("release name or version is not configured for release update")

            flags_commit_deploy = "--deploy" \
                if self.args.rmk_update_skip_deploy != "true" else "--skip-context-switch --commit"
            self.run_command(f"rmk release update --repository {release_repository} "
                             f"--tag {release_version} --skip-ci {flags_commit_deploy}")
        except Exception as err:
            raise ValueError(f"{err}")


class ProjectUpdateCommand(BaseCommand):
    def __init__(self, github_context: GitHubContext, args: Namespace, environment: str, tenant: str):
        super().__init__(environment)
        self.github_context = github_context
        self.args = args
        self.tenant = tenant

    def run(self):
        try:
            dependency_name = self.args.rmk_project_dependency_name
            dependency_version = self.args.rmk_project_dependency_version
            if not dependency_name or not dependency_version:
                raise ValueError("dependency name or version is not configured for project update")

            self.run_command(f"rmk project update --dependency {dependency_name} --version {dependency_version}")
        except Exception as err:
            raise ValueError(f"{err}")


class HelmfileValidateCommand(BaseCommand):
    def __init__(self, github_context: GitHubContext, args: Namespace, environment: str, tenant: str):
        super().__init__(environment)
        self.github_context = github_context
        self.args = args
        self.tenant = tenant

    def run(self):
        print(f"Validate Helmfile templates for branch: {self.github_context.ref_name}")
        try:
            print("Execute release build.")
            self.run_command("rmk release build --skip-context-switch 1> /dev/null")

            print("Execute release template.")
            self.run_command("rmk release template --skip-context-switch --helmfile-args=\"--quiet\" --helmfile-args=\"--log-level=error\"")

            print("The Helmfile templates have been validated.")
        except Exception as err:
            raise ValueError(f"{err}")


class RMKCLIExecutor(CMDInterface):
    def __init__(self, github_context: GitHubContext, args: Namespace, environment: str, tenant: str):
        self.environment = environment
        self.github_context = github_context
        self.args = args
        self.tenant = tenant

    def execute(self):
        """Output counters as GitHub Actions outputs"""
        data_output = {
            "environment": self.environment,
            "git_branch":  self.github_context.ref_name,
        }

        match self.args.rmk_command:
            case "destroy":
                DestroyCommand(self.github_context, self.args, self.environment, self.tenant).run()
                GitHubOutput().output_dict(data_output)
            case "helmfile_validate":
                HelmfileValidateCommand(self.github_context, self.args, self.environment, self.tenant).run()
                GitHubOutput().output_dict(data_output)
            case "provision":
                ProvisionCommand(self.github_context, self.args, self.environment, self.tenant).run()
                GitHubOutput().output_dict(data_output)
            case "project_update":
                extra_output = {
                    "rmk_project_dependency_name": self.args.rmk_project_dependency_name,
                    "rmk_project_dependency_version": self.args.rmk_project_dependency_version,
                }
                data_output = {**data_output, **extra_output}

                ProjectUpdateCommand(self.github_context, self.args, self.environment, self.tenant).run()
                GitHubOutput().output_dict(data_output)
            case "release_sync":
                ReleaseSyncCommand(self.github_context, self.args, self.environment, self.tenant).run()
                GitHubOutput().output_dict(data_output)
            case "release_update":
                extra_output = {
                    "rmk_release_repository_full_name": self.args.rmk_release_repository_full_name,
                    "rmk_release_version": self.args.rmk_release_version,
                }
                data_output = {**data_output, **extra_output}

                ReleaseUpdateCommand(self.github_context, self.args, self.environment, self.tenant).run()
                GitHubOutput().output_dict(data_output)
            case _:
                raise ValueError(f"unknown RMK command: {self.args.rmk_command}")
