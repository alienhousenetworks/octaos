"""
High-fidelity local fallback routing and geocoding connector.
Uses Haversine distance adjusted by empirical road curvature factor (1.35x)
and urban traffic speed profiles to produce realistic road travel estimates
without incurring third-party API costs or requiring internet connectivity.
"""
from __future__ import annotations
import math
from datetime import datetime
from typing import Any
from app.services.sales_os.field_sales.connectors.base import MappingConnector


class LocalRoadsFallbackConnector(MappingConnector):
    """
    Local road network estimator with empirical urban winding factor.
    Returns status 'ESTIMATED_OFFLINE' so straight-line distance is never claimed as Google live traffic ETA.
    """

    ROAD_WINDING_FACTOR = 1.35  # Actual road distance is ~35% longer than great-circle
    AVG_URBAN_SPEED_KMH = 30.0  # Average city driving speed (approx 8.33 m/s)

    def _haversine_meters(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Great-circle distance in meters between two lat/lon points."""
        r = 6371000.0  # Earth radius in meters
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = math.sin(delta_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2)
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        return r * c

    def _traffic_multiplier(self) -> float:
        """Slight penalty during morning (8-10am) and evening (5-7pm) rush hours."""
        hour = datetime.now().hour
        if 8 <= hour <= 10 or 17 <= hour <= 19:
            return 1.30  # 30% slower during peak commute
        return 1.05  # General urban intersections and lights

    async def geocode(self, address: str) -> dict[str, Any]:
        """Simple local resolver for common test/urban addresses or fallback coordinates."""
        addr_lower = (address or "").lower()
        # Default mock urban coordinates (e.g. Bangalore / Tech Corridor)
        base_lat, base_lng = 12.9716, 77.5946
        
        # Specific known hub offsets
        if "whitefield" in addr_lower:
            base_lat, base_lng = 12.9698, 77.7500
        elif "koramangala" in addr_lower or "south" in addr_lower:
            base_lat, base_lng = 12.9352, 77.6245
        elif "indiranagar" in addr_lower or "east" in addr_lower:
            base_lat, base_lng = 12.9784, 77.6408
        elif "electronic city" in addr_lower:
            base_lat, base_lng = 12.8399, 77.6770
        elif "north" in addr_lower or "airport" in addr_lower:
            base_lat, base_lng = 13.1986, 77.7066

        return {
            "latitude": round(base_lat, 6),
            "longitude": round(base_lng, 6),
            "formatted_address": address.strip() or "Standard Project Location",
            "provider": "local_fallback",
            "status": "ESTIMATED_OFFLINE",
        }

    async def calculate_route(
        self,
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float,
    ) -> dict[str, Any]:
        """Calculates road-estimated distance and duration."""
        straight_dist = self._haversine_meters(origin_lat, origin_lng, dest_lat, dest_lng)
        road_distance = straight_dist * self.ROAD_WINDING_FACTOR
        
        # Speed in meters per second
        speed_mps = (self.AVG_URBAN_SPEED_KMH * 1000.0) / 3600.0
        duration_sec = (road_distance / speed_mps) * self._traffic_multiplier()

        dist_km = round(road_distance / 1000.0, 1)
        dur_min = max(3, int(round(duration_sec / 60.0)))

        return {
            "distance_meters": int(round(road_distance)),
            "duration_seconds": int(round(duration_sec)),
            "distance_text": f"{dist_km} km",
            "duration_text": f"{dur_min} mins",
            "provider": "local_fallback",
            "status": "ESTIMATED_OFFLINE",
        }

    async def calculate_matrix(
        self,
        origins: list[tuple[float, float]],
        destinations: list[tuple[float, float]],
    ) -> dict[str, Any]:
        """Calculates NxM travel-time and distance matrix."""
        duration_matrix: list[list[int]] = []
        distance_matrix: list[list[int]] = []

        speed_mps = (self.AVG_URBAN_SPEED_KMH * 1000.0) / 3600.0
        traffic = self._traffic_multiplier()

        for o_lat, o_lng in origins:
            dur_row: list[int] = []
            dist_row: list[int] = []
            for d_lat, d_lng in destinations:
                straight_dist = self._haversine_meters(o_lat, o_lng, d_lat, d_lng)
                road_dist = straight_dist * self.ROAD_WINDING_FACTOR
                dur_sec = max(180, int((road_dist / speed_mps) * traffic)) if straight_dist > 50 else 0
                dur_row.append(dur_sec)
                dist_row.append(int(road_dist))
            duration_matrix.append(dur_row)
            distance_matrix.append(dist_row)

        return {
            "duration_matrix": duration_matrix,
            "distance_matrix": distance_matrix,
            "provider": "local_fallback",
            "status": "ESTIMATED_OFFLINE",
        }
