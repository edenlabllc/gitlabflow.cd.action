import os

from slack_sdk.webhook import WebhookClient
from github import Github, GithubException


class SlackNotifier:
    ICONS = {
        "Success": "https://img.icons8.com/doodle/48/000000/add.png",
        "Failure": "https://img.icons8.com/office/40/000000/minus.png",
        "Skip": "https://img.icons8.com/ios-filled/50/000000/0-degrees.png",
    }

    def __init__(self, status, branch, message, additional_info=None, tenant=None):
        self.status = status
        self.branch = branch
        self.message = message
        self.additional_info = additional_info or {}
        self.tenant = tenant or ""
        self.icon_url = self.ICONS.get(status, self.ICONS["Skip"])
        self.github_repo = os.getenv("GITHUB_REPOSITORY")
        self.github_run_id = os.getenv("GITHUB_RUN_ID")
        self.github_run_attempt = os.getenv("GITHUB_RUN_ATTEMPT")
        self.github_token = os.getenv("GITHUB_TOKEN")
        self.slack_webhook_url = os.getenv("INPUT_RMK_SLACK_WEBHOOK")
        self.webhook_client = WebhookClient(self.slack_webhook_url)
        self.github_client = Github(self.github_token)

    def get_action_job_url(self):
        try:
            repo = self.github_client.get_repo(self.github_repo)
            runs = repo.get_workflow_runs()
            for run in runs:
                if str(run.id) == self.github_run_id:
                    jobs = run.jobs()
                    job_id = jobs[0].id if jobs.totalCount > 0 else None
                    if job_id:
                        return f"{os.getenv('GITHUB_SERVER_URL')}/{self.github_repo}/actions/runs/{self.github_run_id}/job/{job_id}"
        except GithubException as err:
            print(f"Error accessing GitHub API: {err}")
        return None

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
        action_job_url = self.get_action_job_url()
        action_run_by = os.getenv("GITHUB_ACTOR") if os.getenv(
            "GITHUB_EVENT_NAME") == "workflow_dispatch" else "ci-cd-fhir-user"

        payload = self.construct_payload(action_job_url, action_run_by)
        response = self.webhook_client.send(text=payload["text"], username=payload["username"], icon_url=payload["icon_url"])
        return response.status_code


# if __name__ == "__main__":
#     additional_info = {"Environment": "Production", "Deployed Version": "v1.2.3"}
#     notifier = SlackNotifier(status="Success", branch="main", message="Deployment completed",
#                              additional_info=additional_info)
#     response_code = notifier.notify()
#     print(f"Slack notification sent with response code: {response_code}")
