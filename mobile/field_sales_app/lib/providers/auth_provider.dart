import 'package:flutter/foundation.dart';
import 'package:field_sales_app/services/api_service.dart';
import 'package:field_sales_app/services/storage_service.dart';

class AuthProvider extends ChangeNotifier {
  final StorageService storage;
  final ApiService api;

  bool _isLoading = false;
  String? _errorMessage;

  AuthProvider(this.storage, this.api) {
    _restore();
  }

  bool get isLoading => _isLoading;
  String? get errorMessage => _errorMessage;
  bool get isAuthenticated => storage.getToken() != null;
  String? get userId => storage.getUserId();
  String? get tenantId => storage.getTenantId();

  void _restore() {
    notifyListeners();
  }

  Future<bool> login({
    required String email,
    required String password,
    required String tenantId,
    String? customBaseUrl,
  }) async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    if (customBaseUrl != null && customBaseUrl.trim().isNotEmpty) {
      await storage.setBaseUrl(customBaseUrl.trim());
    }

    try {
      final res = await api.post('/auth/login', {
        'email': email.trim(),
        'password': password,
        'tenant_id': tenantId.trim(),
      });

      final accessToken = res['access_token'] ?? res['token'];
      if (accessToken == null) {
        throw Exception('Server did not return an access token.');
      }

      await storage.setToken(accessToken);
      await storage.setTenantId(tenantId.trim());
      await storage.setUserId(res['user_id'] ?? email.trim());

      _isLoading = false;
      notifyListeners();
      return true;
    } catch (e) {
      _isLoading = false;
      _errorMessage = e.toString();
      notifyListeners();
      return false;
    }
  }

  Future<void> logout() async {
    await storage.clearAuth();
    notifyListeners();
  }
}
