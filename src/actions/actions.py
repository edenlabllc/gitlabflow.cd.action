import os

from ..utils.cmd import BaseCommand, CMDInterface


class DestroyCommand(BaseCommand):
    def run(self):
        print(f"Destroying cluster for branch: {self.environment}")
        self.run_command("rmk release list")
        self.run_command("rmk release destroy")
        self.run_command("rmk cluster provision --plan")
        self.run_command("rmk cluster destroy")
        print(f"Cluster has been destroyed for branch: {self.environment}")
        self.notify_slack("Success", "Cluster has been destroyed")


class ProvisionCommand(BaseCommand):
    def run(self):
        print(f"Provisioning cluster for branch: {self.environment}")
        self.run_command("rmk cluster provision")
        self.run_command("rmk release list")
        self.run_command("rmk release sync")
        self.notify_slack("Success", "Cluster has been provisioned")


class ReleaseSyncCommand(BaseCommand):
    def run(self):
        sync_labels = os.getenv("INPUT_RMK_SYNC_LABELS", "")
        flags_labels = "".join([f" --selector {label}" for label in sync_labels.split()])
        self.run_command(f"rmk release sync {flags_labels}")


class ReleaseUpdateCommand(BaseCommand):
    def run(self):
        repo = os.getenv("REPOSITORY_FULL_NAME")
        version = os.getenv("VERSION")
        flags_commit_deploy = "--deploy" if os.getenv(
            "INPUT_RMK_UPDATE_SKIP_DEPLOY") != "true" else "--skip-context-switch --commit"
        self.run_command(f"rmk release update --repository {repo} --tag {version} --skip-ci {flags_commit_deploy}")


class ReindexCommand(BaseCommand):
    def run(self):
        os.environ["FHIR_SERVER_SEARCH_REINDEXER_ENABLED"] = "true"
        collections_set = f"--set env.COLLECTIONS={os.getenv('INPUT_REINDEXER_COLLECTIONS')}" if os.getenv(
            "INPUT_REINDEXER_COLLECTIONS") else ""
        self.run_command(
            f"rmk release sync --selector name={os.getenv('INPUT_REINDEXER_RELEASE_NAME')} {collections_set}")
        self.notify_slack("Success", "Reindexer job complete")


class ProjectUpdateCommand(BaseCommand):
    def run(self):
        dependency_name = os.getenv("INPUT_PROJECT_DEPENDENCY_NAME")
        dependency_version = os.getenv("INPUT_PROJECT_DEPENDENCY_VERSION")
        if not dependency_name or not dependency_version:
            raise ValueError("ERROR: Dependency name or version is not configured for project update.")
        self.run_command(f"rmk project update --dependency {dependency_name} --version {dependency_version}")


class RMKCLIExecutor(CMDInterface):
    COMMANDS = {
        "destroy": DestroyCommand,
        "project_update": ProjectUpdateCommand,
        "provision": ProvisionCommand,
        "release_update": ReleaseUpdateCommand,
        "release_sync": ReleaseSyncCommand,
    }

    def __init__(self, command: str, environment: str):
        self.command = command
        self.environment = environment

    def execute(self):
        if self.command in self.COMMANDS:
            self.COMMANDS[self.command](self.environment).run()
        else:
            raise ValueError(f"Unknown RMK command: {self.command}")


#
# if __name__ == "__main__":
#     rmk_executor = RMKCLIExecutor(
#         command=os.getenv("INPUT_RMK_COMMAND", "destroy"),
#         environment=os.getenv("ENVIRONMENT", "develop")
#     )
#     rmk_executor.execute()
