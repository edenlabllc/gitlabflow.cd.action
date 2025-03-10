import subprocess
import requests

from argparse import Namespace
from packaging import version


class RMKInstaller:
    def __init__(self, args: Namespace):
        self.version = args.rmk_version
        self.url = args.rmk_download_url
        self.verify_rmk_version()
        self.install_rmk()

    def verify_rmk_version(self):
        print("Verifying RMK installation version...")
        if self.version != "latest":
            if version.parse('v0.45.2') > version.parse(self.version):
                raise Exception(f"version {self.version} of RMK is not correct. " +
                                "The version for RMK must be at least v0.45.2 or greater.")

    def install_rmk(self):
        print("Installing RMK.")
        try:
            response = requests.get(self.url)
            response.raise_for_status()
        except requests.RequestException as err:
            raise Exception(f"error downloading RMK installer file:\n{err}")

        try:
            subprocess.run(
                ["bash", "-s", "--", self.version],
                check=True,
                text=True,
                input=response.text
            )
        except subprocess.CalledProcessError as err:
            raise Exception(f"error installing RMK:\n{err}")
