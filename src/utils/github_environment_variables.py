# GITHUB_ACTOR=user
# GITHUB_API_URL=https://api.github.com/
# GITHUB_EVENT_NAME=workflow_dispatch
# GITHUB_REF=refs/heads/feature-branch-1
# GITHUB_REF_NAME=feature/FFS-123-test
# GITHUB_REF_TYPE=branch
# GITHUB_REPOSITORY=octocat/Hello-World
# GITHUB_REPOSITORY_OWNER=octocat
# GITHUB_RUN_ATTEMPT=1
# GITHUB_RUN_ID=1658821493
# GITHUB_SERVER_URL=https://github.com

import os

from dataclasses import dataclass
from typing import Optional, Dict, List


@dataclass
class GitHubContext:
    actor: str
    api_url: str
    event_name: str
    ref: str
    ref_name: str
    ref_type: str
    repository: str
    repository_owner: str
    run_attempt: str
    run_id: str
    server_url: str

    @staticmethod
    def from_env() -> "GitHubContext":
        required_env_vars = [
            "GITHUB_ACTOR",
            "GITHUB_API_URL",
            "GITHUB_EVENT_NAME",
            "GITHUB_REF",
            "GITHUB_REF_NAME",
            "GITHUB_REF_TYPE",
            "GITHUB_REPOSITORY",
            "GITHUB_REPOSITORY_OWNER",
            "GITHUB_RUN_ATTEMPT",
            "GITHUB_RUN_ID",
            "GITHUB_SERVER_URL",
        ]

        missing_vars = [var for var in required_env_vars if os.getenv(var) is None]
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

        return GitHubContext(
            actor=os.getenv("GITHUB_ACTOR"),
            api_url=os.getenv("GITHUB_API_URL"),
            event_name=os.getenv("GITHUB_EVENT_NAME"),
            ref=os.getenv("GITHUB_REF"),
            ref_name=os.getenv("GITHUB_REF_NAME"),
            ref_type=os.getenv("GITHUB_REF_TYPE"),
            repository=os.getenv("GITHUB_REPOSITORY"),
            repository_owner=os.getenv("GITHUB_REPOSITORY_OWNER"),
            run_attempt=os.getenv("GITHUB_RUN_ATTEMPT"),
            run_id=os.getenv("GITHUB_RUN_ID"),
            server_url=os.getenv("GITHUB_SERVER_URL"),
        )

    def to_list(self) -> List[str]:
        """Return context attributes as a list."""
        return [
            f"actor: {self.actor}",
            f"api_url: {self.api_url}",
            f"event_name: {self.event_name}",
            f"ref: {self.ref}",
            f"ref_name: {self.ref_name}",
            f"ref_type: {self.ref_type}",
            f"repository: {self.repository}",
            f"repository_owner: {self.repository_owner}",
            f"run_attempt: {self.run_attempt}",
            f"run_id: {self.run_id}",
            f"server_url: {self.server_url}",
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


# if __name__ == "__main__":
#     try:
#         github_context = GitHubContext.from_env()
#         print("Context as list:", github_context.to_list())
#         print("Context as string:", github_context.to_string())
#
#         key_to_search = "repository"
#         value = github_context.search_key(key_to_search)
#         print(f"Search result for '{key_to_search}':", value if value else "Key not found")
#
#         if not github_context.validate_repository_format():
#             print("Warning: Repository format is incorrect. Expected 'owner/repo'.")
#
#         print("GitHub URL:", github_context.get_github_url())
#         print("Repository Name:", github_context.get_repository_name())
#         print("GitHub Actions Job API URL:", github_context.get_action_job_api_url())
#         print("Environment Variables as Dict:", github_context.get_env_as_dict())
#
#     except ValueError as e:
#         print(f"Error: {e}")
#         exit(1)
