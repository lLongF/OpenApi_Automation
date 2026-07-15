from __future__ import annotations

import json
import shutil
import subprocess
import sys
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.responses import Response
from pydantic import BaseModel, Field


ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIR = ROOT / "web" / "frontend"
REPORTS_DIR = ROOT / "reports"
RUNS_DIR = REPORTS_DIR / "runs"
TEST_DATA_DIR = ROOT / "data" / "test_data"
ENV_PATH = ROOT / "config" / "env.yaml"

MODULE_TEST_TARGETS = {
    "voice_clone": "tests/test_voice.py::test_voice_clone",
    "voice_infer": "tests/test_voice.py::test_voice_infer",
    "timbre_design": "tests/test_timbre_design.py",
    "videots": "tests/test_videots.py",
    "subtitle_erase": "tests/test_subtitle_erase.py",
    "asr": "tests/test_asr.py",
    "speaker_classify": "tests/test_speaker_classify.py",
    "voice_separate": "tests/test_voice_separate.py",
    "video_compose": "tests/test_video_compose.py",
}


class RunRequest(BaseModel):
    env: str = "dev"
    live: bool = True
    marker: str | None = None
    module: str | None = None
    no_openapi_case_sync: bool = True


class RunSummary(BaseModel):
    id: str
    status: str
    env: str
    live: bool
    marker: str | None = None
    module: str | None = None
    target: str
    command: list[str]
    created_at: str
    started_at: str | None = None
    finished_at: str | None = None
    exit_code: int | None = None
    log_url: str
    report_url: str


class CaseUpdateRequest(BaseModel):
    case: dict[str, Any] = Field(default_factory=dict)


app = FastAPI(title="OpenAPI Automation Console")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

RUNS: dict[str, RunSummary] = {}
NO_CACHE_HEADERS = {
    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
    "Pragma": "no-cache",
    "Expires": "0",
}


class NoCacheStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope) -> Response:
        response = await super().get_response(path, scope)
        response.headers.update(NO_CACHE_HEADERS)
        return response


@app.on_event("startup")
def startup() -> None:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    _load_existing_runs()


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/envs")
def list_envs() -> dict[str, Any]:
    raw = _read_yaml(ENV_PATH)
    environments = raw.get("environments") or {}
    return {
        "default": raw.get("default"),
        "items": [
            {
                "name": name,
                "base_url": item.get("base_url"),
                "user_id": item.get("user_id"),
                "api_key_env": item.get("api_key_env"),
            }
            for name, item in environments.items()
        ],
    }


@app.get("/api/cases")
def list_cases() -> dict[str, Any]:
    modules = []
    for path in sorted(TEST_DATA_DIR.glob("*.yaml")):
        raw = _read_yaml(path)
        for name, value in raw.items():
            if not isinstance(value, dict):
                continue
            groups = _case_groups(value)
            if not groups:
                continue
            cases = []
            for group_name, group_cases in groups.items():
                for case in group_cases:
                    case_item = dict(case)
                    case_item["__case_group"] = group_name
                    cases.append(case_item)
            modules.append(
                {
                    "name": name,
                    "file": str(path.relative_to(ROOT)).replace("\\", "/"),
                    "target": MODULE_TEST_TARGETS.get(name, "tests"),
                    "case_count": len(cases),
                    "cases": cases,
                }
            )
    return {"modules": modules}


@app.post("/api/cases/{module_name}")
def add_case(module_name: str, request: CaseUpdateRequest) -> dict[str, Any]:
    path, raw, section = _find_case_module(module_name)
    case = _clean_case(request.case)
    group_name = request.case.get("__case_group") or "cases"
    cases = section.setdefault(group_name, [])
    if not case.get("id"):
        raise HTTPException(status_code=400, detail="case.id is required")
    if any(item.get("id") == case["id"] for item in _all_cases(section)):
        raise HTTPException(status_code=409, detail=f"case id already exists: {case['id']}")
    cases.append(case)
    _write_yaml(path, raw)
    return {"ok": True, "file": str(path.relative_to(ROOT)).replace("\\", "/")}


@app.put("/api/cases/{module_name}/{case_id}")
def update_case(module_name: str, case_id: str, request: CaseUpdateRequest) -> dict[str, Any]:
    path, raw, section = _find_case_module(module_name)
    updated_case = _clean_case(request.case)
    for cases in _case_groups(section).values():
        for index, item in enumerate(cases):
            if item.get("id") == case_id:
                cases[index] = updated_case
                _write_yaml(path, raw)
                return {"ok": True, "file": str(path.relative_to(ROOT)).replace("\\", "/")}
    raise HTTPException(status_code=404, detail=f"case not found: {case_id}")


@app.post("/api/runs", response_model=RunSummary)
def start_run(request: RunRequest) -> RunSummary:
    target = MODULE_TEST_TARGETS.get(request.module or "", "tests")
    if request.module and target == "tests":
        raise HTTPException(status_code=404, detail=f"unknown module: {request.module}")

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S_") + uuid.uuid4().hex[:6]
    run_dir = RUNS_DIR / run_id
    results_dir = run_dir / "allure-results"
    run_dir.mkdir(parents=True, exist_ok=True)
    results_dir.mkdir(parents=True, exist_ok=True)

    command = [
        sys.executable,
        "-m",
        "pytest",
        target,
        "--env",
        request.env,
        "--alluredir",
        str(results_dir),
        "--clean-alluredir",
    ]
    if request.live:
        command.append("--live")
    if request.marker:
        command.extend(["-m", request.marker])
    if request.no_openapi_case_sync:
        command.append("--no-openapi-case-sync")

    summary = RunSummary(
        id=run_id,
        status="queued",
        env=request.env,
        live=request.live,
        marker=request.marker,
        module=request.module,
        target=target,
        command=command,
        created_at=_now(),
        log_url=f"/api/runs/{run_id}/log",
        report_url=f"/api/runs/{run_id}/allure-report/index.html",
    )
    RUNS[run_id] = summary
    _save_run(summary)

    thread = threading.Thread(target=_run_pytest, args=(summary, run_dir), daemon=True)
    thread.start()
    return summary


@app.get("/api/runs")
def list_runs() -> dict[str, Any]:
    return {"runs": sorted(RUNS.values(), key=lambda item: item.created_at, reverse=True)}


@app.get("/api/runs/{run_id}", response_model=RunSummary)
def get_run(run_id: str) -> RunSummary:
    run = RUNS.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"run not found: {run_id}")
    return run


@app.get("/api/runs/{run_id}/log")
def get_run_log(run_id: str) -> dict[str, str]:
    run_dir = RUNS_DIR / run_id
    log_path = run_dir / "stdout.log"
    if not log_path.exists():
        return {"log": ""}
    return {"log": log_path.read_text(encoding="utf-8", errors="replace")}


@app.get("/api/runs/{run_id}/allure-report")
def get_run_allure_index(run_id: str) -> FileResponse:
    return get_run_allure_file(run_id, "index.html")


@app.get("/api/runs/{run_id}/allure-report/{path:path}")
def get_run_allure_file(run_id: str, path: str) -> FileResponse:
    relative = Path(path)
    if relative.is_absolute() or ".." in relative.parts:
        raise HTTPException(status_code=404, detail="report file not found")

    file_path = RUNS_DIR / run_id / "allure-report" / relative
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="report file not found")
    return FileResponse(file_path, headers=NO_CACHE_HEADERS)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")
app.mount("/allure-report", NoCacheStaticFiles(directory=REPORTS_DIR / "allure-report", html=True), name="allure-report")


def _run_pytest(summary: RunSummary, run_dir: Path) -> None:
    log_path = run_dir / "stdout.log"
    summary.status = "running"
    summary.started_at = _now()
    _save_run(summary)

    with log_path.open("w", encoding="utf-8", errors="replace") as log:
        log.write("Command: " + " ".join(summary.command) + "\n\n")
        log.flush()
        process = subprocess.Popen(
            summary.command,
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        assert process.stdout is not None
        for line in process.stdout:
            log.write(line)
            log.flush()
        summary.exit_code = process.wait()
        _generate_run_allure_report(run_dir, log)

    summary.finished_at = _now()
    summary.status = "passed" if summary.exit_code == 0 else "failed"
    _save_run(summary)


def _read_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        loaded = yaml.safe_load(file) or {}
    if not isinstance(loaded, dict):
        raise HTTPException(status_code=500, detail=f"YAML root must be object: {path}")
    return loaded


def _write_yaml(path: Path, data: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as file:
        yaml.safe_dump(data, file, allow_unicode=True, sort_keys=False)


def _find_case_module(module_name: str) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    for path in sorted(TEST_DATA_DIR.glob("*.yaml")):
        raw = _read_yaml(path)
        section = raw.get(module_name)
        if isinstance(section, dict) and _case_groups(section):
            return path, raw, section
    raise HTTPException(status_code=404, detail=f"module not found: {module_name}")


def _case_groups(section: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    groups = {}
    for key, value in section.items():
        if key == "cases" or key.endswith("_cases"):
            if isinstance(value, list):
                groups[key] = value
    return groups


def _all_cases(section: dict[str, Any]) -> list[dict[str, Any]]:
    cases = []
    for value in _case_groups(section).values():
        cases.extend(value)
    return cases


def _clean_case(case: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in case.items() if not key.startswith("__")}


def _save_run(summary: RunSummary) -> None:
    run_dir = RUNS_DIR / summary.id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "run.json").write_text(json.dumps(summary.model_dump(), indent=2, ensure_ascii=False), encoding="utf-8")


def _load_existing_runs() -> None:
    for path in RUNS_DIR.glob("*/run.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            data["report_url"] = f"/api/runs/{data['id']}/allure-report/index.html"
            RUNS[data["id"]] = RunSummary(**data)
        except Exception:
            continue


def _generate_run_allure_report(run_dir: Path, log) -> None:
    results_dir = run_dir / "allure-results"
    report_dir = run_dir / "allure-report"
    if not results_dir.exists():
        return

    allure = _find_allure_cli()
    if allure is None:
        log.write("\nAllure CLI not found, skip per-run HTML report generation.\n")
        log.flush()
        return

    command = [str(allure), "generate", str(results_dir), "-o", str(report_dir), "--clean"]
    completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    if completed.returncode == 0:
        log.write(f"\nPer-run Allure report generated: {report_dir / 'index.html'}\n")
    else:
        log.write("\nPer-run Allure report generation failed.\n")
        if completed.stdout:
            log.write(completed.stdout)
        if completed.stderr:
            log.write(completed.stderr)
    log.flush()


def _find_allure_cli() -> Path | None:
    local_allure = ROOT / "tools" / "allure" / "bin" / "allure.bat"
    if local_allure.exists():
        return local_allure

    command = shutil.which("allure")
    return Path(command) if command else None


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")
