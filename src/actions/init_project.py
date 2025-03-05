import os

from argparse import Namespace
from git import Repo, GitCommandError
from ..utils.cmd import BaseCommand, CMDInterface


class RMKConfigInitCommand(BaseCommand, CMDInterface):
    def __init__(self, environment: str, args: Namespace):
        super().__init__(environment)
        self.slack_notification = args.rmk_slack_notifications
        self.slack_channel = args.rmk_slack_channel
        self.slack_message_details = args.rmk_slack_message_details
        self.slack_webhook = args.rmk_slack_webhook

    def execute(self):
        self.run()

    def run(self):
        """Configure Slack notifications if enabled."""
        if self.slack_notification == "true":
            os.environ["RMK_SLACK_WEBHOOK"] = self.slack_webhook
            os.environ["RMK_SLACK_CHANNEL"] = self.slack_channel

            flags_slack_message_details = ""
            if self.slack_message_details.splitlines():
                flags_slack_message_details = " ".join(
                    [f'--slack-message-details="{detail}"' for detail in self.slack_message_details.splitlines()]
                )

            self.run_command(f"rmk config init --progress-bar=false --slack-notifications {flags_slack_message_details}")
        else:
            self.run_command("rmk config init --progress-bar=false")


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
            repo = Repo("/github/workspace")
            repo.config_writer().set_value("user", "name", self.GIT_CONFIG["name"]).release()
            repo.config_writer().set_value("user", "email", self.GIT_CONFIG["email"]).release()
        except GitCommandError as err:
            print(f"ERROR: Failed to configure Git: {err}")
            exit(1)

    def configure_rmk_init(self, args: Namespace):
        """Configure Slack notifications using SlackConfigCommand."""
        slack_config = RMKConfigInitCommand(self.environment, args)
        slack_config.execute()
