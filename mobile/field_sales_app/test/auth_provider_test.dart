import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:field_sales_app/services/storage_service.dart';
import 'package:field_sales_app/services/api_service.dart';
import 'package:field_sales_app/providers/auth_provider.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('AuthProvider Tests', () {
    late StorageService storage;

    setUp(() async {
      SharedPreferences.setMockInitialValues({});
      storage = await StorageService.init();
    });

    test('Initial unauthenticated state', () {
      final api = ApiService(storage);
      final auth = AuthProvider(storage, api);

      expect(auth.isAuthenticated, isFalse);
      expect(auth.isLoading, isFalse);
      expect(auth.errorMessage, isNull);
    });

    test('Logout clears storage and notifies', () async {
      await storage.setToken('test-token');
      await storage.setTenantId('test-tenant');
      await storage.setUserId('test-user');

      final api = ApiService(storage);
      final auth = AuthProvider(storage, api);

      expect(auth.isAuthenticated, isTrue);
      await auth.logout();
      expect(auth.isAuthenticated, isFalse);
      expect(storage.getToken(), isNull);
    });
  });
}
