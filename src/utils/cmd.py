import subprocess

from abc import ABC, abstractmethod
from src.notification.slack_natification import SlackNotifier


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
    def run_command(cmd: str):
        try:
            subprocess.run(cmd, shell=True, check=True)
        except subprocess.CalledProcessError as err:
            raise ValueError(f"ERROR: Command '{cmd}' failed with exit code {err.returncode}")

    def notify_slack(self, status: str, message: str):
        additional_info = {"Environment": "Production", "Deployed Version": "v1.2.3"}
        notifier = SlackNotifier(status="Success", branch="main", message="Deployment completed",
                                 additional_info=additional_info)
        response_code = notifier.notify()
        print(f"Slack notification sent with response code: {response_code}")
        print(f"Slack Notification - Status: {status}, Environment: {self.environment}, Message: {message}")
