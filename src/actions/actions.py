from argparse import Namespace

from ..utils.cmd import BaseCommand, CMDInterface
from ..utils.github_environment_variables import GitHubContext


class DestroyCommand(BaseCommand):
    def __init__(self, github_context: GitHubContext, args: Namespace, environment: str, tenant: str):
        super().__init__(environment)
        self.github_context = github_context
        self.args = args
        self.tenant = tenant

    def run(self):
        print(f"Destroying cluster for branch {self.github_context.ref_name}, environment {self.environment}")
        try:
            self.run_command("rmk release list")
            self.run_command("rmk release destroy")
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
                raise ValueError("ERROR: Release name or version is not configured for release update.")

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
                raise ValueError("ERROR: Dependency name or version is not configured for project update.")

            self.run_command(f"rmk project update --dependency {dependency_name} --version {dependency_version}")
        except Exception as err:
            raise ValueError(f"{err}")


class HelmfileValidateCommand(BaseCommand):
    def __init__(self, github_context: GitHubContext, args: Namespace, environment: str, tenant: str):
        super().__init__(environment)
        self.github_context = github_context
        self.args = args
        self.tenant = tenant
        self.head_ref_branch = self.github_context.ref
        # self.head_ref_branch = self.github_context.ref if self.github_context.ref.startswith("refs/heads/") \
        #     else self.args.helmfile_template_head_ref_branch

    # def git_checkout(self):
    #     try:
    #         repo = Repo(".")
    #         if repo.is_dirty(untracked_files=True):
    #             raise ValueError("Repository has uncommitted changes. Commit or stash them before checkout.")
    #
    #         git = repo.git
    #         git.checkout(self.head_ref_branch)
    #         print(f"Checked out to branch: {self.head_ref_branch}")
    #     except GitCommandError as err:
    #         raise ValueError(f"Failed to checkout branch '{self.head_ref_branch}': {err}")

    def run(self):
        print(f"Validate Helmfile templates for branch: {self.github_context.ref}")
        try:
            # if not self.head_ref_branch:
            #     raise ValueError(
            #         "ERROR: Head branch name is incorrect. Check the workflow's helmfile_template_head_ref_branch input")
            #
            # self.git_checkout()

            print("Execute release build.")
            self.run_command("rmk release build --skip-context-switch")

            print("Execute release template.")
            self.run_command("rmk release template --skip-context-switch")

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
        match self.args.rmk_command:
            case "destroy":
                DestroyCommand(self.github_context, self.args, self.environment, self.tenant).run()
            case "helmfile_validate":
                HelmfileValidateCommand(self.github_context, self.args, self.environment, self.tenant).run()
            case "provision":
                ProvisionCommand(self.github_context, self.args, self.environment, self.tenant).run()
            case "project_update":
                ProjectUpdateCommand(self.github_context, self.args, self.environment, self.tenant).run()
            case "release_sync":
                ReleaseSyncCommand(self.github_context, self.args, self.environment, self.tenant).run()
            case "release_update":
                ReleaseUpdateCommand(self.github_context, self.args, self.environment, self.tenant).run()
            case _:
                raise ValueError(f"Unknown RMK command: {self.args.rmk_command}")
