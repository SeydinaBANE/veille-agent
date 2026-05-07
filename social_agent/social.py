"""
Social Agent — Récupère les posts publics LinkedIn & Twitter/X
Méthode : scraping public (pas d'API payante requise)
"""

import requests
import re
from bs4 import BeautifulSoup
from dotenv import load_dotenv
load_dotenv()

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
}


def fetch_linkedin_posts(linkedin_url: str, company_name: str) -> list[str]:
    """Récupère les posts récents LinkedIn via scraping public."""
    posts = []
    try:
        # Utilise DuckDuckGo pour chercher les posts récents
        query = f'site:linkedin.com "{company_name}" post annonce 2025'
        r = requests.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json", "no_html": "1"},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10
        )
        data = r.json()
        for topic in data.get("RelatedTopics", [])[:5]:
            if isinstance(topic, dict) and topic.get("Text"):
                posts.append(topic["Text"])

        # Fallback : scraping direct de la page LinkedIn publique
        if not posts and linkedin_url:
            resp = requests.get(linkedin_url, headers=HEADERS, timeout=10)
            soup = BeautifulSoup(resp.text, "lxml")
            for el in soup.find_all(["p", "span"], limit=20):
                text = el.get_text(strip=True)
                if len(text) > 50:
                    posts.append(text[:300])

    except Exception as e:
        posts.append(f"LinkedIn non accessible : {e}")

    return posts[:5]


def fetch_twitter_posts(twitter_handle: str) -> list[str]:
    """Récupère les tweets récents via Nitter (miroir public Twitter)."""
    posts = []
    if not twitter_handle:
        return posts

    nitter_instances = [
        "https://nitter.poast.org",
        "https://nitter.privacydev.net",
        "https://nitter.net",
    ]

    for instance in nitter_instances:
        try:
            url = f"{instance}/{twitter_handle.lstrip('@')}"
            r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=8)
            if r.status_code != 200:
                continue
            soup = BeautifulSoup(r.text, "lxml")
            tweets = soup.find_all("div", class_="tweet-content")
            for tweet in tweets[:5]:
                text = tweet.get_text(strip=True)
                if text:
                    posts.append(text[:280])
            if posts:
                break
        except Exception:
            continue

    if not posts:
        posts.append(f"Twitter/@{twitter_handle} non accessible via Nitter")

    return posts


def run_social(competitors: list[dict]) -> list[dict]:
    """Collecte les données sociales de tous les concurrents."""
    results = []
    for c in competitors:
        name = c.get("name", "inconnu")
        print(f"   📱 Social scraping : {name}...")

        data = {
            "name": name,
            "linkedin_posts": fetch_linkedin_posts(
                c.get("linkedin", ""), name
            ),
            "twitter_posts": fetch_twitter_posts(
                c.get("twitter", "")
            ),
        }
        results.append(data)

    return results
