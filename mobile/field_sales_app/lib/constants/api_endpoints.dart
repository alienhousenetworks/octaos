class ApiEndpoints {
  // Default OctaOS Production API endpoint (derives from http://151.242.187.221/app/home)
  static const String defaultBaseUrl = 'http://151.242.187.221/api/v1';

  /// Sanitizes any user input (e.g. "http://151.242.187.221/app/home") into a valid API endpoint
  static String normalizeBaseUrl(String input) {
    var trimmed = input.trim();
    if (trimmed.isEmpty) return defaultBaseUrl;
    if (!trimmed.startsWith('http://') && !trimmed.startsWith('https://')) {
      trimmed = 'http://$trimmed';
    }
    final uri = Uri.tryParse(trimmed);
    if (uri != null && uri.host.isNotEmpty) {
      final portSuffix = (uri.hasPort && uri.port != 80 && uri.port != 443) ? ':${uri.port}' : '';
      var path = uri.path.replaceAll(RegExp(r'/+$'), '');
      if (path.isEmpty || path.startsWith('/app') || !path.endsWith('/api/v1')) {
        path = '/api/v1';
      }
      return '${uri.scheme}://${uri.host}$portSuffix$path';
    }
    return trimmed;
  }

  static const String login = '/auth/login';
  static const String agentLocation = '/sales-os/field-sales/agent/location';
  static const String agentShift = '/sales-os/field-sales/agent/shift';
  static const String myDay = '/sales-os/field-sales/agent/my-day';
  static const String visitCheckIn = '/sales-os/field-sales/visits'; // + /{id}/check-in
  static const String visitOutcome = '/sales-os/field-sales/visits'; // + /{id}/outcome
  static const String aiRecover = '/sales-os/field-sales/ai/recover';
  static const String aiProposals = '/sales-os/field-sales/ai/proposals';
  static const String offlineSync = '/sales-os/field-sales/sync/offline';
  static const String agentProjects = '/sales-os/field-sales/agent/projects';
  static const String agentLeads = '/sales-os/field-sales/agent/leads';
  static const String agentProfile = '/sales-os/field-sales/agent/profile';
}
