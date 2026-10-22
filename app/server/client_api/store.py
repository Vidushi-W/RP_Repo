"""One repository contract: MongoDB server storage, SQLite for local development."""

import json
import sqlite3
import threading
from datetime import datetime, timezone
from . import config


class Store:
    def __init__(self, path=None, mongo_uri=None):
        self.lock = threading.RLock()
        uri = config.MONGO_URI if mongo_uri is None else mongo_uri
        self.mongo = None
        if uri:
            from pymongo import MongoClient, ASCENDING

            self.client = MongoClient(uri, serverSelectionTimeoutMS=5000)
            self.client.admin.command(
                "ping"
            )  # Never fall back if configured Mongo fails.
            self.mongo = self.client[config.MONGO_DATABASE]
            for name in ("users", "sessions", "jobs"):
                self.mongo[name].create_index([("id", ASCENDING)], unique=True)
            self.mongo.users.create_index("email", unique=True)
            self.mongo.sessions.create_index("expires_at", expireAfterSeconds=0)
            self.mode = "mongodb"
        else:
            target = path or config.DATA / "client-development.sqlite3"
            target.parent.mkdir(parents=True, exist_ok=True)
            self.db = sqlite3.connect(target, check_same_thread=False)
            self.db.execute(
                "CREATE TABLE IF NOT EXISTS records (kind TEXT,id TEXT,data TEXT,email TEXT,PRIMARY KEY(kind,id))"
            )
            self.db.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS unique_user_email ON records(email) WHERE kind='users'"
            )
            self.db.commit()
            self.mode = "sqlite-development"

    def save(self, kind, item, insert=False):
        with self.lock:
            if self.mongo is not None:
                item = dict(item)
                if kind == "sessions":
                    item["expires_at"] = datetime.fromtimestamp(
                        item["expires"], timezone.utc
                    )
                if insert:
                    self.mongo[kind].insert_one(dict(item))
                else:
                    self.mongo[kind].replace_one(
                        {"id": item["id"]}, dict(item), upsert=True
                    )
            else:
                sql = "INSERT" if insert else "INSERT OR REPLACE"
                self.db.execute(
                    f"{sql} INTO records VALUES (?,?,?,?)",
                    (
                        kind,
                        item["id"],
                        json.dumps(item),
                        item.get("email") if kind == "users" else None,
                    ),
                )
                self.db.commit()

    def get(self, kind, id):
        with self.lock:
            if self.mongo is not None:
                return self.mongo[kind].find_one({"id": id}, {"_id": 0})
            row = self.db.execute(
                "SELECT data FROM records WHERE kind=? AND id=?", (kind, id)
            ).fetchone()
            return json.loads(row[0]) if row else None

    def find(self, kind, **query):
        with self.lock:
            if self.mongo is not None:
                return list(self.mongo[kind].find(query, {"_id": 0}))
            rows = self.db.execute(
                "SELECT data FROM records WHERE kind=?", (kind,)
            ).fetchall()
            records = [json.loads(raw) for (raw,) in rows]
            return [
                record
                for record in records
                if all(record.get(key) == value for key, value in query.items())
            ]

    def delete(self, kind, id):
        with self.lock:
            if self.mongo is not None:
                self.mongo[kind].delete_one({"id": id})
            else:
                self.db.execute("DELETE FROM records WHERE kind=? AND id=?", (kind, id))
                self.db.commit()
