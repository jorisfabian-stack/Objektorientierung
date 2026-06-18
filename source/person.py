from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

DATA_ROOT = Path(__file__).resolve().parent.parent / "data"
PERSON_DB_FILE = DATA_ROOT / "person_db.json"


@dataclass
class Person:
    id: int
    firstname: str
    lastname: str
    date_of_birth: int
    picture_path: str
    gender: str
    ekg_tests: List[Dict[str, Any]]

    @property
    def full_name(self) -> str:
        return f"{self.lastname}, {self.firstname}"

    @property
    def display_name(self) -> str:
        return f"{self.firstname} {self.lastname}"

    @property
    def age(self) -> int:
        today = date.today()
        return today.year - self.date_of_birth

    @classmethod
    def from_dict(cls, source: Dict[str, Any]) -> "Person":
        return cls(
            id=int(source.get("id", 0)),
            firstname=source.get("firstname", ""),
            lastname=source.get("lastname", ""),
            date_of_birth=int(source.get("date_of_birth", 0)),
            picture_path=source.get("picture_path", ""),
            gender=source.get("gender", ""),
            ekg_tests=source.get("ekg_tests", []) or [],
        )

    @classmethod
    def load_all(cls, path: Optional[Path] = None) -> List["Person"]:
        if path is None:
            path = PERSON_DB_FILE
        path = Path(path)
        with path.open(encoding="utf-8") as file:
            raw_data = json.load(file)
        return [cls.from_dict(entry) for entry in raw_data]

    @classmethod
    def find_by_full_name(cls, persons: Iterable["Person"], full_name: str) -> Optional["Person"]:
        for person in persons:
            if person.full_name == full_name:
                return person
        return None

    def get_ekg_tests(self) -> List[Dict[str, Any]]:
        return list(self.ekg_tests)

    def get_test_by_id(self, test_id: int) -> Optional[Dict[str, Any]]:
        for test in self.ekg_tests:
            if test.get("id") == test_id:
                return test
        return None

    def get_picture_path(self) -> Path:
        return Path(self.picture_path)


def load_person_data() -> List[Person]:
    return Person.load_all()


def get_person_list(persons: Iterable[Person]) -> List[str]:
    return [person.full_name for person in persons]


def find_person_data_by_name(persons: Iterable[Person], suchstring: str) -> Optional[Person]:
    return Person.find_by_full_name(persons, suchstring)


if __name__ == "__main__":
    personen = Person.load_all()
    print("Geladene Personen:")
    for person in personen[:3]:
        print(person)
    print("-" * 20)
    print("Namen:")
    print(get_person_list(personen))
