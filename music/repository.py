import sqlite3
import json

class MusicRepository:
    def __init__(self, path="db/music.db"):
        self.conn = sqlite3.connect(path)
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS music_state (
                guild_id INTEGER PRIMARY KEY,
                state_json TEXT NOT NULL
            )
            """
        )
        self.conn.commit()

    def save(self, guild_id: int, state: dict):
        self.conn.execute(
            """
            INSERT INTO music_state (guild_id, state_json)
            VALUES (?, ?)
            ON CONFLICT(guild_id)
            DO UPDATE SET state_json = excluded.state_json
            """,
            (guild_id, json.dumps(state))
        )
        self.conn.commit()

    def load(self, guild_id: int) -> dict | None:
        cur = self.conn.execute(
            "SELECT state_json FROM music_state WHERE guild_id = ?",
            (guild_id,)
        )

        row = cur.fetchone()
        return json.loads(row[0]) if row else None