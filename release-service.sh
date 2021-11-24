#!/bin/bash
set -e

VERSION="${1}"
GIT_BRANCH="${2}"
GITHUB_SHA="${3}"
RELEASE_FILES="${4}"

echo
echo "Release service (only for master)."
if [[ "master" == "${GIT_BRANCH}" ]]; then
  echo "Configure Git user.name and user.email."
  git config user.name github-actions
  git config user.email github-actions@github.com

  RELEASE_MSG="Release ${VERSION}"

  echo "Add Git tag ${VERSION}."
  git tag -a "${VERSION}" -m "${RELEASE_MSG}"
  git push origin "${VERSION}" -f

  if gh release view "${VERSION}" &> /dev/null; then
    echo "GitHub release ${VERSION} already exists."
    echo "Skipped."
  else
    echo "Create GitHub release ${VERSION}."
    gh release create "${VERSION}" --target "${GITHUB_SHA}" --notes "${RELEASE_MSG}" ${RELEASE_FILES}
  fi
else
  echo "Skipped."
fi
