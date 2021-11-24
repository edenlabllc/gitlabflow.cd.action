#!/bin/bash
set -e

REPOSITORY_NAME="${1}"
VERSION="${2}"
GIT_BRANCH="${3}"
SCAN_IMAGE="${4}"
DELETE_IMAGE="${5}"

function scan_image() {
  IMPORTANT_VULNERABILITIES=".CRITICAL, .HIGH, .MEDIUM, .UNDEFINED"
  IGNORED_VULNERABILITIES=".LOW"
  SLEEP=3

  echo "Important vulnerabilities to be scanned: ${IMPORTANT_VULNERABILITIES//./}"
  echo "Ignored vulnerabilities: ${IGNORED_VULNERABILITIES//./}"

  # for asynchronous scanning and alerting use ECR events and EventBridge:
  # https://docs.aws.amazon.com/AmazonECR/latest/userguide/ecr-eventbridge.html
  while true; do
    IMAGE_SCAN_RESULT="$(aws ecr describe-image-scan-findings --repository-name "${REPOSITORY_NAME}" --image-id "imageTag=${VERSION}")"
    IMAGE_SCAN_STATUS="$(echo "${IMAGE_SCAN_RESULT}" | jq -r '.imageScanStatus.status')"
    IMAGE_SCAN_DESCRIPTION="$(echo "${IMAGE_SCAN_RESULT}" | jq -r '.imageScanStatus.description')"

    echo
    echo "Current image scan status:"
    echo "${IMAGE_SCAN_STATUS}"
    [[ "null" != "${IMAGE_SCAN_DESCRIPTION}" ]] && echo "${IMAGE_SCAN_DESCRIPTION}"

    if [[ "${IMAGE_SCAN_STATUS}" == "COMPLETE" ]]; then
      echo
      VULNERABILITIES_COUNT="$(echo "${IMAGE_SCAN_RESULT}" | jq -r '.imageScanFindings.findingSeverityCounts | ['"${IMPORTANT_VULNERABILITIES}"' // 0] | add')"
      echo "Important vulnerabilities total: ${VULNERABILITIES_COUNT}"

      echo
      echo "All vulnerabilities subtotals:"
      echo "${IMAGE_SCAN_RESULT}" | jq -r '.imageScanFindings.findingSeverityCounts'

      echo
      echo "All vulnerabilities:"
      echo "${IMAGE_SCAN_RESULT}" | jq -r '.imageScanFindings.findings'

      echo
      if [[ "${VULNERABILITIES_COUNT}" -eq "0" ]]; then
        echo "Image has no important vulnerabilities."
        return
      else
        >&2 echo "Image has important vulnerabilities. Fix the image and push the changes."
        return 1
      fi
    elif [[ "${IMAGE_SCAN_STATUS}" == "FAILED" ]]; then
      >&2 echo "Image scan has failed. Fix the image and push the changes."
      return 1
    else
      echo "Waiting for ${SLEEP} seconds..."
      sleep "${SLEEP}"
    fi
  done
}

echo
echo "Scan image for vulnerabilities (only if scan_image=true)."
IMAGE_SCAN_FAILED="false"
if [[ "${SCAN_IMAGE}" == "true" ]] && ! scan_image; then
  IMAGE_SCAN_FAILED="true"
else
  echo "Skipped."
fi

echo
echo "Delete image from AWS ECR repository (only for branches except master, develop and if delete_image=true)."
if [[ "master" != "${GIT_BRANCH}" && "develop" != "${GIT_BRANCH}" && "${DELETE_IMAGE}" == "true" ]]; then
  aws ecr batch-delete-image \
     --repository-name "${REPOSITORY_NAME}" \
     --image-ids imageTag="${VERSION}"
else
  echo "Skipped."
fi

if [[ "${IMAGE_SCAN_FAILED}" == "true" ]]; then
  >&2 echo "Exiting because image scan has failed."
  exit 1
fi
