"""Abstract connector interface for mapping, geocoding, and routing services."""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any


class MappingConnector(ABC):
    """Provider-independent interface for road network routing and geocoding."""

    @abstractmethod
    async def geocode(self, address: str) -> dict[str, Any]:
        """
        Geocode a property address into geographic coordinates.
        Returns: {
            "latitude": float,
            "longitude": float,
            "formatted_address": str,
            "provider": str,
            "status": "OK" | "ZERO_RESULTS" | "ERROR"
        }
        """
        pass

    @abstractmethod
    async def calculate_route(
        self,
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float,
    ) -> dict[str, Any]:
        """
        Calculate driving distance, duration, and road route between two points.
        Returns: {
            "distance_meters": int,
            "duration_seconds": int,
            "duration_text": str,
            "distance_text": str,
            "provider": str,
            "status": "OK" | "ESTIMATED_OFFLINE" | "ERROR"
        }
        """
        pass

    @abstractmethod
    async def calculate_matrix(
        self,
        origins: list[tuple[float, float]],
        destinations: list[tuple[float, float]],
    ) -> dict[str, Any]:
        """
        Calculate NxM travel-time and distance matrix between multiple points.
        Returns: {
            "duration_matrix": list[list[int]],  # duration in seconds
            "distance_matrix": list[list[int]],  # distance in meters
            "provider": str,
            "status": "OK" | "ESTIMATED_OFFLINE" | "ERROR"
        }
        """
        pass
