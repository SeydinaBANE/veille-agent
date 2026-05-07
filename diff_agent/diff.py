"""
Diff Agent — Compare les nouvelles données avec les snapshots précédents
Détecte : changements de prix, nouveaux articles, nouveaux posts, changements homepage
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from storage.snapshot import load_snapshot, save_snapshot, slugify
from datetime import datetime


def text_changed(old: str | None, new: str | None, threshold: int = 100) -> bool:
    """Détecte si un texte a significativement changé."""
    if old is None and new is not None:
        return True
    if old is None or new is None:
        return False
    # Compare les 500 premiers caractères (zone la plus stable)
    old_sample = old[:500].lower().split()
    new_sample = new[:500].lower().split()
    common = set(old_sample) & set(new_sample)
    if not old_sample:
        return bool(new_sample)
    similarity = len(common) / max(len(set(old_sample)), 1)
    return similarity < 0.85  # Changement si moins de 85% de mots communs


def diff_competitor(web_data: dict, social_data: dict) -> dict:
    """Calcule le diff pour un concurrent."""
    name = web_data.get("name", "inconnu")
    slug = slugify(name)

    old = load_snapshot(slug)
    new_snapshot = {
        "name": name,
        "website": web_data.get("website"),
        "homepage": web_data.get("homepage"),
        "pricing": web_data.get("pricing"),
        "blog_titles": web_data.get("blog_titles", []),
        "linkedin_posts": social_data.get("linkedin_posts", []),
        "twitter_posts": social_data.get("twitter_posts", []),
    }

    changes = []

    if old is None:
        changes.append({
            "type": "nouveau_concurrent",
            "description": f"Premier scan de {name} — baseline créée"
        })
    else:
        # Changement homepage
        if text_changed(old.get("homepage"), new_snapshot["homepage"]):
            changes.append({
                "type": "site_modifie",
                "description": "Page d'accueil modifiée depuis le dernier scan"
            })

        # Changement pricing
        if text_changed(old.get("pricing"), new_snapshot["pricing"]):
            changes.append({
                "type": "prix_modifie",
                "description": "Page de tarification modifiée ⚠️"
            })

        # Nouveaux titres blog
        old_titles = set(old.get("blog_titles", []))
        new_titles = set(new_snapshot["blog_titles"])
        new_posts = new_titles - old_titles
        if new_posts:
            changes.append({
                "type": "nouveau_contenu",
                "description": f"Nouveaux articles détectés : {', '.join(list(new_posts)[:3])}"
            })

        # Nouveaux posts sociaux
        old_li = set(old.get("linkedin_posts", []))
        new_li = set(new_snapshot["linkedin_posts"])
        new_li_posts = new_li - old_li
        if new_li_posts:
            changes.append({
                "type": "nouveau_post_linkedin",
                "description": f"{len(new_li_posts)} nouveau(x) post(s) LinkedIn"
            })

        old_tw = set(old.get("twitter_posts", []))
        new_tw = set(new_snapshot["twitter_posts"])
        new_tw_posts = new_tw - old_tw
        if new_tw_posts:
            changes.append({
                "type": "nouveau_post_twitter",
                "description": f"{len(new_tw_posts)} nouveau(x) tweet(s)"
            })

    # Sauvegarde le nouveau snapshot
    save_snapshot(slug, new_snapshot)

    return {
        "name": name,
        "changes": changes,
        "has_changes": len(changes) > 0,
        "data": new_snapshot,
        "scanned_at": datetime.now().isoformat(),
    }


def run_diff(web_results: list[dict], social_results: list[dict]) -> list[dict]:
    """Calcule les diffs pour tous les concurrents."""
    # Index social par nom
    social_index = {r["name"]: r for r in social_results}

    diffs = []
    for web in web_results:
        name = web.get("name", "")
        social = social_index.get(name, {"linkedin_posts": [], "twitter_posts": []})
        diff = diff_competitor(web, social)
        diffs.append(diff)
        status = f"{len(diff['changes'])} changement(s)" if diff["has_changes"] else "aucun changement"
        print(f"   🔄 Diff {name} : {status}")

    return diffs
