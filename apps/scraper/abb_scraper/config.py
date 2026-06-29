from pydantic_settings import BaseSettings, SettingsConfigDict

from abb_scraper.metadata import site_domain

DEFAULT_START_URL = "https://abb-bank.az/"
DEFAULT_USER_AGENT = "ABB-RAG-Assessment-Bot/0.1 (+https://abb-bank.az; assessment crawler)"


class ScraperSettings(BaseSettings):
    """Crawl configuration. Env-driven (prefix SCRAPE_), overridable via CLI flags."""

    model_config = SettingsConfigDict(env_prefix="SCRAPE_", env_file=".env", extra="ignore")

    start_url: str = DEFAULT_START_URL
    user_agent: str = DEFAULT_USER_AGENT

    @property
    def domain(self) -> str:
        """Canonical apex host — the crawl scope and the corpus `source`."""

        return site_domain(self.start_url)
