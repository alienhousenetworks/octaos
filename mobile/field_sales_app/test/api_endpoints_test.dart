import 'package:flutter_test/flutter_test.dart';
import 'package:field_sales_app/constants/api_endpoints.dart';

void main() {
  group('ApiEndpoints URL Normalization Tests', () {
    test('Default base URL is production server API', () {
      expect(ApiEndpoints.defaultBaseUrl, 'http://151.242.187.221/api/v1');
    });

    test('Normalizes http://151.242.187.221/app/home to http://151.242.187.221/api/v1', () {
      final normalized = ApiEndpoints.normalizeBaseUrl('http://151.242.187.221/app/home');
      expect(normalized, 'http://151.242.187.221/api/v1');
    });

    test('Normalizes plain IP host http://151.242.187.221 to http://151.242.187.221/api/v1', () {
      final normalized = ApiEndpoints.normalizeBaseUrl('http://151.242.187.221');
      expect(normalized, 'http://151.242.187.221/api/v1');
    });

    test('Preserves already correct endpoint http://151.242.187.221/api/v1', () {
      final normalized = ApiEndpoints.normalizeBaseUrl('http://151.242.187.221/api/v1');
      expect(normalized, 'http://151.242.187.221/api/v1');
    });

    test('Trims trailing slashes correctly', () {
      final normalized = ApiEndpoints.normalizeBaseUrl('http://151.242.187.221/api/v1///');
      expect(normalized, 'http://151.242.187.221/api/v1');
    });

    test('Preserves custom dev ports if provided', () {
      final normalized = ApiEndpoints.normalizeBaseUrl('http://151.242.187.221:8000');
      expect(normalized, 'http://151.242.187.221:8000/api/v1');
    });

    test('Handles scheme-less input by prepending http://', () {
      final normalized = ApiEndpoints.normalizeBaseUrl('151.242.187.221/app/home');
      expect(normalized, 'http://151.242.187.221/api/v1');
    });

    test('Empty input returns default base URL', () {
      final normalized = ApiEndpoints.normalizeBaseUrl('   ');
      expect(normalized, ApiEndpoints.defaultBaseUrl);
    });
  });
}
