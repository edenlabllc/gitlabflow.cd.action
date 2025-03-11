import os

from typing import Dict

class GitHubOutput:
    def __init__(self):
        self.is_github_actions_runner = 'GITHUB_OUTPUT' in os.environ

    def output_dict(self, body: Dict[str, str]):
        if self.is_github_actions_runner:
            with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
                for key in body: print(f"{key}={body[key]}", file=f)
        else:
            print("Skip output counters as GitHub actions outputs.")
