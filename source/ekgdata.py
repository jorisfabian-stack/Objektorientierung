from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

DATA_ROOT = Path(__file__).resolve().parent.parent / "data"


@dataclass
class Ekgdata:
    duration: List[float]
    heart_rate: List[float]
    power_original: List[float]
    raw_rows: List[Dict[str, Any]]

    @classmethod
    def from_file(cls, path: Path) -> "Ekgdata":
        rows: List[Dict[str, Any]] = []
        duration: List[float] = []
        heart_rate: List[float] = []
        power_original: List[float] = []

        with path.open("r", encoding="utf-8", errors="ignore") as file:
            reader = csv.reader(file, delimiter="\t")
            for raw_row in reader:
                if not raw_row or len(raw_row) < 2:
                    continue
                try:
                    hr = float(raw_row[0])
                    power = float(raw_row[1])
                except ValueError:
                    continue
                duration.append(len(duration) + 1)
                heart_rate.append(hr)
                power_original.append(power)
                rows.append({"heart_rate": hr, "power_original": power})

        return cls(
            duration=duration,
            heart_rate=heart_rate,
            power_original=power_original,
            raw_rows=rows,
        )

    @classmethod
    def from_ekg_test(cls, ekg_test: Dict[str, Any]) -> Optional["Ekgdata"]:
        link = ekg_test.get("result_link")
        if not link:
            return None
        path = Path(link)
        if not path.exists():
            return None
        return cls.from_file(path)

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

    def summary(self) -> Dict[str, Any]:
        return {
            "samples": self.sample_count(),
            "heart_rate_avg": self.average_heart_rate(),
            "heart_rate_max": self.max_heart_rate(),
            "power_avg": self.average_power(),
            "power_max": self.max_power(),
        }


if __name__ == "__main__":
    example_file = DATA_ROOT / "ekg_data" / "01_Ruhe.txt"
    data = Ekgdata.from_file(example_file)
    print(data.summary())
