"""Insert and verify a clearly marked MongoDB connection-test record.

This script uses MONGODB_URI from the private .env file and never prints it.
The inserted document has no learner metrics and is not a practice result.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from pymongo.errors import PyMongoError

from backend.app import COLLECTION_NAME, _database


def main() -> None:
    database = _database()
    collection = database[COLLECTION_NAME]
    collection.create_index([("user_id", 1), ("timestamp", -1)])

    run_id = str(uuid4())
    record = {
        "record_type": "CONNECTION_TEST",
        "test_run_id": run_id,
        "user_id": "__connection_test__",
        "sign_id": "connection_test",
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
        "hands_detected": 0,
        "expected_hands": None,
        "status": "CONNECTION_TEST",
        "metrics": {
            "dtw_distance": None,
            "similarity_score": None,
            "analysis_latency_ms": 0.0,
        },
        "finger_angles": {},
        "detected_error_codes": [],
        "remediation_recommended": None,
    }

    try:
        inserted = collection.insert_one(record)
        fetched = collection.find_one({"_id": inserted.inserted_id})
    except PyMongoError as error:
        raise SystemExit(f"MongoDB insert/query failed ({type(error).__name__}).") from None

    if fetched is None:
        raise SystemExit("Insert returned an id, but the verification query found no document.")
    print(f"MongoDB connection verified. Database: {database.name}")
    print(f"Collection: {COLLECTION_NAME}")
    print(f"Inserted and queried connection-test record: {inserted.inserted_id}")
    print("This marked record has no learner score and is not a real practice attempt.")


if __name__ == "__main__":
    main()
