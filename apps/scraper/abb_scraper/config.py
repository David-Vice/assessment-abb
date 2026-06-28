from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_START_URL = "https://abb-bank.az/"
DEFAULT_USER_AGENT = "ABB-RAG-Assessment-Bot/0.1 (+https://abb-bank.az; assessment crawler)"


class ScraperSettings(BaseSettings):
    """Crawl configuration. Env-driven (prefix SCRAPE_), overridable via CLI flags."""

    model_config = SettingsConfigDict(env_prefix="SCRAPE_", env_file=".env", extra="ignore")

    start_url: str = DEFAULT_START_URL
    max_pages: int = 300
    max_depth: int = 5
    playwright_enabled: bool = False
    user_agent: str = DEFAULT_USER_AGENT
    download_delay: float = 0.5
    concurrent_requests_per_domain: int = 8
    target_concurrency: float = 1.0
