import subprocess

from abc import ABC, abstractmethod
from argparse import Namespace

from src.notification.slack_natification import SlackNotifier
from src.utils.github_environment_variables import GitHubContext


class CMDInterface(ABC):
    @abstractmethod
    def execute(self):
        pass


class BaseCommand(ABC):
    def __init__(self, environment: str):
        self.environment = environment

    @abstractmethod
    def run(self):
        pass

    @staticmethod
    def run_command(cmd: str, capture_output: bool = False):
        try:
            if capture_output:
                result = subprocess.run(cmd, shell=True, check=True, text=True, stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE)
                return result.stdout.strip()
            else:
                subprocess.run(cmd, shell=True, check=True)
                return None
        except subprocess.CalledProcessError as err:
            raise ValueError(f"command '{cmd}' failed with exit code {err.returncode}")

    def notify_slack(self, github_context: GitHubContext, args: Namespace, status, message, additional_info=None, tenant=None):
        notifier = SlackNotifier(github_context, args, status=status, message=message,
                                 additional_info=additional_info, tenant=tenant)
        response_code = notifier.notify()
        print(f"Slack notification sent with response code: {response_code}")
        print(f"Slack Notification - Status: {status}, Environment: {self.environment}, Message: {message}")
