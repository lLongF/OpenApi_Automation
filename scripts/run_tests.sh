#!/usr/bin/env bash
set -euo pipefail

ENV_NAME="${TEST_ENV:-dev}"
MARK_EXPR="${1:-}"
export ALLURE_NO_ANALYTICS=1

mkdir -p reports/allure-results reports/allure-report

LOCAL_ALLURE="${PWD}/tools/allure/bin/allure"

if [[ -n "${MARK_EXPR}" ]]; then
  python3 -m pytest --env "${ENV_NAME}" --live -m "${MARK_EXPR}"
else
  python3 -m pytest --env "${ENV_NAME}" --live
fi

if [[ -x "${LOCAL_ALLURE}" ]]; then
  "${LOCAL_ALLURE}" generate reports/allure-results -o reports/allure-report --clean
  echo "Allure report: file://${PWD}/reports/allure-report/index.html"
elif command -v allure >/dev/null 2>&1; then
  allure generate reports/allure-results -o reports/allure-report --clean
  echo "Allure report: file://${PWD}/reports/allure-report/index.html"
else
  echo "Allure CLI not found. On Windows run: powershell -ExecutionPolicy Bypass -File scripts/install_allure.ps1"
fi
echo "Pytest HTML report: file://${PWD}/reports/report.html"
