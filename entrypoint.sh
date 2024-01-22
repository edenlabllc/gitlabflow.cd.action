#!/bin/bash
set -e

################################
############ CD part ###########
################################

function notify_slack() {
  local STATUS="${1}"
  local BRANCH="${2}"
  local MESSAGE="${3}"
  local TENANT="${4:-${TENANT}}"

  local ICON_URL="https://img.icons8.com/ios-filled/50/000000/0-degrees.png"

  local ACTION_JOB_API_URL="${GITHUB_API_URL}/repos/${GITHUB_REPOSITORY}/actions/runs/${GITHUB_RUN_ID}/attempts/${GITHUB_RUN_ATTEMPT}/jobs"
  local ACTION_JOB_ID="$(curl -sL \
    -H 'Accept: application/vnd.github+json' \
    -H 'Authorization: Bearer '"${GITHUB_TOKEN}" \
    -H 'X-GitHub-Api-Version: 2022-11-28' \
    "${ACTION_JOB_API_URL}" | jq .jobs[].id)"
  local ACTION_JOB_URL="${GITHUB_SERVER_URL}/${GITHUB_REPOSITORY}/actions/runs/${GITHUB_RUN_ID}/job/${ACTION_JOB_ID}"

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

  select_environment "${BRANCH}"

  if [[ -n "${GITHUB_ACTOR}" && "${GITHUB_EVENT_NAME}" == "workflow_dispatch" ]]; then
    ACTION_RUN_BY="${GITHUB_ACTOR}"
  else
    ACTION_RUN_BY="ci-cd-fhir-user"
  fi

  if [[ -n "${AWS_REGION}" ]]; then
    local AWS_EKS_CLUSTERS_LIST="https://${AWS_REGION}.console.aws.amazon.com/eks/home?region=${AWS_REGION}#/clusters"
  fi

  if (aws sts get-caller-identity --output json &>/dev/null); then
    local AWS_ACCOUNT_ID="$(aws sts get-caller-identity --output json | jq -r '.Account')"
  fi

  if (aws eks list-clusters --no-paginate --output json &>/dev/null); then
    local AWS_EKS_CLUSTERS_COUNT="$(aws eks list-clusters --no-paginate --output json | jq -r '.clusters | length')"
  fi

  curl \
    -s \
    -X POST \
    -H 'Content-Type: application/json' \
    --data '{"username":"GitLabFlow Action","icon_url":"'${ICON_URL}'","text":"*Action run by*: '"${ACTION_RUN_BY}"'\n*Action job URL*: '"${ACTION_JOB_URL}"'\n*Tenant*: '"${TENANT}"'\n*Branch*: '"${BRANCH}"'\n*Status*: '"${STATUS}"'\n*Message*: '"${MESSAGE}"'\n*AWS account ID*: '"${AWS_ACCOUNT_ID}"'\n*AWS region*: '"${AWS_REGION}"'\n*AWS EKS clusters count*: '"${AWS_EKS_CLUSTERS_COUNT}"'\n*AWS EKS clusters list*: '"${AWS_EKS_CLUSTERS_LIST}"'\n"}' \
    "${INPUT_RMK_SLACK_WEBHOOK}"
}

# constants for selecting branches
readonly TASK_NUM_REGEXP="[a-z]\+-\d\+"
readonly SEMVER_REGEXP="v\d\+.\d\+.\d\+\(-rc\)\?\$"

readonly PREFIX_FEATURE_BRANCH="feature"
readonly PREFIX_RELEASE_BRANCH="release"

readonly SELECT_FEATURE_BRANCHES="${PREFIX_FEATURE_BRANCH}/${TASK_NUM_REGEXP}"
readonly SELECT_RELEASE_BRANCHES="${PREFIX_RELEASE_BRANCH}/${TASK_NUM_REGEXP}\|${PREFIX_RELEASE_BRANCH}/${SEMVER_REGEXP}"

readonly SELECT_ORIGIN_FEATURE_BRANCHES="origin/${PREFIX_FEATURE_BRANCH}/${TASK_NUM_REGEXP}"
readonly SELECT_ORIGIN_RELEASE_BRANCHES="origin/${PREFIX_RELEASE_BRANCH}/${TASK_NUM_REGEXP}\|origin/${PREFIX_RELEASE_BRANCH}/${SEMVER_REGEXP}"

readonly SELECT_ALL_BRANCHES="${SELECT_FEATURE_BRANCHES}\|${SELECT_RELEASE_BRANCHES}"
readonly SELECT_ORIGIN_ALL_BRANCHES="${SELECT_ORIGIN_FEATURE_BRANCHES}\|${SELECT_ORIGIN_RELEASE_BRANCHES}"

function check_aws_credentials() {
  if [[ -z "${AWS_REGION}" || -z "${AWS_ACCESS_KEY_ID}" || -z "${AWS_SECRET_ACCESS_KEY}" ]]; then
    >&2 echo "ERROR: For environment ${1} AWS credentials are not configured"
    exit 1
  fi
}

# Define a set of credentials for a specific environment
function export_aws_credentials() {
  # AWS SDKs of different languages might use either AWS_DEFAULT_REGION or AWS_REGION
  case "${1}" in
  develop)
    export AWS_DEFAULT_REGION="${INPUT_CD_DEVELOP_AWS_REGION}"
    export AWS_REGION="${INPUT_CD_DEVELOP_AWS_REGION}"
    export AWS_ACCESS_KEY_ID="${INPUT_CD_DEVELOP_AWS_ACCESS_KEY_ID}"
    export AWS_SECRET_ACCESS_KEY="${INPUT_CD_DEVELOP_AWS_SECRET_ACCESS_KEY}"
    ;;
  staging)
    export AWS_DEFAULT_REGION="${INPUT_CD_STAGING_AWS_REGION}"
    export AWS_REGION="${INPUT_CD_STAGING_AWS_REGION}"
    export AWS_ACCESS_KEY_ID="${INPUT_CD_STAGING_AWS_ACCESS_KEY_ID}"
    export AWS_SECRET_ACCESS_KEY="${INPUT_CD_STAGING_AWS_SECRET_ACCESS_KEY}"
    ;;
  production)
    export AWS_DEFAULT_REGION="${INPUT_CD_PRODUCTION_AWS_REGION}"
    export AWS_REGION="${INPUT_CD_PRODUCTION_AWS_REGION}"
    export AWS_ACCESS_KEY_ID="${INPUT_CD_PRODUCTION_AWS_ACCESS_KEY_ID}"
    export AWS_SECRET_ACCESS_KEY="${INPUT_CD_PRODUCTION_AWS_SECRET_ACCESS_KEY}"
    ;;
  esac

  check_aws_credentials "${1}"
  echo "Selected AWS credentials for ${1}"
  echo "AWS_REGION: ${AWS_REGION}"
  echo "AWS_DEFAULT_REGION: ${AWS_DEFAULT_REGION}"
}

# Define environment by a specific branch name
function select_environment() {
  if echo "${1}" | grep -i "develop\|staging\|production" &> /dev/null; then
    export_aws_credentials "${1}"
    return 0
  fi

  if echo "${1}" | grep -i "${SELECT_FEATURE_BRANCHES}" &> /dev/null; then
    export_aws_credentials develop
    return 0
  fi

  if echo "${1}" | grep -i "${SELECT_RELEASE_BRANCHES}" &> /dev/null; then
    if echo "${1}" | grep -i "${SEMVER_REGEXP}" &> /dev/null; then
      if echo "${1}" | grep -i "\-rc" &> /dev/null; then
        export_aws_credentials staging
        return 0
      fi

      export_aws_credentials production
      return 0
    fi

    export_aws_credentials staging
    return 0
  fi

  >&2 echo "ERROR: Environment \"${1}\" not allowed for environment selection."
  return 1
}

function destroy_clusters() {
  local EXIT_CODE=0

  # grep should be case-insensitive and match the RMK's Golang regex ^[a-z]+-\d+; ^v\d+\.\d+\.\d+-
  for REMOTE_BRANCH in $(git branch -r | grep -i "${SELECT_ORIGIN_ALL_BRANCHES}"); do
    local LOCAL_BRANCH="${REMOTE_BRANCH#origin/}"

    git checkout "${LOCAL_BRANCH}"

    if ! [[ $(git show -s --format=%s | grep -v "\[skip cluster destroy\]") ]]; then
      notify_slack  "Skip" "${LOCAL_BRANCH}" "Cluster destroy skipped"
      echo "Skip cluster destroy for branch: \"${LOCAL_BRANCH}\""
      echo
      continue
    fi

    select_environment "${LOCAL_BRANCH}"

    if ! (rmk config init --progress-bar=false); then
      >&2 echo "ERROR: Config init failed for branch: \"${LOCAL_BRANCH}\""
      echo
      # mark as error because initialization is considered required
      EXIT_CODE=1
      # continue deleting rest of clusters
      continue
    fi

    echo
    echo "Destroying cluster for branch: \"${LOCAL_BRANCH}\""

    if ! (rmk cluster switch); then
      echo "Cluster doesn't exist for branch: \"${LOCAL_BRANCH}\""
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

  if [[ "${INPUT_CHECK_ORPHANED_CLUSTERS}" == "true" ]]; then
    # match EKS clusters (case-insensitive)
    ORPHANED_CLUSTERS="$(aws eks list-clusters --output=json | jq -r '.clusters[] | select(. | test("^'"${TENANT}"'-([a-z]+-\\d+|v\\d+\\.\\d+\\.\\d+(-rc)?)-eks$"; "i"))')"
    echo
    echo "Orphaned clusters:"
    echo "${ORPHANED_CLUSTERS}"
    if [[ "${ORPHANED_CLUSTERS}" != "" ]]; then
      notify_slack "Failure" "N/A" "Orphaned clusters:\n${ORPHANED_CLUSTERS}"
    fi
  fi

  if [[ "${INPUT_CHECK_ORPHANED_VOLUMES}" == "true" ]]; then
    # check all volumes in the region because there is no volume tag with a tenant name in AWS
    ORPHANED_VOLUMES="$(aws ec2 describe-volumes --output=json --filters "Name=status,Values=[available,error]" \
      | jq -r '.Volumes[] | (.CreateTime + " " + .AvailabilityZone + " " +  .VolumeId + " " + (.Tags | map(select(.Key=="Name" or .Key=="kubernetes.io/created-for/pvc/name") | .Value) | join(" ")) + " " + .State + " " + .VolumeType + " "  + (.Size | tostring) + "GiB")')"
    echo
    echo "Orphaned volumes:"
    echo "${ORPHANED_VOLUMES}"
    if [[ "${ORPHANED_VOLUMES}" != "" ]]; then
      notify_slack "Failure" "N/A" "Orphaned volumes:\n${ORPHANED_VOLUMES}" "N/A"
    fi
  fi

  exit ${EXIT_CODE}
}

function check_cluster_provision_command_valid() {
  if ! [[ "${INPUT_RMK_COMMAND}" =~ provision|destroy ]]; then
    >&2 echo "ERROR: For cluster provisioning and destroy, only the following commands are allowed: provision destroy"
    exit 1
  fi
}

echo
echo "Initialize environment variables."

git config --global "user.name" "github-actions"
git config --global "user.email" "github-actions@github.com"
git config --global --add "safe.directory" "/github/workspace"

# exports are required by the installer scripts and rmk
export GITHUB_TOKEN="${INPUT_GITHUB_TOKEN_REPO_FULL_ACCESS}"
export CLOUDFLARE_TOKEN="${INPUT_CLOUDFLARE_TOKEN}"
export GITHUB_ORG="${GITHUB_REPOSITORY%%/*}"

GIT_BRANCH="${GITHUB_REF#refs/heads/}"
ENVIRONMENT="${GIT_BRANCH}"
REPOSITORY_FULL_NAME="${INPUT_REPOSITORY_FULL_NAME}"
VERSION="${INPUT_VERSION}"

echo
echo "Install RMK."
curl -sL "https://edenlabllc-rmk-tools-infra.s3.eu-north-1.amazonaws.com/rmk/s3-installer" | bash -s -- "${INPUT_RMK_VERSION}"
rmk --version

export TENANT=$(echo "${GITHUB_REPOSITORY}" | cut -d '/' -f2 | cut -d '.' -f1)

if [[ "${INPUT_DESTROY_CLUSTERS}" == "true" ]]; then
  if [[ "${INPUT_CLUSTER_PROVISIONER}" == "true" ]]; then
    >&2 echo "ERROR: Inputs cluster_provisioner and destroy_clusters can't be provided simultaneously."
    exit 1
  fi

  destroy_clusters
fi

if [[ "${GITHUB_REF}" != refs/heads/* ]]; then
  >&2 echo "ERROR: Only pushes to branches are supported. Check the workflow's on.push.* section."
  exit 1
fi

if [[ "${INPUT_CLUSTER_PROVISIONER}" == "true" ]]; then
  # transform to lowercase for case-insensitive matching
  if echo "${ENVIRONMENT}" | grep -i "${SELECT_ALL_BRANCHES}" &> /dev/null; then
    echo
    echo "Skipped checking allowed environments."
    echo "Preparing temporary cluster for branch: \"${ENVIRONMENT}\""
    check_cluster_provision_command_valid
  else
    >&2 echo "ERROR: Provisioning temporary clusters is only allowed for the following branch prefixes
      (case-insensitive): feature/ffs-* release/rc-* release/vX.X.X-rc release/vX.X.X"
    exit 1
  fi
elif [[ "${INPUT_RMK_COMMAND}" != "reindex" && "${INPUT_ROUTES_TEST}" != "true" ]]; then
  ALLOWED_ENVIRONMENTS=("${INPUT_ALLOWED_ENVIRONMENTS/,/ }")
  if [[ ! " ${ALLOWED_ENVIRONMENTS[*]} " =~ " ${ENVIRONMENT} " ]]; then
    >&2 echo "ERROR: Environment \"${ENVIRONMENT}\" not allowed for automatic CD."
    exit 1
  fi
fi

select_environment "${ENVIRONMENT}"

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
    >&2 echo "ERROR: Failed to get list of releases for branch: \"${ENVIRONMENT}\""
    exit 1
  fi

  if ! (rmk release destroy); then
    notify_slack "Failure" "${ENVIRONMENT}" "Destroying releases failed"
    exit 1
  fi

  if ! (rmk cluster provision --plan); then
    >&2 echo "ERROR: Failed to prepare terraform plan for branch: \"${ENVIRONMENT}\""
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

  if ! (rmk cluster provision); then
    notify_slack "Failure" "${ENVIRONMENT}" "Cluster provisioning failed"
    exit 1
  fi

  if ! (rmk release list); then
    >&2 echo "ERROR: Failed to get list of releases for branch: \"${ENVIRONMENT}\""
    notify_slack "Failure" "${ENVIRONMENT}" "Failed to get list of releases"
    exit 1
  fi

  if ! (rmk release sync); then
    notify_slack "Failure" "${ENVIRONMENT}" "Release sync failed"
    exit 1
  fi

  notify_slack "Success" "${ENVIRONMENT}" "Cluster has been provisioned"
  ;;
sync)
  FLAGS_LABELS=""
  if [[ "${INPUT_RMK_SYNC_LABELS}" != "" ]]; then
    for LABEL in ${INPUT_RMK_SYNC_LABELS}; do
      FLAGS_LABELS="${FLAGS_LABELS} -l ${LABEL}"
    done
  fi

  rmk release -- ${FLAGS_LABELS} sync
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
