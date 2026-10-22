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
      dynamic res;
      try {
        // FastAPI OAuth2PasswordRequestForm expects application/x-www-form-urlencoded with 'username' and 'password'
        res = await api.postForm('/auth/login', {
          'username': email.trim(),
          'password': password,
        });
      } catch (err) {
        // Fallback to JSON login initiate if OAuth2 form fails with 404/422
        if (err is ApiException && (err.statusCode == 404 || err.statusCode == 422)) {
          res = await api.post('/auth/login/initiate', {
            'email': email.trim(),
            'password': password,
            if (tenantId.trim().isNotEmpty) 'tenant_id': tenantId.trim(),
          });
        } else {
          rethrow;
        }
      }

      final accessToken = res['access_token'] ?? res['token'];
      if (accessToken == null) {
        throw Exception('Server did not return an access token.');
      }

      await storage.setToken(accessToken.toString());
      final resolvedTenantId = (res['tenant_id'] != null && res['tenant_id'].toString().trim().isNotEmpty)
          ? res['tenant_id'].toString().trim()
          : tenantId.trim();
      await storage.setTenantId(resolvedTenantId);
      await storage.setUserId(res['user_id']?.toString() ?? email.trim());

      _isLoading = false;
      notifyListeners();
      return true;
    } catch (e) {
      _isLoading = false;
      var msg = e.toString();
      if (msg.startsWith('Exception: ')) {
        msg = msg.substring('Exception: '.length);
      }
      _errorMessage = msg;
      notifyListeners();
      return false;
    }
  }

  Future<void> logout() async {
    await storage.clearAuth();
    notifyListeners();
  }
}
