"""Centralized Configuration and Dataset Profiles."""

from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import NamedTuple

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ProfileType(str, Enum):
    """Supported dataset scale profiles."""
    STARTER = "STARTER"
    FULL = "FULL"


class ProfileConfig(NamedTuple):
    """Specific parameters for a dataset profile."""
    facilities_count: int
    docks_per_facility: int
    yard_slots_per_facility: int
    carriers_count: int
    vehicles_count: int
    appointments_count: int
    simulation_days: int
    operating_start_hour: int
    operating_end_hour: int


PROFILES: dict[ProfileType, ProfileConfig] = {
    ProfileType.STARTER: ProfileConfig(
        facilities_count=2,
        docks_per_facility=10,  # 20 total docks
        yard_slots_per_facility=15,  # 30 total yard slots
        carriers_count=10,
        vehicles_count=40,
        appointments_count=1000,
        simulation_days=7,
        operating_start_hour=6,
        operating_end_hour=22,
    ),
    ProfileType.FULL: ProfileConfig(
        facilities_count=10,
        docks_per_facility=10,  # 100 total docks
        yard_slots_per_facility=20,  # 200 total yard slots
        carriers_count=50,
        vehicles_count=300,
        appointments_count=20000,
        simulation_days=60,
        operating_start_hour=6,
        operating_end_hour=22,
    ),
}


class Settings(BaseSettings):
    """Global application settings and environmental overrides."""
    model_config = SettingsConfigDict(
        env_prefix="LOGISTICS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    seed: int = Field(default=20261022, description="Deterministic PRNG seed")
    profile: ProfileType = Field(default=ProfileType.STARTER, description="Active dataset profile")
    database_url: str = Field(default="sqlite:///data/logistics.db", description="SQLAlchemy DB connection URL")
    simulation_start: datetime = Field(
        default=datetime(2026, 10, 22, 0, 0, 0, tzinfo=timezone.utc),
        description="Deterministic simulation anchor timestamp in UTC",
    )
    data_dir: Path = Field(default=Path("data"), description="Base data directory")
    exports_dir: Path = Field(default=Path("exports"), description="Base exports directory")
    api_host: str = Field(default="127.0.0.1", description="FastAPI host")
    api_port: int = Field(default=8000, description="FastAPI port")

    @property
    def sim_year(self) -> int:
        """Return the simulation reference year."""
        return self.simulation_start.year

    @property
    def active_profile_config(self) -> ProfileConfig:
        """Return the configuration tuple for the currently selected profile."""
        return PROFILES[self.profile]

    def ensure_directories(self) -> None:
        """Create necessary subdirectories for database, exports, and reports."""
        subdirs = [
            self.data_dir / "ground_truth",
            self.exports_dir / "csv",
            self.exports_dir / "json",
            self.exports_dir / "sql",
            self.exports_dir / "reports",
        ]
        for path in subdirs:
            path.mkdir(parents=True, exist_ok=True)


# Default global settings singleton instance
settings = Settings()
