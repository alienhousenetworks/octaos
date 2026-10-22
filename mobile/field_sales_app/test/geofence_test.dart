import 'package:flutter_test/flutter_test.dart';
import 'package:field_sales_app/services/location_service.dart';

void main() {
  group('LocationService & Geofencing Math Tests', () {
    test('Same coordinate distance returns 0.0', () {
      final dist = LocationService.calculateDistanceMeters(12.9716, 77.5946, 12.9716, 77.5946);
      expect(dist, 0.0);
    });

    test('Short proximity distance (< 250m) is within geofence', () {
      // 0.001 degree of latitude is roughly ~111 meters
      final lat1 = 12.9716;
      final lon1 = 77.5946;
      final lat2 = 12.9726; // approx 111m away
      final lon2 = 77.5946;

      final dist = LocationService.calculateDistanceMeters(lat1, lon1, lat2, lon2);
      expect(dist, greaterThan(100.0));
      expect(dist, lessThan(125.0));

      final service = LocationService();
      final inFence = service.isWithinGeofence(
        currentLat: lat2,
        currentLng: lon2,
        propertyLat: lat1,
        propertyLng: lon1,
      );
      expect(inFence, isTrue);
    });

    test('Distance outside 250m (> 500m) is outside geofence', () {
      // 0.008 degree of latitude is roughly ~888 meters
      final lat1 = 12.9716;
      final lon1 = 77.5946;
      final lat2 = 12.9800;
      final lon2 = 77.5946;

      final dist = LocationService.calculateDistanceMeters(lat1, lon1, lat2, lon2);
      expect(dist, greaterThan(500.0));

      final service = LocationService();
      final inFence = service.isWithinGeofence(
        currentLat: lat2,
        currentLng: lon2,
        propertyLat: lat1,
        propertyLng: lon1,
      );
      expect(inFence, isFalse);
    });
  });
}
