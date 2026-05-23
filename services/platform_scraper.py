
class PlatformScraper:
    def __init__(self):
        pass

    async def fetch_achievements(self, platform: str, game_id: str):
        return [
            {
                "platform": platform,
                "game_id": game_id,
                "achievement_id": "ach_1",
                "title": "First Achievement",
                "achieved": True,
                "timestamp": "2026-05-23T12:00:00"
            }
        ]
