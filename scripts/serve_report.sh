#!/usr/bin/env bash
set -euo pipefail

PORT="${1:-8088}"
echo "Serving reports at: http://127.0.0.1:${PORT}/"
echo "Pytest HTML:       http://127.0.0.1:${PORT}/report.html"
echo "Allure HTML:       http://127.0.0.1:${PORT}/allure-report/index.html"
python3 -m http.server "${PORT}" --directory reports
