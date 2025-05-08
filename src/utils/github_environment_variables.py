# GITHUB_ACTOR=user
# GITHUB_API_URL=https://api.github.com/
# GITHUB_BASE_REF=feature/FFS-2-test
# GITHUB_EVENT_NAME=workflow_dispatch
# GITHUB_HEAD_REF=feature/FFS-3-test
# GITHUB_REF=refs/heads/feature-branch-1
# GITHUB_REF_NAME=feature/FFS-123-test
# GITHUB_REF_TYPE=branch
# GITHUB_REPOSITORY=octocat/Hello-World
# GITHUB_REPOSITORY_OWNER=octocat
# GITHUB_RUN_ATTEMPT=1
# GITHUB_RUN_ID=1658821493
# GITHUB_RUN_NUMBER=1
# GITHUB_SERVER_URL=https://github.com
# GITHUB_SHA=ffac537e6cbbf934b08745a378932722df287a53

import os

from dataclasses import dataclass
from typing import Optional, Dict, List


@dataclass
class GitHubContext:
    actor: str
    api_url: str
    base_ref: str
    event_name: str
    head_ref: str
    ref: str
    ref_name: str
    ref_type: str
    repository: str
    repository_owner: str
    run_attempt: str
    run_id: str
    run_number: str
    server_url: str
    sha: str

    @staticmethod
    def from_env(github_custom_ref="", github_custom_ref_name="") -> "GitHubContext":
        required_env_vars = [
            "GITHUB_ACTOR",
            "GITHUB_API_URL",
            "GITHUB_BASE_REF",
            "GITHUB_EVENT_NAME",
            "GITHUB_HEAD_REF",
            "GITHUB_REF",
            "GITHUB_REF_NAME",
            "GITHUB_REF_TYPE",
            "GITHUB_REPOSITORY",
            "GITHUB_REPOSITORY_OWNER",
            "GITHUB_RUN_ATTEMPT",
            "GITHUB_RUN_ID",
            "GITHUB_RUN_NUMBER",
            "GITHUB_SERVER_URL",
            "GITHUB_SHA",
        ]

        missing_vars = [var for var in required_env_vars if os.getenv(var) is None]
        if missing_vars:
            raise ValueError(f"missing required environment variables: {', '.join(missing_vars)}")

        return GitHubContext(
            actor=os.getenv("GITHUB_ACTOR"),
            api_url=os.getenv("GITHUB_API_URL"),
            base_ref=os.getenv("GITHUB_BASE_REF"),
            event_name=os.getenv("GITHUB_EVENT_NAME"),
            head_ref=os.getenv("GITHUB_HEAD_REF"),
            ref=github_custom_ref if github_custom_ref else os.getenv("GITHUB_REF"),
            ref_name=github_custom_ref_name if github_custom_ref_name else os.getenv("GITHUB_REF_NAME"),
            ref_type=os.getenv("GITHUB_REF_TYPE"),
            repository=os.getenv("GITHUB_REPOSITORY"),
            repository_owner=os.getenv("GITHUB_REPOSITORY_OWNER"),
            run_attempt=os.getenv("GITHUB_RUN_ATTEMPT"),
            run_id=os.getenv("GITHUB_RUN_ID"),
            run_number=os.getenv("GITHUB_RUN_NUMBER"),
            server_url=os.getenv("GITHUB_SERVER_URL"),
            sha=os.getenv("GITHUB_SHA"),
        )

    def to_list(self) -> List[str]:
        """Return context attributes as a list."""
        return [
            f"actor: {self.actor}",
            f"api_url: {self.api_url}",
            f"base_ref: {self.base_ref}",
            f"event_name: {self.event_name}",
            f"head_ref: {self.head_ref}",
            f"ref: {self.ref}",
            f"ref_name: {self.ref_name}",
            f"ref_type: {self.ref_type}",
            f"repository: {self.repository}",
            f"repository_owner: {self.repository_owner}",
            f"run_attempt: {self.run_attempt}",
            f"run_id: {self.run_id}",
            f"run_number: {self.run_number}",
            f"server_url: {self.server_url}",
            f"sha: {self.sha}",
        ]

    def to_string(self) -> str:
        """Return context attributes as a single formatted string."""
        return " | ".join(self.to_list())

    def search_key(self, key: str) -> Optional[str]:
        """Quick search for a specific key in the context attributes."""
        context_dict = self.__dict__
        return context_dict.get(key, None)

    def validate_repository_format(self) -> bool:
        """Check if the repository follows the format 'owner/repo'."""
        return "/" in self.repository and len(self.repository.split("/")) == 2

    def get_github_url(self) -> str:
        """Generate the GitHub repository URL."""
        return f"{self.server_url}/{self.repository}"

    def get_env_as_dict(self) -> Dict[str, str]:
        """Return all attributes as a dictionary."""
        return self.__dict__

    def get_repository_name(self) -> str:
        """Extract and return the repository name from 'owner/repo'."""
        if self.validate_repository_format():
            return self.repository.split("/")[1]
        return "Invalid Repository Format"

    def get_action_job_api_url(self) -> str:
        """Generate the GitHub Actions job API URL."""
        return f"{self.api_url}/repos/{self.repository}/actions/runs/{self.run_id}/attempts/{self.run_attempt}/jobs"
