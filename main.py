"""
Veille Concurrentielle Agent — LangGraph Pipeline
Orchestration : Discovery → Scraper + Social (parallèle) → Diff → Analysis → Report
"""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from typing import TypedDict
from dataclasses import asdict
from datetime import datetime
from langgraph.graph import StateGraph, END
from dotenv import load_dotenv
load_dotenv()

from adapters.llm.openrouter import OpenRouterLLMClient
from adapters.search.duckduckgo import DuckDuckGoSearchEngine
from adapters.social.scraper import PublicSocialScraper
from adapters.storage.snapshot_repository import JsonSnapshotRepository
from adapters.web.scraper import HttpWebScraper
from application.discovery import DiscoveryService
from application.diff import DiffService
from application.scraper import ScraperService
from application.social import SocialService
from domain.models import Competitor, CompetitorDiff, SocialData, WebData
from analysis_agent.analysis import run_analysis
from report_agent.report import run_report

_discovery_service: DiscoveryService | None = None
_scraper_service: ScraperService | None = None
_social_service: SocialService | None = None
_diff_service: DiffService | None = None


def _get_discovery_service() -> DiscoveryService:
    global _discovery_service
    if _discovery_service is None:
        _discovery_service = DiscoveryService(
            llm=OpenRouterLLMClient(api_key=os.environ["OPENROUTER_API_KEY"], model="anthropic/claude-haiku-4-5"),
            search=DuckDuckGoSearchEngine(),
        )
    return _discovery_service


def _get_scraper_service() -> ScraperService:
    global _scraper_service
    if _scraper_service is None:
        _scraper_service = ScraperService(scraper=HttpWebScraper())
    return _scraper_service


def _get_social_service() -> SocialService:
    global _social_service
    if _social_service is None:
        _social_service = SocialService(scraper=PublicSocialScraper())
    return _social_service


def _get_diff_service() -> DiffService:
    global _diff_service
    if _diff_service is None:
        _diff_service = DiffService(repository=JsonSnapshotRepository())
    return _diff_service


def _diff_to_legacy_dict(diff: CompetitorDiff) -> dict:
    return {
        "name": diff.name,
        "changes": [{"type": c.change_type.value, "description": c.description} for c in diff.changes],
        "has_changes": diff.has_changes,
        "data": asdict(diff.snapshot),
        "scanned_at": diff.scanned_at,
    }


# ─── State ───────────────────────────────────────────────────────────────────

class VeilleState(TypedDict):
    sector: str                    # Secteur / mot-clé en entrée
    max_competitors: int           # Nombre de concurrents à surveiller
    competitors: list[dict]        # Liste découverte par discovery agent
    web_data: list[dict]           # Données scrapées des sites
    social_data: list[dict]        # Données sociales (LinkedIn, Twitter)
    diffs: list[dict]              # Changements vs snapshots précédents
    analysis: dict                 # Analyse et scores LLM
    report_path: str               # Chemin du rapport généré
    trace: dict                    # Métriques d'exécution


# ─── Nodes ───────────────────────────────────────────────────────────────────

def discovery_node(state: VeilleState) -> VeilleState:
    print(f"\n🔍 [DISCOVERY] Identification des concurrents...")
    t = datetime.now()
    competitors = _get_discovery_service().discover(state["sector"], state["max_competitors"])
    state["competitors"] = [asdict(c) for c in competitors]
    state["trace"]["discovery"] = {"duration_s": round((datetime.now() - t).total_seconds(), 2), "count": len(competitors)}
    print(f"   ✅ {len(competitors)} concurrents trouvés")
    return state


def scraper_node(state: VeilleState) -> VeilleState:
    print(f"\n🌐 [SCRAPER] Scraping des sites web...")
    t = datetime.now()
    competitors = [Competitor(**c) for c in state["competitors"]]
    web_data = _get_scraper_service().scrape_all(competitors)
    state["web_data"] = [asdict(w) for w in web_data]
    state["trace"]["scraper"] = {"duration_s": round((datetime.now() - t).total_seconds(), 2)}
    print(f"   ✅ {len(web_data)} sites scrapés")
    return state


def social_node(state: VeilleState) -> VeilleState:
    print(f"\n📱 [SOCIAL] Collecte des posts sociaux...")
    t = datetime.now()
    competitors = [Competitor(**c) for c in state["competitors"]]
    social_data = _get_social_service().collect_all(competitors)
    state["social_data"] = [asdict(s) for s in social_data]
    state["trace"]["social"] = {"duration_s": round((datetime.now() - t).total_seconds(), 2)}
    print(f"   ✅ Données sociales collectées")
    return state


def diff_node(state: VeilleState) -> VeilleState:
    print(f"\n🔄 [DIFF] Comparaison avec snapshots précédents...")
    t = datetime.now()
    web_data = [WebData(**w) for w in state["web_data"]]
    social_data = [SocialData(**s) for s in state["social_data"]]
    diffs = _get_diff_service().diff_all(web_data, social_data)
    state["diffs"] = [_diff_to_legacy_dict(d) for d in diffs]
    changed = sum(1 for d in diffs if d.has_changes)
    state["trace"]["diff"] = {"duration_s": round((datetime.now() - t).total_seconds(), 2), "changed": changed}
    print(f"   ✅ {changed}/{len(diffs)} concurrent(s) avec changements")
    return state


def analysis_node(state: VeilleState) -> VeilleState:
    print(f"\n🎯 [ANALYSIS] Analyse stratégique des signaux...")
    t = datetime.now()
    analysis = run_analysis(state["diffs"])
    state["analysis"] = analysis
    state["trace"]["analysis"] = {"duration_s": round((datetime.now() - t).total_seconds(), 2)}
    print(f"   ✅ Analyse terminée")
    return state


def report_node(state: VeilleState) -> VeilleState:
    print(f"\n📝 [REPORT] Génération du rapport...")
    t = datetime.now()
    report_path = run_report(state["sector"], state["analysis"], state["diffs"])
    state["report_path"] = report_path
    state["trace"]["report"] = {"duration_s": round((datetime.now() - t).total_seconds(), 2)}
    return state


# ─── Graph ───────────────────────────────────────────────────────────────────

def build_graph():
    graph = StateGraph(VeilleState)

    graph.add_node("discovery", discovery_node)
    graph.add_node("scraper",   scraper_node)
    graph.add_node("social",    social_node)
    graph.add_node("diff",      diff_node)
    graph.add_node("analysis",  analysis_node)
    graph.add_node("report",    report_node)

    # Séquentiel : discovery → scraper → social → diff → analysis → report
    graph.set_entry_point("discovery")
    graph.add_edge("discovery", "scraper")
    graph.add_edge("scraper",   "social")
    graph.add_edge("social",    "diff")
    graph.add_edge("diff",      "analysis")
    graph.add_edge("analysis",  "report")
    graph.add_edge("report",    END)

    return graph.compile()


# ─── Entry point ─────────────────────────────────────────────────────────────

def run(sector: str, max_competitors: int = 5):
    print(f"\n{'='*55}")
    print(f"  🕵️  Veille Concurrentielle — LangGraph")
    print(f"  Secteur : {sector}")
    print(f"  Concurrents max : {max_competitors}")
    print(f"{'='*55}")

    app = build_graph()

    initial_state: VeilleState = {
        "sector": sector,
        "max_competitors": max_competitors,
        "competitors": [],
        "web_data": [],
        "social_data": [],
        "diffs": [],
        "analysis": {},
        "report_path": "",
        "trace": {},
    }

    final_state = app.invoke(initial_state)

    total = sum(v.get("duration_s", 0) for v in final_state["trace"].values() if isinstance(v, dict))

    print(f"\n{'='*55}")
    print(f"  ✅ Rapport généré : {final_state['report_path']}")
    print(f"  ⏱️  Durée totale : {total:.1f}s")
    print(f"{'='*55}\n")

    return final_state


if __name__ == "__main__":
    import sys
    sector = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "paiement en ligne SaaS"
    run(sector)
