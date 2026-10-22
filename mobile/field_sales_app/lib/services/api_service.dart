import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:field_sales_app/services/storage_service.dart';

class ApiService {
  final StorageService storage;

  ApiService(this.storage);

  String get baseUrl => storage.getBaseUrl();

  Map<String, String> _headers() {
    final token = storage.getToken();
    final tenantId = storage.getTenantId();
    final headers = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };
    if (token != null) {
      headers['Authorization'] = 'Bearer $token';
    }
    if (tenantId != null) {
      headers['X-Tenant-ID'] = tenantId;
    }
    return headers;
  }

  Future<dynamic> get(String endpoint) async {
    final url = Uri.parse('$baseUrl$endpoint');
    final response = await http.get(url, headers: _headers()).timeout(const Duration(seconds: 15));
    return _processResponse(response);
  }

  Future<dynamic> post(String endpoint, Map<String, dynamic> body) async {
    final url = Uri.parse('$baseUrl$endpoint');
    final response = await http
        .post(url, headers: _headers(), body: jsonEncode(body))
        .timeout(const Duration(seconds: 15));
    return _processResponse(response);
  }

  dynamic _processResponse(http.Response response) {
    final bodyStr = response.body;
    dynamic bodyJson;
    try {
      bodyJson = bodyStr.isNotEmpty ? jsonDecode(bodyStr) : null;
    } catch (_) {
      bodyJson = bodyStr;
    }

    if (response.statusCode >= 200 && response.statusCode < 300) {
      return bodyJson;
    } else {
      String detail = 'Request failed (${response.statusCode})';
      if (bodyJson is Map && bodyJson['detail'] != null) {
        detail = bodyJson['detail'].toString();
      }
      throw ApiException(detail, response.statusCode);
    }
  }
}

class ApiException implements Exception {
  final String message;
  final int statusCode;

  ApiException(this.message, this.statusCode);

  @override
  String toString() => message;
}
