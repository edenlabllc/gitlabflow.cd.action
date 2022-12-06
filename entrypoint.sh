#!/bin/bash
set -e

################################
############ CD part ###########
################################

echo
echo "Initialize environment variables."
echo
echo "Install rmk and dependencies, initialize configuration, run CD."

git config --global "user.name" "github-actions"
git config --global "user.email" "github-actions@github.com"
git config --global --add "safe.directory" "/github/workspace"

# exports are required by the installer scripts and rmk
export GITHUB_TOKEN="${INPUT_GITHUB_TOKEN_REPO_FULL_ACCESS}"
export CLOUDFLARE_TOKEN="${INPUT_CLOUDFLARE_TOKEN}"
export GITHUB_ORG="${GITHUB_REPOSITORY%%/*}"

curl -sL "https://edenlabllc-rmk-tools-infra.s3.eu-north-1.amazonaws.com/rmk/s3-installer" | bash -s -- "${INPUT_RMK_VERSION}"
rmk --version

export TENANT=$(echo "${GITHUB_REPOSITORY}" | cut -d '/' -f2 | cut -d '.' -f1)

function notify_slack() {
  local STATUS="${1}"
  local BRANCH="${2}"
  local MESSAGE="${3}"
  local TENANT="${4:-${TENANT}}"

  local ICON_URL="https://img.icons8.com/ios-filled/50/000000/0-degrees.png"

  case "${STATUS}" in
    Success)
      ICON_URL="https://img.icons8.com/doodle/48/000000/add.png"
      ;;
    Failure)
      ICON_URL="https://img.icons8.com/office/40/000000/minus.png"
      ;;
    Skip)
      ICON_URL="https://img.icons8.com/ios-filled/50/000000/0-degrees.png"
      ;;
  esac

  curl \
    -s \
    -X POST \
    -H 'Content-Type: application/json' \
    --data '{"username":"GitLabFlow Action","icon_url":"'${ICON_URL}'","text":"*Tenant*: '"${TENANT}"'\n*Status*: '"${STATUS}"'\n*Message*: '"${MESSAGE}"'\n'"*Branch*: ${BRANCH}"'"}' \
    "${INPUT_RMK_SLACK_WEBHOOK}"
}

function destroy_clusters() {
  local EXIT_CODE=0

  # grep should be case-insensitive and match the RMK's Golang regex ^[a-z]+-\d+
  for REMOTE_BRANCH in $(git branch -r | grep -i "origin/feature/ffs-\d\+"); do
    local LOCAL_BRANCH="${REMOTE_BRANCH#origin/}"

    git checkout "${LOCAL_BRANCH}"

    if ! [[ $(git show -s --format=%s | grep -v "\[skip cluster destroy\]") ]]; then
      notify_slack  "Skip" "${LOCAL_BRANCH}" "Cluster destroy skipped"
      echo "Skip cluster destroy for branch: \"${LOCAL_BRANCH}\""
      echo
      continue
    fi

    if ! (rmk config init --progress-bar=false); then
      echo >&2 "Config init failed for branch: \"${LOCAL_BRANCH}\""
      echo
      # mark as error because initialization is considered required
      EXIT_CODE=1
      # continue deleting rest of clusters
      continue
    fi

    echo
    echo "Destroying cluster for branch: \"${LOCAL_BRANCH}\""

    if ! (rmk cluster switch); then
      echo >&2 "Cluster doesn't exist for branch: \"${LOCAL_BRANCH}\""
      echo
      continue
    fi

    if ! (rmk release destroy); then
      notify_slack  "Failure" "${LOCAL_BRANCH}" "Destroying releases failed"
      continue
    fi

    if ! (rmk cluster destroy); then
      notify_slack  "Failure" "${LOCAL_BRANCH}" "Destroying cluster failed"
      continue
    fi

    echo "Cluster has been destroyed for branch: \"${LOCAL_BRANCH}\""
    notify_slack "Success" "${LOCAL_BRANCH}" "Cluster has been destroyed"
  done

  if [[ "${INPUT_CHECK_ORPHANED_CLUSTERS}" == true ]]; then
    #todo
    ORPHANED_CLUSTERS="$(aws eks list-clusters --output=json | jq -r '.clusters[] | select(. | test("^'"${TENANT}"'-(ffs|rc)-\\d+-eks$"))')"
    echo
    echo "Orphaned clusters:"
    echo "${ORPHANED_CLUSTERS}"
    if [[ "${ORPHANED_CLUSTERS}" != "" ]]; then
      notify_slack "Failure" "N/A" "Orphaned clusters:\n${ORPHANED_CLUSTERS}"
    fi
  fi

  if [[ "${INPUT_CHECK_ORPHANED_VOLUMES}" == true ]]; then
    # check all volumes in the region because there is no volume tag with a tenant name in AWS
    ORPHANED_VOLUMES="$(aws ec2 describe-volumes --output=json --filters "Name=status,Values=[available,error]" \
      | jq -r '.Volumes[] | (.CreateTime + " " + .AvailabilityZone + " " + .State + " " +  .VolumeId + " " + .VolumeType + " "  + (.Size | tostring) + "GiB")')"
    echo
    echo "Orphaned volumes:"
    echo "${ORPHANED_VOLUMES}"
    if [[ "${ORPHANED_VOLUMES}" != "" ]]; then
      notify_slack "Failure" "N/A" "Orphaned volumes:\n${ORPHANED_VOLUMES}" "N/A"
    fi
  fi

  exit ${EXIT_CODE}
}

if [[ "${INPUT_DESTROY_CLUSTERS}" == true ]]; then
  if [[ "${INPUT_CLUSTER_PROVISIONER}" == true ]]; then
    >&2 echo "ERROR: Inputs cluster_provisioner and destroy_clusters can't be provided simultaneously."
    exit 1
  fi

  export AWS_REGION="${INPUT_CD_DEVELOP_AWS_REGION}"
  export AWS_ACCESS_KEY_ID="${INPUT_CD_DEVELOP_AWS_ACCESS_KEY_ID}"
  export AWS_SECRET_ACCESS_KEY="${INPUT_CD_DEVELOP_AWS_SECRET_ACCESS_KEY}"

  destroy_clusters
fi

if [[ "${GITHUB_REF}" != refs/heads/* ]]; then
  >&2 echo "ERROR: Only pushes to branches are supported. Check the workflow's on.push.* section."
  exit 1
fi

GIT_BRANCH="${GITHUB_REF#refs/heads/}"
ENVIRONMENT="${GIT_BRANCH}"

function check_cluster_provision_command_valid() {
  if ! [[ "${INPUT_RMK_COMMAND}" =~ provision|destroy ]]; then
    >&2 echo "ERROR: For cluster provisioning and destroy, only the following commands are allowed: provision destroy"
    exit 1
  fi
}

function check_release_cluster_not_exist() {
  local EXIT_CODE=0

  # grep should be case-insensitive and match the RMK's Golang regex ^[a-z]+-\d+
  for REMOTE_BRANCH in $(git branch -r | grep -i "origin/release/rc-\d\+"); do
    local LOCAL_BRANCH="${REMOTE_BRANCH#origin/}"

    git checkout "${LOCAL_BRANCH}"

    if ! (rmk config init --progress-bar=false 1> /dev/null); then
      echo >&2 "Config init failed for branch: \"${LOCAL_BRANCH}\""
      echo
      # mark as error because initialization is considered required
      EXIT_CODE=1
      # continue to search available release cluster
      continue
    fi

    if (rmk cluster switch 2> /dev/null); then
      echo >&2 "Release cluster already exists for branch: \"${LOCAL_BRANCH}\""
      echo >&2 "Destroy existing cluster and try again."
      exit 1
    fi
  done

  git checkout "${GIT_BRANCH}"

  return ${EXIT_CODE}
}

if [[ "${INPUT_CLUSTER_PROVISIONER}" == "true" ]]; then
  case "${ENVIRONMENT}" in
    feature/FFS-*|release/RC-*)
      echo
      echo "Skipped checking allowed environment."
      echo "Preparing feature cluster for branch: \"${ENVIRONMENT}\""
      check_cluster_provision_command_valid
      ;;
    *)
      #todo
      >&2 echo "ERROR: Provisioning temporary clusters is only allowed for the following branch prefixes: feature/FFS-* release/RC-*"
      exit 1
      ;;
  esac
elif [[ "${INPUT_RMK_COMMAND}" != "reindex" && "${INPUT_ROUTES_TEST}" != "true" ]]; then
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
  staging|release/RC-*)
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

if [[ "${INPUT_MONGODB_BACKUP}" == "true" ]]; then
  export MONGODB_TOOLS_ENABLED="true"

  if ! (rmk release -- -l name=mongodb-tools sync --set "env.ACTION=backup"); then
    notify_slack "Failure" "${ENVIRONMENT}" "MongoDB backup failed"
    exit 1
  fi

  exit 0
fi

if [[ "${INPUT_ROUTES_TEST}" == "true" ]]; then
  git clone "https://${GITHUB_TOKEN}@github.com/${GITHUB_ORG}/fhir.routes.tests.git"
  ENV_DOMAIN="https://$(rmk --lf=json config view | jq -r '.config.RootDomain')"
  cd fhir.routes.tests && git checkout "${INPUT_ROUTES_TEST_BRANCH}" && docker build -t testing .
  docker run testing -D url="${ENV_DOMAIN}"

  exit 0
fi

case "${INPUT_RMK_COMMAND}" in
destroy)
  echo
  echo "Destroy cluster for branch: \"${ENVIRONMENT}\""

  if ! (rmk release list); then
    echo >&2 "Failed to get list of releases for branch: \"${ENVIRONMENT}\""
    exit 1
  fi

  if ! (rmk release destroy); then
    notify_slack "Failure" "${ENVIRONMENT}" "Destroying releases failed"
    exit 1
  fi

  if ! (rmk cluster provision --plan); then
    echo >&2 "Failed to prepare terraform plan for branch: \"${ENVIRONMENT}\""
    notify_slack "Failure" "${ENVIRONMENT}" "Failed to prepare terraform plan"
    exit 1
  fi

  if ! (rmk cluster destroy); then
    notify_slack "Failure" "${ENVIRONMENT}" "Destroying cluster failed"
    exit 1
  fi

  echo "Cluster has been destroyed for branch: \"${ENVIRONMENT}\""
  notify_slack "Success" "${ENVIRONMENT}" "Cluster has been destroyed"
  ;;
provision)
  echo
  echo "Provision cluster for branch: \"${ENVIRONMENT}\""

  if [[ "${ENVIRONMENT}" =~ release\/RC-* ]]; then
    check_release_cluster_not_exist
  fi

  if ! (rmk cluster provision); then
    notify_slack "Failure" "${ENVIRONMENT}" "Cluster provisioning failed"
    exit 1
  fi

  if ! (rmk release list); then
    echo >&2 "Failed to get list of releases for branch: \"${ENVIRONMENT}\""
    notify_slack "Failure" "${ENVIRONMENT}" "Failed to get list of releases"
    exit 1
  fi

  if [[ "${INPUT_MONGODB_RESTORE}" == "true" ]]; then
    export MONGODB_TOOLS_ENABLED="true"
  fi

  if ! (rmk release sync); then
    notify_slack "Failure" "${ENVIRONMENT}" "Release sync failed"
    exit 1
  fi

  notify_slack "Success" "${ENVIRONMENT}" "Cluster has been provisioned"
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
reindex)
  export FHIR_SERVER_SEARCH_REINDEXER_ENABLED="true"
  if [[ "${INPUT_REINDEXER_COLLECTIONS}" != "" ]]; then
    COLLECTIONS_SET="--set env.COLLECTIONS=${INPUT_REINDEXER_COLLECTIONS}"
  fi
  
  if ! (rmk release -- -l name="${INPUT_REINDEXER_RELEASE_NAME}" sync ${COLLECTIONS_SET}); then
    notify_slack "Failure" "${ENVIRONMENT}" "Reindexer job failed"
    exit 1
  fi
  notify_slack "Success" ${ENVIRONMENT} "Reindexer job complete"
  ;;
esac

# always output action variables, description by link https://github.blog/changelog/2022-10-11-github-actions-deprecating-save-state-and-set-output-commands/
echo "git_branch=${GIT_BRANCH}" >> "${GITHUB_OUTPUT}"
echo "repository_full_name=${REPOSITORY_FULL_NAME}" >> "${GITHUB_OUTPUT}"
echo "version=${VERSION}" >> "${GITHUB_OUTPUT}"
echo "environment=${ENVIRONMENT}" >> "${GITHUB_OUTPUT}"
