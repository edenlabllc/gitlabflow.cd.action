import json
import os

from argparse import Namespace
from git import Repo, GitCommandError
from ..utils.cmd import BaseCommand, CMDInterface


class RMKConfigInitCommand(BaseCommand, CMDInterface):
    def __init__(self, environment: str, args: Namespace):
        super().__init__(environment)
        self.cluster_provider = args.rmk_cluster_provider
        self.github_token = args.github_token
        self.slack_notification = args.rmk_slack_notifications
        self.slack_channel = args.rmk_slack_channel
        self.slack_message_details = args.rmk_slack_message_details
        self.slack_webhook = args.rmk_slack_webhook

    def execute(self):
        self.run()

    def run(self):
        """Configure Slack notifications if enabled."""
        os.environ["RMK_GITHUB_TOKEN"] = self.github_token
        if self.slack_notification == "true":
            os.environ["RMK_SLACK_WEBHOOK"] = self.slack_webhook
            os.environ["RMK_SLACK_CHANNEL"] = self.slack_channel

            flags_slack_message_details = ""
            if self.slack_message_details.splitlines():
                flags_slack_message_details = " ".join(
                    [f'--slack-message-details="{detail}"' for detail in self.slack_message_details.splitlines()]
                )

            self.run_command(f"rmk config init --cluster-provider={self.cluster_provider}"
                             f" --progress-bar=false --slack-notifications {flags_slack_message_details}")
        else:
            self.run_command(f"rmk config init --cluster-provider={self.cluster_provider} --progress-bar=false")


class GETTenant(BaseCommand, CMDInterface):
    def __init__(self, environment: str):
        super().__init__(environment)

    def execute(self) -> str:
        return self.run()

    def run(self) -> str:
        output = self.run_command(f"rmk --log-format=json config view", True)
        rmk_config = json.loads(output)
        return rmk_config["config"]["Tenant"]


class ProjectInitializer:
    GIT_CONFIG = {
        "name":  "github-actions",
        "email": "github-actions@github.com",
    }

    def __init__(self, environment: str):
        print("Initialize project repository.")
        self.environment = environment
        self.configure_git()

    def configure_git(self):
        """Configure Git user settings."""
        try:
            repo = Repo(".")
            repo.config_writer().set_value("user", "name", self.GIT_CONFIG["name"]).release()
            repo.config_writer().set_value("user", "email", self.GIT_CONFIG["email"]).release()
        except GitCommandError as err:
            raise ValueError(f"ERROR: Failed to configure Git: {err}")

    def configure_rmk_init(self, args: Namespace):
        """Configure Slack notifications using SlackConfigCommand."""
        rmk_init = RMKConfigInitCommand(self.environment, args)
        rmk_init.execute()
