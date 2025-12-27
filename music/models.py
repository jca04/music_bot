from dataclasses import dataclass

@dataclass
class Song:
    title: str
    url: str
    webpage_url: str
    duration: int