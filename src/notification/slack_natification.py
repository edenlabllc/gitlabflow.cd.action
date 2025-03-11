from argparse import Namespace

from slack_sdk.webhook import WebhookClient
from github import Github, GithubException

from src.utils.github_environment_variables import GitHubContext


class SlackNotifier:
    ICONS = {
        "Success": "https://img.icons8.com/doodle/48/000000/add.png",
        "Failure": "https://img.icons8.com/office/40/000000/minus.png",
        "Skip": "https://img.icons8.com/ios-filled/50/000000/0-degrees.png",
    }

    def __init__(self, github_context: GitHubContext, args: Namespace, status, message, additional_info=None, tenant=None):
        self.branch = github_context.ref_name
        self.status = status
        self.message = message
        self.additional_info = additional_info or {}
        self.tenant = tenant or ""
        self.icon_url = self.ICONS.get(status, self.ICONS["Skip"])
        self.github_context = github_context

        if not args.github_token or not args.github_token.strip():
            raise ValueError("GitHub token is missing or empty")
        self.github_client = Github(args.github_token)

        if not args.rmk_slack_webhook or not args.rmk_slack_webhook.strip():
            raise ValueError("slack Webhook token is missing or empty")
        self.webhook_client = WebhookClient(args.rmk_slack_webhook)

    def get_action_job_url(self):
        try:
            repo = self.github_client.get_repo(self.github_context.repository)
            runs = repo.get_workflow_runs()
            for run in runs:
                if str(run.id) == self.github_context.run_id:
                    jobs = run.jobs()
                    job_id = jobs[0].id if jobs.totalCount > 0 else None
                    if job_id:
                        return f"{self.github_context.get_github_url()}/actions/runs/{ self.github_context.run_id}/job/{job_id}"
        except GithubException as err:
            raise ValueError(f"accessing GitHub API: {err}")

    def construct_payload(self, action_job_url, action_run_by):
        payload_text = (
            f"*Action run by*: {action_run_by}\n"
            f"*Action job URL*: {action_job_url}\n"
            f"*Tenant*: {self.tenant}\n"
            f"*Branch*: {self.branch}\n"
            f"*Status*: {self.status}\n"
            f"*Message*: {self.message}\n"
        )
        for key, value in self.additional_info.items():
            payload_text += f"*{key}*: {value}\n"

        return {
            "username": "GitLabFlow Action",
            "icon_url": self.icon_url,
            "text": payload_text
        }

    def notify(self):
        try:
            action_job_url = self.get_action_job_url()
            action_run_by = self.github_context.actor \
                if self.github_context.event_name == "workflow_dispatch" else "ci-cd-fhir-user"
            payload = self.construct_payload(action_job_url, action_run_by)
            response = self.webhook_client.send_dict(payload)
        except Exception as err:
            raise ValueError(f"sending webhook request: {err}")

        return response.status_code
