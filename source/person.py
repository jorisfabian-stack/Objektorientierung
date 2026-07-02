from __future__ import annotations

import hashlib
import json
import secrets
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence
from source.logging_config import get_logger

logger = get_logger(__name__)

DATA_ROOT = Path(__file__).resolve().parent.parent / "data"
PERSON_DB_FILE = DATA_ROOT / "person_db.json"


@dataclass
class Person:
    """Domain object representing a single test person with multiple EKG tests."""

    id: int
    firstname: str
    lastname: str
    date_of_birth: int
    picture_path: str
    gender: str
    ekg_tests: List[Dict[str, Any]]
    username: str = ""
    email: str = ""
    password_hash: str = ""
    password_salt: str = ""

    @property
    def full_name(self) -> str:
        """Return the person's full name in format 'lastname, firstname'."""
        return f"{self.lastname}, {self.firstname}"

    @property
    def display_name(self) -> str:
        """Return the person's display name in format 'firstname lastname'."""
        return f"{self.firstname} {self.lastname}"

    @property
    def age(self) -> int:
        """Calculate and return the person's current age in years."""
        today = date.today()
        return today.year - self.date_of_birth

    @property
    def birth_year(self) -> int:
        """Return the person's birth year."""
        return self.date_of_birth

    @classmethod
    def from_dict(cls, source: Dict[str, Any]) -> "Person":
        """Create a Person instance from a dictionary, typically loaded from JSON."""
        return cls(
            id=int(source.get("id", 0)),
            firstname=source.get("firstname", ""),
            lastname=source.get("lastname", ""),
            date_of_birth=int(source.get("date_of_birth", 0)),
            picture_path=source.get("picture_path", ""),
            gender=source.get("gender", ""),
            ekg_tests=source.get("ekg_tests", []) or [],
            username=source.get("username", ""),
            email=source.get("email", ""),
            password_hash=source.get("password_hash", ""),
            password_salt=source.get("password_salt", ""),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert the Person instance to a dictionary suitable for JSON serialization."""
        return {
            "id": self.id,
            "firstname": self.firstname,
            "lastname": self.lastname,
            "date_of_birth": self.date_of_birth,
            "picture_path": self.picture_path,
            "gender": self.gender,
            "ekg_tests": [test.copy() for test in self.ekg_tests],
            "username": self.username,
            "email": self.email,
            "password_hash": self.password_hash,
            "password_salt": self.password_salt,
        }

    @classmethod
    def load_all(cls, path: Optional[Path] = None) -> List["Person"]:
        """Load all persons from a JSON file."""
        if path is None:
            path = PERSON_DB_FILE
        path = Path(path)
        logger.debug("Loading persons from %s", path)
        with path.open(encoding="utf-8") as file:
            raw_data = json.load(file)
        persons = [cls.from_dict(entry) for entry in raw_data]
        logger.info("Loaded %d persons", len(persons))
        return persons

    @classmethod
    def save_all(cls, persons: Sequence["Person"], path: Optional[Path] = None) -> None:
        """Save a list of persons to a JSON file."""
        if path is None:
            path = PERSON_DB_FILE
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        logger.debug("Saving %d persons to %s", len(persons), path)
        with path.open("w", encoding="utf-8") as file:
            json.dump([person.to_dict() for person in persons], file, ensure_ascii=False, indent=4)
        logger.info("Saved persons to %s", path)

    @classmethod
    def find_by_full_name(cls, persons: Iterable["Person"], full_name: str) -> Optional["Person"]:
        """Search for a person by their full name."""
        for person in persons:
            if person.full_name == full_name:
                return person
        return None

    @classmethod
    def find_by_identifier(cls, persons: Iterable["Person"], identifier: str) -> Optional["Person"]:
        """Search for a person by username, email, or full name."""
        normalized = identifier.strip().lower()
        for person in persons:
            if person.username.strip().lower() == normalized:
                return person
            if person.email.strip().lower() == normalized:
                return person
            if person.full_name.strip().lower() == normalized:
                return person
        return None

    def get_ekg_tests(self) -> List[Dict[str, Any]]:
        """Return a copy of the person's EKG test list."""
        return list(self.ekg_tests)

    def get_test_by_id(self, test_id: int) -> Optional[Dict[str, Any]]:
        """Find an EKG test by its ID."""
        for test in self.ekg_tests:
            if test.get("id") == test_id:
                return test
        return None

    def add_ekg_test(self, new_test: Dict[str, Any]) -> None:
        """Add a new EKG test to the person's test list."""
        self.ekg_tests.append(new_test)

    def get_picture_path(self) -> Path:
        """Get the full path to the person's picture file."""
        return Path(self.picture_path)

    @staticmethod
    def next_person_id(persons: Iterable["Person"]) -> int:
        """Generate the next available person ID."""
        current_ids = [person.id for person in persons if isinstance(person.id, int)]
        return max(current_ids, default=0) + 1

    @staticmethod
    def next_test_id(persons: Iterable["Person"]) -> int:
        """Generate the next available EKG test ID across all persons."""
        test_ids: List[int] = []
        for person in persons:
            for test in person.ekg_tests:
                try:
                    test_ids.append(int(test.get("id", 0)))
                except (TypeError, ValueError):
                    continue
        return max(test_ids, default=0) + 1

    def set_password(self, password: str) -> None:
        """Set a user password using a salted hash."""
        self.password_salt = secrets.token_hex(16)
        self.password_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            self.password_salt.encode("utf-8"),
            100_000,
        ).hex()

    def verify_password(self, password: str) -> bool:
        """Verify a plaintext password against the stored hash."""
        if not self.password_hash or not self.password_salt:
            return False
        hashed = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            self.password_salt.encode("utf-8"),
            100_000,
        ).hex()
        return secrets.compare_digest(hashed, self.password_hash)


def load_person_data() -> List[Person]:
    """Load all persons from the database, sorted by last name.
    
    Returns:
        List of Person instances sorted alphabetically by last name.
    """
    persons = Person.load_all()
    return sorted(persons, key=lambda person: person.lastname.lower())


def get_person_list(persons: Iterable[Person]) -> List[str]:
    """Extract a list of full names from a collection of persons.
    
    Args:
        persons: Iterable of Person instances.
        
    Returns:
        List of full names in format 'lastname, firstname'.
    """
    return [person.full_name for person in persons]


def find_person_data_by_name(persons: Iterable[Person], suchstring: str) -> Optional[Person]:
    """Find a person by their full name in a collection.
    
    Args:
        persons: Iterable of Person instances to search.
        suchstring: Full name to search for (format: 'lastname, firstname').
        
    Returns:
        Person instance if found, None otherwise.
    """
    return Person.find_by_full_name(persons, suchstring)
