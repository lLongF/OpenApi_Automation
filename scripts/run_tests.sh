#!/usr/bin/env bash
set -euo pipefail

ENV_NAME="${TEST_ENV:-dev}"
MARK_EXPR="${1:-}"

mkdir -p reports/allure-results reports/allure-report

if [[ -n "${MARK_EXPR}" ]]; then
  python3 -m pytest --env "${ENV_NAME}" --live -m "${MARK_EXPR}"
else
  python3 -m pytest --env "${ENV_NAME}" --live
fi

if command -v allure >/dev/null 2>&1; then
  allure generate reports/allure-results -o reports/allure-report --clean
  echo "Allure report: file://${PWD}/reports/allure-report/index.html"
else
  echo "Allure CLI not found."
fi
echo "Pytest HTML report: file://${PWD}/reports/report.html"
