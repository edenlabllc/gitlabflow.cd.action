#!/bin/bash
set -e

################################
############ CD part ###########
################################

echo
echo "Initialize environment variables."

GITHUB_ORG="${GITHUB_REPOSITORY%%/*}"

if [[ "${GITHUB_REF}" != refs/heads/* ]]; then
  >&2 echo "Only pushes to branches are supported. Check the workflow's on.push.* section."
  exit 1
fi
GIT_BRANCH="${GITHUB_REF#refs/heads/}"

ENVIRONMENT="${GIT_BRANCH}"
ALLOWED_ENVIRONMENTS=("develop" "staging")

if [[ ! " ${ALLOWED_ENVIRONMENTS[*]} " =~ " ${ENVIRONMENT} " ]]; then
    >&2 echo "Environment \"${ENVIRONMENT}\" not allowed for automatic CD."
    exit 1
fi

REPOSITORY_FULL_NAME="${INPUT_REPOSITORY_FULL_NAME}"
VERSION="${INPUT_VERSION}"

# exports are required by the installer scripts and rmk
export CLOUDFLARE_TOKEN="${INPUT_CLOUDFLARE_TOKEN}"
export GITHUB_TOKEN="${INPUT_GITHUB_TOKEN_REPO_FULL_ACCESS}"
export CI_CD_TOOLS_VERSION="${INPUT_CI_CD_TOOLS_VERSION}"

case "${ENVIRONMENT}" in
  develop)
    export AWS_REGION="${INPUT_CD_DEVELOP_AWS_REGION}"
    export AWS_ACCESS_KEY_ID="${INPUT_CD_DEVELOP_AWS_ACCESS_KEY_ID}"
    export AWS_SECRET_ACCESS_KEY="${INPUT_CD_DEVELOP_AWS_SECRET_ACCESS_KEY}"
    ;;
  staging)
    export AWS_REGION="${INPUT_CD_STAGING_AWS_REGION}"
    export AWS_ACCESS_KEY_ID="${INPUT_CD_STAGING_AWS_ACCESS_KEY_ID}"
    export AWS_SECRET_ACCESS_KEY="${INPUT_CD_STAGING_AWS_SECRET_ACCESS_KEY}"
    ;;
esac

echo
echo "Install rmk and dependencies, initialize configuration, run CD."

git config user.name github-actions
git config user.email github-actions@github.com

curl -sL "https://${GITHUB_TOKEN}@raw.githubusercontent.com/${GITHUB_ORG}/rmk.tools.infra/${CI_CD_TOOLS_VERSION}/bin/installer" | bash

rmk --version
rmk config init --progress-bar=false

case "${INPUT_RMK_COMMAND}" in
  update)
    if [[ "${INPUT_RMK_UPDATE_HELMFILE_REPOS_COMMAND}" != "" ]]; then
      rmk release "${INPUT_RMK_UPDATE_HELMFILE_REPOS_COMMAND}"
    fi

    rmk release update --repository "${REPOSITORY_FULL_NAME}" --tag "${VERSION}" --skip-actions --deploy
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
esac

# always output action variables
echo "::set-output name=git_branch::${GIT_BRANCH}"
echo "::set-output name=environment::${ENVIRONMENT}"
echo "::set-output name=repository_full_name::${REPOSITORY_FULL_NAME}"
echo "::set-output name=version::${VERSION}"
