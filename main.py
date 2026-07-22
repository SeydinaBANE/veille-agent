"""
Veille Concurrentielle Agent — LangGraph Pipeline
Orchestration : Discovery → Scraper + Social (parallèle) → Diff → Analysis → Report

Architecture hexagonale :
- domain/       entités métier + ports (interfaces attendues des adapters)
- application/  use cases, orchestrent les ports (aucune dépendance à une infra concrète)
- adapters/     implémentations concrètes des ports (LLM, scraping, stockage, notifications)

Ce module est le composition root : il instancie les adapters, les injecte
dans les use cases, et orchestre le tout via un StateGraph LangGraph.
"""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from typing import Callable, TypedDict
from dataclasses import dataclass
from datetime import datetime
from langgraph.graph import StateGraph, END
from dotenv import load_dotenv
load_dotenv()

from adapters.llm.openrouter import OpenRouterLLMClient
from adapters.search.duckduckgo import DuckDuckGoSearchEngine
from adapters.social.scraper import PublicSocialScraper
from adapters.storage.report_repository import MarkdownReportRepository
from adapters.storage.snapshot_repository import JsonSnapshotRepository
from adapters.web.scraper import HttpWebScraper
from application.analysis import AnalysisService
from application.discovery import DiscoveryService
from application.diff import DiffService
from application.report import ReportService
from application.scraper import ScraperService
from application.social import SocialService
from domain.models import Competitor, CompetitorDiff, SocialData, StepTrace, StrategicAnalysis, WebData

OnStep = Callable[[str], None]


# ─── Composition root ────────────────────────────────────────────────────────

@dataclass
class Services:
    discovery: DiscoveryService
    scraper: ScraperService
    social: SocialService
    diff: DiffService
    analysis: AnalysisService
    report: ReportService


_services: Services | None = None


def _get_services() -> Services:
    global _services
    if _services is None:
        api_key = os.environ["OPENROUTER_API_KEY"]
        _services = Services(
            discovery=DiscoveryService(
                llm=OpenRouterLLMClient(api_key=api_key, model="anthropic/claude-haiku-4-5"),
                search=DuckDuckGoSearchEngine(),
            ),
            scraper=ScraperService(scraper=HttpWebScraper()),
            social=SocialService(scraper=PublicSocialScraper()),
            diff=DiffService(repository=JsonSnapshotRepository()),
            analysis=AnalysisService(
                llm=OpenRouterLLMClient(api_key=api_key, model="anthropic/claude-opus-4-5"),
            ),
            report=ReportService(
                llm=OpenRouterLLMClient(api_key=api_key, model="anthropic/claude-sonnet-4-6"),
                repository=MarkdownReportRepository(),
            ),
        )
    return _services


# ─── State ───────────────────────────────────────────────────────────────────

class VeilleState(TypedDict):
    sector: str                        # Secteur / mot-clé en entrée
    max_competitors: int                # Nombre de concurrents à surveiller
    competitors: list[Competitor]        # Liste découverte par discovery
    web_data: list[WebData]              # Données scrapées des sites
    social_data: list[SocialData]        # Données sociales (LinkedIn, Twitter)
    diffs: list[CompetitorDiff]          # Changements vs snapshots précédents
    analysis: StrategicAnalysis          # Analyse et scores LLM
    report_path: str                    # Chemin du rapport généré
    trace: dict[str, StepTrace]          # Métriques d'exécution
    on_step: OnStep | None               # Callback de progression (UI)


def _emit(state: VeilleState, message: str) -> None:
    print(f"\n{message}")
    on_step = state.get("on_step")
    if on_step is not None:
        on_step(message)


# ─── Nodes ───────────────────────────────────────────────────────────────────

def discovery_node(state: VeilleState) -> VeilleState:
    _emit(state, "🔍 [DISCOVERY] Identification des concurrents...")
    t = datetime.now()
    competitors = _get_services().discovery.discover(state["sector"], state["max_competitors"])
    state["competitors"] = competitors
    state["trace"]["discovery"] = StepTrace(
        duration_s=round((datetime.now() - t).total_seconds(), 2),
        detail=f"{len(competitors)} concurrents",
    )
    print(f"   ✅ {len(competitors)} concurrents trouvés")
    return state


def scraper_node(state: VeilleState) -> VeilleState:
    _emit(state, "🌐 [SCRAPER] Scraping des sites web...")
    t = datetime.now()
    web_data = _get_services().scraper.scrape_all(state["competitors"])
    state["web_data"] = web_data
    state["trace"]["scraper"] = StepTrace(duration_s=round((datetime.now() - t).total_seconds(), 2))
    print(f"   ✅ {len(web_data)} sites scrapés")
    return state


def social_node(state: VeilleState) -> VeilleState:
    _emit(state, "📱 [SOCIAL] Collecte des posts sociaux...")
    t = datetime.now()
    social_data = _get_services().social.collect_all(state["competitors"])
    state["social_data"] = social_data
    state["trace"]["social"] = StepTrace(duration_s=round((datetime.now() - t).total_seconds(), 2))
    print(f"   ✅ Données sociales collectées")
    return state


def diff_node(state: VeilleState) -> VeilleState:
    _emit(state, "🔄 [DIFF] Comparaison avec snapshots précédents...")
    t = datetime.now()
    diffs = _get_services().diff.diff_all(state["web_data"], state["social_data"])
    state["diffs"] = diffs
    changed = sum(1 for d in diffs if d.has_changes)
    state["trace"]["diff"] = StepTrace(
        duration_s=round((datetime.now() - t).total_seconds(), 2),
        detail=f"{changed}/{len(diffs)} changé(s)",
    )
    print(f"   ✅ {changed}/{len(diffs)} concurrent(s) avec changements")
    return state


def analysis_node(state: VeilleState) -> VeilleState:
    _emit(state, "🎯 [ANALYSIS] Analyse stratégique des signaux...")
    t = datetime.now()
    analysis = _get_services().analysis.analyze(state["diffs"])
    state["analysis"] = analysis
    state["trace"]["analysis"] = StepTrace(duration_s=round((datetime.now() - t).total_seconds(), 2))
    print(f"   ✅ Analyse terminée")
    return state


def report_node(state: VeilleState) -> VeilleState:
    _emit(state, "📝 [REPORT] Génération du rapport...")
    t = datetime.now()
    report_path = _get_services().report.generate(state["sector"], state["analysis"])
    state["report_path"] = report_path
    state["trace"]["report"] = StepTrace(duration_s=round((datetime.now() - t).total_seconds(), 2))
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

def run(sector: str, max_competitors: int = 5, on_step: OnStep | None = None) -> VeilleState:
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
        "analysis": StrategicAnalysis(competitors=[], summary=""),
        "report_path": "",
        "trace": {},
        "on_step": on_step,
    }

    final_state = app.invoke(initial_state)

    total = sum(t.duration_s for t in final_state["trace"].values())

    print(f"\n{'='*55}")
    print(f"  ✅ Rapport généré : {final_state['report_path']}")
    print(f"  ⏱️  Durée totale : {total:.1f}s")
    print(f"{'='*55}\n")

    return final_state


if __name__ == "__main__":
    import sys
    sector = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "paiement en ligne SaaS"
    run(sector)
