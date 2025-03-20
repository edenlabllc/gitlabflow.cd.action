from argparse import Namespace


class AllowEnvironments:
    def __init__(self, args: Namespace, environment: str):
        self.args = args
        self.environment = environment

    def validate(self):
        environments = self.args.allowed_environments.split(",")
        if len([env for env in environments if env == self.environment]) == 0:
            raise ValueError(f"environment {self.environment} is not allowed")

        print(f"Environment {self.environment} is allowed")
