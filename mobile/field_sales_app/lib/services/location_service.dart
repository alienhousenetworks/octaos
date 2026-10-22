import 'dart:math';
import 'package:geolocator/geolocator.dart';

class LocationService {
  static const double geofenceRadiusMeters = 250.0;

  /// Pure mathematical distance calculation (Haversine formula).
  static double calculateDistanceMeters(
    double lat1,
    double lon1,
    double lat2,
    double lon2,
  ) {
    const double r = 6371000.0; // Earth radius in meters
    final double phi1 = lat1 * (pi / 180.0);
    final double phi2 = lat2 * (pi / 180.0);
    final double dphi = (lat2 - lat1) * (pi / 180.0);
    final double dlambda = (lon2 - lon1) * (pi / 180.0);

    final double a = sin(dphi / 2.0) * sin(dphi / 2.0) +
        cos(phi1) * cos(phi2) * sin(dlambda / 2.0) * sin(dlambda / 2.0);
    final double c = 2.0 * atan2(sqrt(a), sqrt(1.0 - a));

    return r * c;
  }

  /// Request permissions and obtain device GPS location.
  Future<Position?> getCurrentPosition() async {
    bool serviceEnabled = await Geolocator.isLocationServiceEnabled();
    if (!serviceEnabled) {
      throw Exception('Location services are disabled on your phone. Please enable GPS.');
    }

    LocationPermission permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
      if (permission == LocationPermission.denied) {
        throw Exception('Location permission denied. Please allow location access to check in at properties.');
      }
    }

    if (permission == LocationPermission.deniedForever) {
      throw Exception('Location permissions are permanently denied. Please enable them in your device settings.');
    }

    return await Geolocator.getCurrentPosition(
      locationSettings: const LocationSettings(
        accuracy: LocationAccuracy.high,
        timeLimit: Duration(seconds: 10),
      ),
    );
  }

  /// Evaluates whether coordinates fall within the property geofence.
  bool isWithinGeofence({
    required double currentLat,
    required double currentLng,
    required double propertyLat,
    required double propertyLng,
    double radiusMeters = geofenceRadiusMeters,
  }) {
    final dist = calculateDistanceMeters(currentLat, currentLng, propertyLat, propertyLng);
    return dist <= radiusMeters;
  }
}
