from __future__ import annotations

import csv
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

DATA_ROOT = Path(__file__).resolve().parent.parent / "data"


@dataclass
class Ekgdata:
    """Data wrapper for parsed EKG sample data and summary statistics."""

    duration: List[float]
    heart_rate: List[float]
    power_original: List[float]
    raw_rows: List[Dict[str, Any]]

    @classmethod
    def from_file(cls, path: Path, downsample_factor: int = 1) -> "Ekgdata":
        """Parse an EKG text file with optional downsampling for performance."""
        duration: List[float] = []
        heart_rate: List[float] = []
        power_original: List[float] = []
        raw_rows: List[Dict[str, Any]] = []

        with path.open("r", encoding="utf-8", errors="ignore") as file:
            reader = csv.reader(file, delimiter="\t")
            for index, raw_row in enumerate(reader):
                if not raw_row or len(raw_row) < 2:
                    continue
                if downsample_factor > 1 and (index % downsample_factor) != 0:
                    continue
                try:
                    hr = float(raw_row[0])
                    power = float(raw_row[1])
                except ValueError:
                    continue
                duration.append(index + 1)
                heart_rate.append(hr)
                power_original.append(power)
                raw_rows.append({"heart_rate": hr, "power_original": power})

        return cls(
            duration=duration,
            heart_rate=heart_rate,
            power_original=power_original,
            raw_rows=raw_rows,
        )

    @classmethod
    def from_ekg_test(cls, ekg_test: Dict[str, Any], downsample_factor: int = 1) -> Optional["Ekgdata"]:
        link = ekg_test.get("result_link")
        if not link:
            return None
        path = Path(link)
        if not path.exists():
            return None
        return cls.from_file(path, downsample_factor=downsample_factor)

    @classmethod
    @lru_cache(maxsize=32)
    def cached_from_file(cls, path: str, downsample_factor: int = 1) -> "Ekgdata":
        return cls.from_file(Path(path), downsample_factor=downsample_factor)

    def average_heart_rate(self) -> float:
        return sum(self.heart_rate) / len(self.heart_rate) if self.heart_rate else 0.0

    def max_heart_rate(self) -> float:
        return max(self.heart_rate) if self.heart_rate else 0.0

    def average_power(self) -> float:
        return sum(self.power_original) / len(self.power_original) if self.power_original else 0.0

    def max_power(self) -> float:
        return max(self.power_original) if self.power_original else 0.0

    def sample_count(self) -> int:
        return len(self.duration)

    def total_duration_minutes(self, sample_rate_hz: float = 1.0) -> float:
        if not self.duration:
            return 0.0
        return round(self.sample_count() / sample_rate_hz / 60.0, 2)

    def summary(self) -> Dict[str, Any]:
        return {
            "samples": self.sample_count(),
            "duration_minutes": self.total_duration_minutes(),
            "heart_rate_avg": self.average_heart_rate(),
            "heart_rate_max": self.max_heart_rate(),
            "power_avg": self.average_power(),
            "power_max": self.max_power(),
        }
