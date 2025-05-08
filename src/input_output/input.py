import os
import argparse


class ArgumentParser:
    class EnvDefault(argparse.Action):
        def __init__(self, envvar, required=True, default=None, **kwargs):
            if envvar:
                if envvar in os.environ:
                    default = os.environ.get(envvar, default)
            if required and default:
                required = False
            super(ArgumentParser.EnvDefault, self).__init__(default=default, required=required, metavar=envvar, **kwargs)

        def __call__(self, parser, namespace, values, option_string=None):
            setattr(namespace, self.dest, values)

    def __init__(self):
        self.parser = argparse.ArgumentParser()
        self.setup_arguments()

    def setup_arguments(self):
        self.parser.add_argument("--allowed-environments",
                                 action=self.EnvDefault, envvar="INPUT_ALLOWED_ENVIRONMENTS",
                                 type=str, default='develop')

        self.parser.add_argument("--cluster-provider-credentials",
                                 action=self.EnvDefault, envvar="INPUT_CLUSTER_PROVIDER_CREDENTIALS",
                                 type=str, required=False)

        self.parser.add_argument("--github-custom-ref",
                                 action=self.EnvDefault, envvar="INPUT_GITHUB_CUSTOM_REF",
                                 type=str, required=False)

        self.parser.add_argument("--github-custom-ref-name",
                                 action=self.EnvDefault, envvar="INPUT_GITHUB_CUSTOM_REF_NAME",
                                 type=str, required=False)

        self.parser.add_argument("--github-token",
                                 action=self.EnvDefault, envvar="INPUT_GITHUB_TOKEN_REPO_FULL_ACCESS",
                                 type=str, required=False)

        self.parser.add_argument("--rmk-cluster-provider",
                                 action=self.EnvDefault, envvar="INPUT_RMK_CLUSTER_PROVIDER",
                                 type=str, required=False)

        self.parser.add_argument("--rmk-command",
                                 action=self.EnvDefault, envvar="INPUT_RMK_COMMAND",
                                 type=str, required=False)

        self.parser.add_argument("--rmk-download-url",
                                 action=self.EnvDefault, envvar="INPUT_RMK_DOWNLOAD_URL",
                                 type=str, default='https://edenlabllc-rmk.s3.eu-north-1.amazonaws.com/rmk/s3-installer')

        self.parser.add_argument("--rmk-project-dependency-name",
                                 action=self.EnvDefault, envvar="INPUT_RMK_PROJECT_DEPENDENCY_NAME",
                                 type=str, required=False)

        self.parser.add_argument("--rmk-project-dependency-version",
                                 action=self.EnvDefault, envvar="INPUT_RMK_PROJECT_DEPENDENCY_VERSION",
                                 type=str, required=False)

        self.parser.add_argument("--rmk-release-repository-full-name",
                                 action=self.EnvDefault, envvar="INPUT_RMK_RELEASE_REPOSITORY_FULL_NAME",
                                 type=str, required=False)

        self.parser.add_argument("--rmk-release-version",
                                 action=self.EnvDefault, envvar="INPUT_RMK_RELEASE_VERSION",
                                 type=str, required=False)

        self.parser.add_argument("--rmk-slack-channel",
                                 action=self.EnvDefault, envvar="INPUT_RMK_SLACK_CHANNEL",
                                 type=str, required=False)

        self.parser.add_argument("--rmk-slack-message-details",
                                 action=self.EnvDefault, envvar="INPUT_RMK_SLACK_MESSAGE_DETAILS",
                                 type=str, required=False)

        self.parser.add_argument("--rmk-slack-notifications",
                                 action=self.EnvDefault, envvar="INPUT_RMK_SLACK_NOTIFICATIONS",
                                 type=str, required=False)

        self.parser.add_argument("--rmk-slack-webhook",
                                 action=self.EnvDefault, envvar="INPUT_RMK_SLACK_WEBHOOK",
                                 type=str, required=False)

        self.parser.add_argument("--rmk-sync-labels",
                                 action=self.EnvDefault, envvar="INPUT_RMK_SYNC_LABELS",
                                 type=str, required=False)

        self.parser.add_argument("--rmk-update-skip-deploy",
                                 action=self.EnvDefault, envvar="INPUT_RMK_UPDATE_SKIP_DEPLOY",
                                 type=str, required=False)

        self.parser.add_argument("--rmk-version",
                                 action=self.EnvDefault, envvar="INPUT_RMK_VERSION",
                                 type=str, default='latest')

    def parse_args(self):
        return self.parser.parse_args()
