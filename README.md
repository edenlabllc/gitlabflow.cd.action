# Gitlabflow CD Action

[![Release](https://img.shields.io/github/v/release/edenlabllc/gitlabflow.cd.action.svg?style=for-the-badge)](https://github.com/edenlabllc/gitlabflow.cd.action/releases/latest)
[![Software License](https://img.shields.io/github/license/edenlabllc/gitlabflow.cd.action.svg?style=for-the-badge)](LICENSE)
[![Powered By: Edenlab](https://img.shields.io/badge/powered%20by-edenlab-8A2BE2.svg?style=for-the-badge)](https://edenlab.io)

Reusable GitHub Action for provisioning and destroying clusters, synchronizing releases, and updating project
dependencies using RMK — with multi-cloud and multi-environment support.

## 🚦 What it does

This action encapsulates CD logic for tenant bootstrap repositories using [RMK](https://github.com/edenlabllc/rmk).  
It supports a wide range of infrastructure and deployment operations, triggered by workflow inputs or environment
settings.

**Key features:**

- Cluster provisioning (`rmk cluster capi *`)
- Cluster destruction with optional `[skip cluster destroy]` support
- Release sync and version updates
- Project dependency version updates
- Helmfile validation
- Slack notifications (optional)
- AWS, Azure, GCP support via structured credentials

## ✅ Supported commands

Controlled by the `rmk_command` input:

| Command             | Purpose                                      |
|---------------------|----------------------------------------------|
| `provision`         | Provision a cluster and sync releases        |
| `destroy`           | Tear down a cluster (with CAPI safety logic) |
| `release_sync`      | Apply release definitions                    |
| `release_update`    | Update release version/tag for a repository  |
| `project_update`    | Patch dependency version in `project.yaml`   |
| `helmfile_validate` | Validate Helmfile templates                  |

## 🧠 Why use this

Managing infra per repo is error-prone and hard to maintain. This action:

- Centralizes CD logic across all tenants and environments.
- Supports GitHub-native CD with workflow-level configuration.
- Tracks outputs for automation and audit.
- Minimizes boilerplate: run, pass inputs, and let RMK do the work.

## ⚙️ Usage

Used in `workflow_dispatch` workflows inside tenant bootstrap repositories.

### Example

```yaml
name: Cluster provisioner

on:
  workflow_dispatch:
    inputs:
      rmk_command:
        description: 'Choose command: provision or destroy'
        required: true
        default: provision
        type: choice
        options:
          - provision
          - destroy
      rmk_version:
        description: RMK version
        required: false
        default: latest

env:
  RMK_CLUSTER_PROVIDER: aws

jobs:
  cluster-provision:
    runs-on: ubuntu-22.04
    steps:
      - name: Checkout
        uses: actions/checkout@v4
      - name: Run Gitlabflow CD Action
        uses: edenlabllc/gitlabflow.cd.action@v2
        with:
          github_token_repo_full_access: ${{ secrets.GH_TOKEN_REPO_FULL_ACCESS }}
          cluster_provider_credentials: ${{ secrets.CLUSTER_PROVIDER_CREDENTIALS }}
          rmk_cluster_provider: ${{ env.RMK_CLUSTER_PROVIDER }}
          rmk_command: ${{ inputs.rmk_command }}
          rmk_version: ${{ inputs.rmk_version }}
```

See [`examples/`](./examples) for more templates.

## 🔐 Required secrets

| Name                           | Purpose                                    |
|--------------------------------|--------------------------------------------|
| `GH_TOKEN_REPO_FULL_ACCESS`    | GitHub PAT with access to private repos    |
| `CLUSTER_PROVIDER_CREDENTIALS` | JSON object with cloud credentials per env |
| `SLACK_WEBHOOK`                | (Optional) Slack Incoming Webhook URL      |

## 🌍Cluster provider credentials

See the [`action.yaml`](action.yml)'s `cluster_provider_credentials` action input for more details. 

## 📤 Outputs

Returned by the action depending on command:

| Output name                        | Description                               |
|------------------------------------|-------------------------------------------|
| `environment`                      | Current CD environment                    |
| `git_branch`                       | Git branch name                           |
| `rmk_release_version`              | Release version (for `release_update`)    |
| `rmk_release_repository_full_name` | Full image repo (for `release_update`)    |
| `rmk_project_dependency_name`      | Dependency name (for `project_update`)    |
| `rmk_project_dependency_version`   | Dependency version (for `project_update`) |

## 🔔 Slack notifications

Enable by setting:

```yaml
with:
  rmk_slack_notifications: true
  rmk_slack_webhook: ${{ secrets.SLACK_WEBHOOK }}
  rmk_slack_channel: "#rmk-test-cd"
  rmk_slack_message_details: |
    GitHub Actions Run: https://github.com/${{ github.repository }}/actions/runs/${{ github.run_id }}
    Triggered by: ${{ github.actor }}
```

Notifications are sent for **Success**, **Failure**, and **Skip** (e.g. `[skip cluster destroy]` in commit message).

## 📂 Internals

- [`action.yml`](./action.yml) — defines inputs and outputs.
- [`main.py`](./main.py) — executes command logic.
- [`examples/`](./examples) — ready-to-use workflow templates.
