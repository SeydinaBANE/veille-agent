"""
Web Scraper Agent — Extrait le contenu des sites concurrents
Scrape : page d'accueil, pricing, blog récent
"""

import requests
import re
from bs4 import BeautifulSoup
from dotenv import load_dotenv
load_dotenv()

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def fetch_page(url: str, timeout: int = 10) -> str | None:
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")

        # Supprime scripts, styles, nav, footer
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()

        # Texte propre
        text = soup.get_text(separator=" ", strip=True)
        text = re.sub(r'\s+', ' ', text)
        return text[:3000]
    except Exception as e:
        return None


def scrape_competitor(competitor: dict) -> dict:
    """Scrape homepage + pricing page d'un concurrent."""
    website = competitor.get("website", "")
    name = competitor.get("name", "inconnu")

    if not website:
        return {"name": name, "homepage": None, "pricing": None, "error": "pas d'URL"}

    print(f"   🌐 Scraping {name} ({website})...")

    result = {
        "name": name,
        "website": website,
        "homepage": None,
        "pricing": None,
        "blog_titles": [],
    }

    # Homepage
    result["homepage"] = fetch_page(website)

    # Pricing (essaie plusieurs URLs courantes)
    for path in ["/pricing", "/tarifs", "/plans", "/price"]:
        content = fetch_page(website.rstrip("/") + path)
        if content and len(content) > 200:
            result["pricing"] = content
            break

    # Blog (titres récents)
    for path in ["/blog", "/news", "/actualites", "/articles"]:
        blog = fetch_page(website.rstrip("/") + path)
        if blog:
            # Extrait les titres H1/H2 potentiels
            soup_text = blog[:2000]
            titles = re.findall(r'(?<!\w)([A-Z][^.!?\n]{20,80})(?=[.!?\n])', soup_text)
            result["blog_titles"] = titles[:5]
            break

    return result


def run_scraper(competitors: list[dict]) -> list[dict]:
    """Scrape tous les concurrents."""
    results = []
    for competitor in competitors:
        data = scrape_competitor(competitor)
        results.append(data)
    return results
