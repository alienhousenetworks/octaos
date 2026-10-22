class AgentStatus {
  final String userId;
  final bool isShiftActive;
  final String status; // off_duty, available, en_route, in_showing, on_break
  final double? latitude;
  final double? longitude;
  final double? accuracy;
  final int? batteryLevel;

  AgentStatus({
    required this.userId,
    required this.isShiftActive,
    required this.status,
    this.latitude,
    this.longitude,
    this.accuracy,
    this.batteryLevel,
  });

  factory AgentStatus.fromJson(Map<String, dynamic> json) {
    return AgentStatus(
      userId: json['user_id'] ?? '',
      isShiftActive: json['is_shift_active'] ?? false,
      status: json['status'] ?? 'off_duty',
      latitude: (json['latitude'] as num?)?.toDouble(),
      longitude: (json['longitude'] as num?)?.toDouble(),
      accuracy: (json['accuracy'] as num?)?.toDouble(),
      batteryLevel: json['battery_level'],
    );
  }
}
