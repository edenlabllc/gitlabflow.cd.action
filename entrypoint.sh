#!/bin/bash
set -e

################################
############ CD part ###########
################################

echo
echo "Initialize environment variables."
echo
echo "Install rmk and dependencies, initialize configuration, run CD."

git config user.name github-actions
git config user.email github-actions@github.com

# exports are required by the installer scripts and rmk
export GITHUB_TOKEN="${INPUT_GITHUB_TOKEN_REPO_FULL_ACCESS}"
export CLOUDFLARE_TOKEN="${INPUT_CLOUDFLARE_TOKEN}"
export GITHUB_ORG="${GITHUB_REPOSITORY%%/*}"

curl -sL "https://${GITHUB_TOKEN}@raw.githubusercontent.com/${GITHUB_ORG}/rmk.tools.infra/master/bin/installer" | bash -s -- "${INPUT_RMK_VERSION}"

rmk --version

export TENANT=$(echo $GITHUB_REPOSITORY | cut -d '/' -f2 | cut -d '.' -f1)

function slack_notification() {
  local icon_url="https://img.icons8.com/ios-filled/50/000000/0-degrees.png"
  case "$1" in
  Success)
    icon_url="https://img.icons8.com/doodle/48/000000/add.png"
    ;;
  Failure)
    icon_url="https://img.icons8.com/office/40/000000/minus.png"
    ;;
  Skip)
    icon_url="https://img.icons8.com/ios-filled/50/000000/0-degrees.png"
    ;;
  esac

  curl -s -X POST -H 'Content-type: application/json' --data '{"username":"Cluster action","icon_url":"'${icon_url}'","text":"*Tenant*: '"${TENANT}"'\n\nAction: '"$1"'\n*Status*: '"$status"'\n'"*Cluster for branch*: $2"'"}' ${INPUT_RMK_SLACK_WEBHOOK}
}

function destroy_clusters() {
  export AWS_REGION="${INPUT_CD_DEVELOP_AWS_REGION}"
  export AWS_ACCESS_KEY_ID="${INPUT_CD_DEVELOP_AWS_ACCESS_KEY_ID}"
  export AWS_SECRET_ACCESS_KEY="${INPUT_CD_DEVELOP_AWS_SECRET_ACCESS_KEY}"

  for remote in $(git branch -r | grep "feature/FFS-999"); do
    git checkout ${remote#origin/}

    if ! [[ $(git show -s --format=%s | grep -v "\[skip cluster destroy\]") ]]; then
      slack_notification "Skip" ${remote#origin/} "Cluster destroy was skipped"
      echo "Skip cluster destroy for branch: \"${remote#origin/}\"."
      echo
      continue
    fi

    rmk config init --progress-bar=false
    echo
    echo "Destroy cluster for branch: \"${remote#origin/}\"."

    if ! (rmk cluster switch); then
      echo >&2 "Cluster doesn't exist for branch: \"${remote#origin/}\"."
      echo
      continue
    fi

    if ! (rmk release destroy); then
      slack_notification "Failure" ${remote#origin/} "Issue with destroying releases"
      continue
    fi

    if ! (rmk cluster destroy); then
      slack_notification "Failure" ${remote#origin/} "Issue with destroying cluster"
      continue
    fi

    echo "Cluster has been destroy for branch: \"${remote#origin/}\"."
    slack_notification "Success" ${remote#origin/} "Cluster has been destroyed"

  done
}

if [[ "${INPUT_DESTROY_CLUSTERS}" == true ]]; then
  if [[ "${INPUT_CLUSTER_PROVISIONER}" == true ]]; then
    echo "Inputs cluster_provisioner and destroy_clusters can't be provided simultaneously"
    exit 1
  fi

  export AWS_REGION="${INPUT_CD_DEVELOP_AWS_REGION}"
  export AWS_ACCESS_KEY_ID="${INPUT_CD_DEVELOP_AWS_ACCESS_KEY_ID}"
  export AWS_SECRET_ACCESS_KEY="${INPUT_CD_DEVELOP_AWS_SECRET_ACCESS_KEY}"

  destroy_clusters
  exit 0
fi

if [[ "${GITHUB_REF}" != refs/heads/* ]]; then
  >&2 echo "ERROR: Only pushes to branches are supported. Check the workflow's on.push.* section."
  exit 1
fi

GIT_BRANCH="${GITHUB_REF#refs/heads/}"
ENVIRONMENT="${GIT_BRANCH}"

function check_cluster_provision_command() {
  if ! [[ "${INPUT_RMK_COMMAND}" =~ provision|destroy ]]; then
    >&2 echo "ERROR: For provision a cluster, commands only are allowed: provision, destroy"
    exit 1
  fi
}

if [[ "${INPUT_CLUSTER_PROVISIONER}" == "true" ]]; then
  case "${ENVIRONMENT}" in
  feature/FFS-*)
    echo
    echo "Skipped check allowed environment. Running prepare feature cluster from branch \"${ENVIRONMENT}\"."
    check_cluster_provision_command
    ;;
  release/v*)
    echo
    echo "Skipped check allowed environment. Running prepare release cluster from branch \"${ENVIRONMENT}\"."
    check_cluster_provision_command
    ;;
  *)
    >&2 echo "ERROR: Provisioning temporary clusters is only allowed from branches with prefixes 'feature/FFS-*' or 'release/v*.'"
    exit 1
    ;;
  esac
else
  ALLOWED_ENVIRONMENTS=("${INPUT_ALLOWED_ENVIRONMENTS/,/ }")
  if [[ ! " ${ALLOWED_ENVIRONMENTS[*]} " =~ " ${ENVIRONMENT} " ]]; then
    >&2 echo "ERROR: Environment \"${ENVIRONMENT}\" not allowed for automatic CD."
    exit 1
  fi
fi

REPOSITORY_FULL_NAME="${INPUT_REPOSITORY_FULL_NAME}"
VERSION="${INPUT_VERSION}"

case "${ENVIRONMENT}" in
develop|feature/FFS-*)
  export AWS_REGION="${INPUT_CD_DEVELOP_AWS_REGION}"
  export AWS_ACCESS_KEY_ID="${INPUT_CD_DEVELOP_AWS_ACCESS_KEY_ID}"
  export AWS_SECRET_ACCESS_KEY="${INPUT_CD_DEVELOP_AWS_SECRET_ACCESS_KEY}"
  ;;
staging|release/v*)
  export AWS_REGION="${INPUT_CD_STAGING_AWS_REGION}"
  export AWS_ACCESS_KEY_ID="${INPUT_CD_STAGING_AWS_ACCESS_KEY_ID}"
  export AWS_SECRET_ACCESS_KEY="${INPUT_CD_STAGING_AWS_SECRET_ACCESS_KEY}"
  ;;
esac

# Slack notification
if [[ "${INPUT_RMK_SLACK_NOTIFICATIONS}" == "true" ]]; then
  export SLACK_WEBHOOK=${INPUT_RMK_SLACK_WEBHOOK}
  export SLACK_CHANNEL=${INPUT_RMK_SLACK_CHANNEL}

  FLAGS_SLACK_MESSAGE_DETAILS=""
  if [[ "${INPUT_RMK_SLACK_MESSAGE_DETAILS}" != "" ]]; then
    OLDIFS="${IFS}"
    IFS=$'\n'
    for DETAIL in ${INPUT_RMK_SLACK_MESSAGE_DETAILS}; do
      FLAGS_SLACK_MESSAGE_DETAILS="${FLAGS_SLACK_MESSAGE_DETAILS} --smd=\"${DETAIL}\""
    done
    IFS="${OLDIFS}"
  fi

  eval rmk config init --progress-bar=false --slack-notifications ${FLAGS_SLACK_MESSAGE_DETAILS}
else
  rmk config init --progress-bar=false
fi

case "${INPUT_RMK_COMMAND}" in
destroy)
  echo
  echo "Destroy cluster for branch: \"${ENVIRONMENT}\"."
  if ! (rmk release list); then
    echo >&2 "Failed to get list of releases for environment: \"${ENVIRONMENT}\"."
    exit 1
  fi

  if ! (rmk release destroy); then
    slack_notification "Failure" ${remote#origin/} "Issue with destroying releases"
    exit 1
  fi

  if ! (rmk cluster provision --plan); then
    echo >&2 "Failed to prepare terraform plan for environment: \"${ENVIRONMENT}\"."
    slack_notification "Failure" ${remote#origin/} "Issue with getting plan for provision"
    exit 1
  fi

  if ! (rmk cluster destroy); then
    slack_notification "Failure" ${remote#origin/} "Issue with destroying cluster"
    exit 1
  fi

  slack_notification "Success" ${ENVIRONMENT} "Cluster has been destroyed"
  ;;
provision)
  echo
  echo "Provision cluster for branch: \"${ENVIRONMENT}\"."

  if ! (rmk cluster provision); then
    slack_notification "Failure" ${remote#origin/} "Issue with cluster provisioning"
    exit 1
  fi

  if ! (rmk release list); then
    echo >&2 "Failed to get list of releases for environment: \"${ENVIRONMENT}\"."
    slack_notification "Failure" ${remote#origin/} "Issue with getting list of releases"
    exit 1
  fi

  if ! (rmk release sync); then
    slack_notification "Failure" ${remote#origin/} "Issue with release sync"
    exit 1
  fi

  slack_notification "Success" ${ENVIRONMENT} "Cluster has been provisioned"
  ;;
sync)
  FLAGS_SKIP_DEPS=""
  if [[ "${INPUT_RMK_SYNC_SKIP_DEPS}" == "true" ]]; then
    FLAGS_SKIP_DEPS="--skip-deps"
  fi

  FLAGS_LABELS=""
  if [[ "${INPUT_RMK_SYNC_LABELS}" != "" ]]; then
    for LABEL in ${INPUT_RMK_SYNC_LABELS}; do
      FLAGS_LABELS="${FLAGS_LABELS} -l ${LABEL}"
    done
  fi

  rmk release -- ${FLAGS_LABELS} sync ${FLAGS_SKIP_DEPS}
  ;;
update)
  if [[ "${INPUT_RMK_UPDATE_HELMFILE_REPOS_COMMAND}" != "" ]]; then
    rmk release "${INPUT_RMK_UPDATE_HELMFILE_REPOS_COMMAND}"
  fi

  if [[ "${INPUT_RMK_UPDATE_SKIP_DEPLOY}" == "true" ]]; then
    FLAGS_COMMIT_DEPLOY="--skip-context-switch --commit"
  else
    FLAGS_COMMIT_DEPLOY="--deploy"
  fi

  rmk release update --repository "${REPOSITORY_FULL_NAME}" --tag "${VERSION}" --skip-actions ${FLAGS_COMMIT_DEPLOY}
  ;;
esac

# always output action variables
echo "::set-output name=git_branch::${GIT_BRANCH}"
echo "::set-output name=repository_full_name::${REPOSITORY_FULL_NAME}"
echo "::set-output name=version::${VERSION}"
echo "::set-output name=environment::${ENVIRONMENT}"
