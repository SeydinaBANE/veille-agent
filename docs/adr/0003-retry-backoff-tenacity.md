# ADR 0003: Retry/backoff via tenacity sur les appels réseau et LLM transitoires

## Statut

Acceptée

## Contexte

Aucun mécanisme de nouvelle tentative n'existait avant le durcissement production : une erreur transitoire (timeout réseau, rate limit OpenRouter, erreur 5xx côté serveur) faisait échouer tout le scan en cours, sans distinction avec une erreur définitive.

## Décision

Ajouter `tenacity` comme dépendance et appliquer un retry (3 tentatives, backoff exponentiel de 1 à 8 secondes) sur les appels identifiés comme transitoires :

- `adapters/llm/openrouter.py` (`OpenRouterLLMClient.complete`) — erreurs `APIConnectionError`, `APITimeoutError`, `RateLimitError`, `InternalServerError` du SDK Anthropic.
- `adapters/search/duckduckgo.py` (`DuckDuckGoSearchEngine._fetch`) — `requests.RequestException`.
- `adapters/social/scraper.py` (`PublicSocialScraper._search_linkedin_duckduckgo`) — même traitement pour la recherche LinkedIn via DuckDuckGo.

Pas de retry ajouté sur les autres échecs réseau (site concurrent indisponible dans `adapters/web/scraper.py`, instance Nitter en panne dans `adapters/social/scraper.py`) : ces cas ont déjà une stratégie de repli dédiée (chemins alternatifs pour le pricing/blog, liste d'instances Nitter de secours), un retry supplémentaire n'apporterait rien.

## Conséquences

- Le pipeline survit à des erreurs transitoires ponctuelles (un rate limit OpenRouter, un timeout DNS) sans intervention manuelle ni relance complète du scan.
- Nouvelle dépendance (`tenacity`) — légère, sans transitive lourde.
- Un service réellement en panne prolongée fait toujours échouer le scan après les 3 tentatives (pas de circuit breaker ni de file d'attente de retry différé) — jugé suffisant pour un scan hebdomadaire ponctuel, à reconsidérer si la fréquence des scans augmente significativement.
- Les tests des adapters concernés désactivent le vrai `sleep` de tenacity (`<methode>.retry.sleep = lambda _: None`) pour rester rapides — voir `tests/test_openrouter_llm.py`, `tests/test_duckduckgo_search.py`, `tests/test_social_scraper.py`.
