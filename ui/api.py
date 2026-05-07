"""
Veille Agent — FastAPI Backend
Routes : scan, rapports, concurrents, historique, planification
"""

import sys
import json
import os
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from apscheduler.schedulers.background import BackgroundScheduler

app = FastAPI(title="Veille Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="ui/static"), name="static")

# ─── Paths ───────────────────────────────────────────────────────────────────

ROOT = Path(__file__).parent.parent
REPORTS_DIR = ROOT / "output" / "reports"
SNAPSHOTS_DIR = ROOT / "storage" / "snapshots"
SCANS_LOG = ROOT / "storage" / "scans.json"
SCHEDULE_CONFIG = ROOT / "storage" / "schedule.json"

REPORTS_DIR.mkdir(parents=True, exist_ok=True)
SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)

# ─── Scan state ──────────────────────────────────────────────────────────────

scan_status = {"running": False, "sector": "", "step": "", "error": ""}


def load_scans_log() -> list:
    if not SCANS_LOG.exists():
        return []
    with open(SCANS_LOG) as f:
        return json.load(f)


def save_scan_log(entry: dict):
    logs = load_scans_log()
    logs.insert(0, entry)
    with open(SCANS_LOG, "w") as f:
        json.dump(logs[:50], f, indent=2, ensure_ascii=False)


# ─── Models ──────────────────────────────────────────────────────────────────

class ScanRequest(BaseModel):
    sector: str
    max_competitors: int = 5


class ScheduleConfig(BaseModel):
    enabled: bool
    sector: str
    max_competitors: int = 5
    day_of_week: str = "monday"
    hour: int = 8


# ─── Background scan ─────────────────────────────────────────────────────────

def run_scan_background(sector: str, max_competitors: int):
    global scan_status
    scan_status = {"running": True, "sector": sector, "step": "Démarrage...", "error": ""}
    start = datetime.now()

    try:
        from main import run
        import discovery_agent.discovery as disc_mod
        import scraper_agent.scraper as scrap_mod
        import social_agent.social as soc_mod

        original_discovery = disc_mod.run_discovery
        original_scraper = scrap_mod.run_scraper
        original_social = soc_mod.run_social

        def patched_discovery(*args, **kwargs):
            scan_status["step"] = "🔍 Identification des concurrents..."
            return original_discovery(*args, **kwargs)

        def patched_scraper(*args, **kwargs):
            scan_status["step"] = "🌐 Scraping des sites web..."
            return original_scraper(*args, **kwargs)

        def patched_social(*args, **kwargs):
            scan_status["step"] = "📱 Collecte des données sociales..."
            return original_social(*args, **kwargs)

        disc_mod.run_discovery = patched_discovery
        scrap_mod.run_scraper = patched_scraper
        soc_mod.run_social = patched_social

        scan_status["step"] = "🔍 Identification des concurrents..."
        result = run(sector, max_competitors)

        duration = round((datetime.now() - start).total_seconds(), 1)
        save_scan_log({
            "sector": sector,
            "date": datetime.now().isoformat(),
            "duration_s": duration,
            "report_path": result.get("report_path", ""),
            "competitors": [c.get("name") for c in result.get("competitors", [])],
            "changes": sum(1 for d in result.get("diffs", []) if d.get("has_changes")),
        })

        # Notifications si signaux prioritaires (score >= 7)
        high_priority = [
            c for c in result.get("analysis", {}).get("competitors", [])
            if c.get("score", 0) >= 7
        ]
        if high_priority:
            from notifier.notify import notify_changes
            notify_changes(sector, high_priority, result.get("report_path", ""))

        scan_status = {"running": False, "sector": sector, "step": "✅ Terminé", "error": ""}

    except Exception as e:
        scan_status = {"running": False, "sector": sector, "step": "Erreur", "error": str(e)}


# ─── Scheduler ───────────────────────────────────────────────────────────────

scheduler = BackgroundScheduler()
scheduler.start()


def load_schedule_config() -> dict:
    if not SCHEDULE_CONFIG.exists():
        return {"enabled": False, "sector": "", "max_competitors": 5, "day_of_week": "monday", "hour": 8}
    return json.loads(SCHEDULE_CONFIG.read_text())


def save_schedule_config(config: dict):
    SCHEDULE_CONFIG.write_text(json.dumps(config, indent=2, ensure_ascii=False))


def apply_schedule(config: dict):
    scheduler.remove_all_jobs()
    if config.get("enabled") and config.get("sector"):
        scheduler.add_job(
            run_scan_background,
            "cron",
            day_of_week=config["day_of_week"],
            hour=config["hour"],
            minute=0,
            args=[config["sector"], config.get("max_competitors", 5)],
            id="weekly_scan",
        )
        print(f"[SCHEDULE] Scan planifié : {config['day_of_week']} à {config['hour']}h00 — {config['sector']}")


apply_schedule(load_schedule_config())


# ─── Routes ──────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index():
    return FileResponse("ui/templates/index.html")


@app.post("/api/scan")
async def start_scan(req: ScanRequest, background_tasks: BackgroundTasks):
    if scan_status["running"]:
        raise HTTPException(400, "Un scan est déjà en cours")
    background_tasks.add_task(run_scan_background, req.sector, req.max_competitors)
    return {"message": "Scan démarré", "sector": req.sector}


@app.get("/api/scan/status")
async def get_scan_status():
    return scan_status


@app.get("/api/reports")
async def list_reports():
    reports = []
    for f in sorted(REPORTS_DIR.glob("*.md"), reverse=True):
        stat = f.stat()
        reports.append({
            "name": f.name,
            "path": str(f),
            "size_kb": round(stat.st_size / 1024, 1),
            "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        })
    return reports


@app.get("/api/reports/{filename}/download")
async def download_report(filename: str):
    path = REPORTS_DIR / filename
    if not path.exists():
        raise HTTPException(404, "Rapport introuvable")
    return FileResponse(path, media_type="text/markdown", filename=filename)


@app.get("/api/reports/{filename}")
async def get_report(filename: str):
    path = REPORTS_DIR / filename
    if not path.exists():
        raise HTTPException(404, "Rapport introuvable")
    return {"content": path.read_text(encoding="utf-8"), "filename": filename}


@app.get("/api/competitors")
async def list_competitors():
    competitors = []
    for f in SNAPSHOTS_DIR.glob("*.json"):
        try:
            data = json.loads(f.read_text())
            competitors.append({
                "slug": f.stem,
                "name": data.get("name", f.stem),
                "website": data.get("website", ""),
                "last_scan": data.get("_saved_at", ""),
            })
        except:
            pass
    return sorted(competitors, key=lambda x: x["last_scan"], reverse=True)


@app.delete("/api/competitors/{slug}")
async def delete_competitor(slug: str):
    path = SNAPSHOTS_DIR / f"{slug}.json"
    if path.exists():
        path.unlink()
    return {"message": f"{slug} supprimé"}


@app.get("/api/history")
async def get_history():
    return load_scans_log()


@app.get("/api/history/{slug}")
async def get_competitor_history(slug: str):
    path = SNAPSHOTS_DIR / f"{slug}.json"
    if not path.exists():
        raise HTTPException(404, "Concurrent introuvable")
    return json.loads(path.read_text())


@app.get("/api/schedule")
async def get_schedule():
    return load_schedule_config()


@app.post("/api/schedule")
async def update_schedule(config: ScheduleConfig):
    c = config.model_dump()
    save_schedule_config(c)
    apply_schedule(c)
    return {"message": "Planification mise à jour"}
