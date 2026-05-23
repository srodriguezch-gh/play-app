import pytest
from services.platform_scraper import PlatformScraper

@pytest.mark.anyio
async def test_scraper_fetches_achievements():
    scraper = PlatformScraper()
    # This should fail if the method isn't implemented
    achievements = await scraper.fetch_achievements("steam", "game_123")
    assert isinstance(achievements, list)
    assert len(achievements) > 0
