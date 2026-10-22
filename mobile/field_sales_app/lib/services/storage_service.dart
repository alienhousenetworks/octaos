import 'package:shared_preferences/shared_preferences.dart';
import '../constants/api_endpoints.dart';

class StorageService {
  static const String _keyToken = 'octa_jwt_token';
  static const String _keyTenantId = 'octa_tenant_id';
  static const String _keyUserId = 'octa_user_id';
  static const String _keyBaseUrl = 'octa_base_url';
  static const String _keyOfflineQueue = 'octa_offline_queue';

  final SharedPreferences prefs;

  StorageService(this.prefs);

  static Future<StorageService> init() async {
    final sp = await SharedPreferences.getInstance();
    return StorageService(sp);
  }

  // Auth tokens
  String? getToken() => prefs.getString(_keyToken);
  Future<void> setToken(String token) => prefs.setString(_keyToken, token);

  String? getTenantId() => prefs.getString(_keyTenantId);
  Future<void> setTenantId(String tenantId) => prefs.setString(_keyTenantId, tenantId);

  String? getUserId() => prefs.getString(_keyUserId);
  Future<void> setUserId(String userId) => prefs.setString(_keyUserId, userId);

  String getBaseUrl() => prefs.getString(_keyBaseUrl) ?? ApiEndpoints.defaultBaseUrl;
  Future<void> setBaseUrl(String url) => prefs.setString(_keyBaseUrl, ApiEndpoints.normalizeBaseUrl(url));

  Future<void> clearAuth() async {
    await prefs.remove(_keyToken);
    await prefs.remove(_keyTenantId);
    await prefs.remove(_keyUserId);
  }

  // Offline event queue
  List<String> getOfflineQueue() => prefs.getStringList(_keyOfflineQueue) ?? [];
  Future<void> setOfflineQueue(List<String> list) => prefs.setStringList(_keyOfflineQueue, list);
}
