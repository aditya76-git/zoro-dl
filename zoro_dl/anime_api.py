import requests


class AnimeAPI:
    """
    A class to interact with the Consumet Anime API (https://consumet.org) for ZORO (Currently AniWatch) and retrieve information about episodes and streams.

    Attributes:
        base_url (str): The base Endpoint for Consumet API for ZORO
    """

    def __init__(self):
        self.base_url = "https://api.consumet.org/anime/zoro"

    def get_episodes(self, id):
        response = requests.get(f"{self.base_url}/info?id={id}").json()
        return response.get("episodes", [])

    def get_info(self, id, key):
        response = requests.get(f"{self.base_url}/info?id={id}").json()
        return response.get(key, "")

    def get_watch_info(self, episode_id):
        response = requests.get(f"{self.base_url}/watch?episodeId={episode_id}").json()
        return response
