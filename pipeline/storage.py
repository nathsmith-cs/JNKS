import json
import os
from datetime import datetime


class SessionStorage:
    def __init__(self):
        self._records = []

    def append(self, frame_number, timestamp_ms, landmarks, ball_info):
        """Append a single frame record. landmarks may be None (no pose detected)."""
        self._records.append({
            "frame": frame_number,
            "timestamp_ms": timestamp_ms,
            "landmarks": landmarks,
            "ball": ball_info,
        })

    @property
    def count(self):
        return len(self._records)

    def save(self, directory="output"):
        """Dump all records to a timestamped JSON file. Returns the file path."""
        if not self._records:
            return None

        os.makedirs(directory, exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
        filename = f"session_{ts}.json"
        path = os.path.join(directory, filename)

        with open(path, "w") as f:
            json.dump(self._records, f)

        return path
