import re

from abc import ABC, abstractmethod
from argparse import Namespace


class EnvironmentSelectorInterface(ABC):
    @abstractmethod
    def select_environment(self, branch_name: str) -> str:
        pass


class EnvironmentSelector(EnvironmentSelectorInterface):
    TASK_NUM_REGEXP = r"[a-z]+-\d+"
    SEMVER_REGEXP = r"v\d+\.\d+\.\d+(-rc)?$"

    PREFIX_FEATURE_BRANCH = "feature"
    PREFIX_RELEASE_BRANCH = "release"

    SELECT_FEATURE_BRANCHES = fr"{PREFIX_FEATURE_BRANCH}/{TASK_NUM_REGEXP}"
    SELECT_RELEASE_BRANCHES = fr"{PREFIX_RELEASE_BRANCH}/{TASK_NUM_REGEXP}|{PREFIX_RELEASE_BRANCH}/{SEMVER_REGEXP}"

    SELECT_ORIGIN_FEATURE_BRANCHES = fr"origin/{PREFIX_FEATURE_BRANCH}/{TASK_NUM_REGEXP}"
    SELECT_ORIGIN_RELEASE_BRANCHES = fr"origin/{PREFIX_RELEASE_BRANCH}/{TASK_NUM_REGEXP}|origin/{PREFIX_RELEASE_BRANCH}/{SEMVER_REGEXP}"

    SELECT_ALL_BRANCHES = fr"{SELECT_FEATURE_BRANCHES}|{SELECT_RELEASE_BRANCHES}"
    SELECT_ORIGIN_ALL_BRANCHES = fr"{SELECT_ORIGIN_FEATURE_BRANCHES}|{SELECT_ORIGIN_RELEASE_BRANCHES}"

    def select_environment(self, branch_name: str) -> str:
        if re.match(r"^(develop|staging|production)$", branch_name, re.IGNORECASE):
            return branch_name

        if re.match(EnvironmentSelector.SELECT_FEATURE_BRANCHES, branch_name, re.IGNORECASE):
            return "develop"

        if re.match(EnvironmentSelector.SELECT_RELEASE_BRANCHES, branch_name, re.IGNORECASE):
            if re.search(EnvironmentSelector.SEMVER_REGEXP, branch_name, re.IGNORECASE):
                if "-rc" in branch_name:
                    return "staging"
                return "production"
            return "staging"

        raise ValueError(f"ERROR: Environment '{branch_name}' not allowed for environment selection.")


class ExtendedEnvironmentSelector(EnvironmentSelector):
    def select_environment(self, branch_name: str) -> str:
        if branch_name.startswith("hotfix/"):
            return "production"
        return super().select_environment(branch_name)
