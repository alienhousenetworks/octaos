"""Google Maps Platform connector using Routes API v2 and Geocoding API."""
from __future__ import annotations
import os
import httpx
from typing import Any
from app.services.sales_os.field_sales.connectors.base import MappingConnector
from app.services.sales_os.field_sales.connectors.local_fallback import LocalRoadsFallbackConnector


class GoogleMapsConnector(MappingConnector):
    """
    Connects to Google Routes API and Geocoding API when GOOGLE_MAPS_API_KEY is available.
    Degrades gracefully to LocalRoadsFallbackConnector if unconfigured or unreachable.
    """

    ROUTES_API_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"
    GEOCODING_API_URL = "https://maps.googleapis.com/maps/api/geocode/json"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("GOOGLE_MAPS_API_KEY")
        self.fallback = LocalRoadsFallbackConnector()

    async def geocode(self, address: str) -> dict[str, Any]:
        if not self.api_key:
            return await self.fallback.geocode(address)

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(
                    self.GEOCODING_API_URL,
                    params={"address": address, "key": self.api_key},
                )
                if res.status_code == 200:
                    data = res.json()
                    if data.get("status") == "OK" and data.get("results"):
                        first = data["results"][0]
                        loc = first["geometry"]["location"]
                        return {
                            "latitude": float(loc["lat"]),
                            "longitude": float(loc["lng"]),
                            "formatted_address": first.get("formatted_address", address),
                            "provider": "google_maps",
                            "status": "OK",
                        }
        except Exception:
            pass

        return await self.fallback.geocode(address)

    async def calculate_route(
        self,
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float,
    ) -> dict[str, Any]:
        if not self.api_key:
            return await self.fallback.calculate_route(origin_lat, origin_lng, dest_lat, dest_lng)

        payload = {
            "origin": {"location": {"latLng": {"latitude": origin_lat, "longitude": origin_lng}}},
            "destination": {"location": {"latLng": {"latitude": dest_lat, "longitude": dest_lng}}},
            "travelMode": "DRIVE",
            "routingPreference": "TRAFFIC_AWARE",
        }
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": "routes.duration,routes.distanceMeters,routes.polyline.encodedPolyline",
        }

        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                res = await client.post(self.ROUTES_API_URL, json=payload, headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    routes = data.get("routes", [])
                    if routes:
                        r = routes[0]
                        dur_str = r.get("duration", "0s").rstrip("s")
                        duration_sec = int(dur_str) if dur_str.isdigit() else 300
                        dist_meters = int(r.get("distanceMeters", 1000))
                        dist_km = round(dist_meters / 1000.0, 1)
                        dur_min = max(1, int(round(duration_sec / 60.0)))
                        return {
                            "distance_meters": dist_meters,
                            "duration_seconds": duration_sec,
                            "distance_text": f"{dist_km} km",
                            "duration_text": f"{dur_min} mins",
                            "polyline": r.get("polyline", {}).get("encodedPolyline"),
                            "provider": "google_maps",
                            "status": "OK",
                        }
        except Exception:
            pass

        return await self.fallback.calculate_route(origin_lat, origin_lng, dest_lat, dest_lng)

    async def calculate_matrix(
        self,
        origins: list[tuple[float, float]],
        destinations: list[tuple[float, float]],
    ) -> dict[str, Any]:
        # Google Routes Matrix is billable per element. Delegate to fallback or compute elements if configured.
        if not self.api_key:
            return await self.fallback.calculate_matrix(origins, destinations)
        # For cost governance, fallback computes fast local road matrix
        return await self.fallback.calculate_matrix(origins, destinations)
