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

  Future<dynamic> postForm(String endpoint, Map<String, String> fields) async {
    final url = Uri.parse('$baseUrl$endpoint');
    final headers = Map<String, String>.from(_headers());
    headers['Content-Type'] = 'application/x-www-form-urlencoded';
    final response = await http
        .post(url, headers: headers, body: fields)
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
        final d = bodyJson['detail'];
        if (d is String) {
          detail = d;
        } else if (d is List) {
          final msgs = d
              .map((item) {
                if (item is Map && item['msg'] != null) {
                  final locList = (item['loc'] is List) ? (item['loc'] as List) : [];
                  final loc = locList.where((l) => l.toString() != 'body').join('.');
                  return loc.isNotEmpty ? '${item['msg']} ($loc)' : item['msg'].toString();
                }
                return item.toString();
              })
              .where((m) => m.isNotEmpty)
              .toList();
          detail = msgs.isNotEmpty ? msgs.join(', ') : d.toString();
        } else {
          detail = d.toString();
        }
      } else if (response.statusCode == 400) {
        detail = 'Invalid email or password';
      } else if (response.statusCode == 401) {
        detail = 'Invalid credentials or session expired';
      } else if (response.statusCode == 403) {
        detail = 'Account is unverified or access is restricted';
      } else if (response.statusCode == 404) {
        detail = 'Service endpoint not found (${response.statusCode})';
      } else if (response.statusCode >= 500) {
        detail = 'Server error (${response.statusCode}). Please try again later.';
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
