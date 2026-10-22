class FieldVisit {
  final String id;
  final String projectName;
  final String projectAddress;
  final double latitude;
  final double longitude;
  final String buyerName;
  final String buyerPhone;
  final String buyerEmail;
  final String? unitNumber;
  final String? unitType;
  final DateTime scheduledAt;
  final int durationMinutes;
  final int sequenceOrder;
  final int estimatedTravelMinutes;
  final String status; // scheduled, en_route, arrived, completed, cancelled, delayed, no_show
  final bool checkInVerified;
  final String? recoveryNotes;

  FieldVisit({
    required this.id,
    required this.projectName,
    required this.projectAddress,
    required this.latitude,
    required this.longitude,
    required this.buyerName,
    required this.buyerPhone,
    required this.buyerEmail,
    this.unitNumber,
    this.unitType,
    required this.scheduledAt,
    required this.durationMinutes,
    required this.sequenceOrder,
    required this.estimatedTravelMinutes,
    required this.status,
    required this.checkInVerified,
    this.recoveryNotes,
  });

  factory FieldVisit.fromJson(Map<String, dynamic> json) {
    return FieldVisit(
      id: json['id'] ?? '',
      projectName: json['project_name'] ?? 'Property Site',
      projectAddress: json['project_address'] ?? 'Site Location',
      latitude: (json['latitude'] as num?)?.toDouble() ?? 12.9716,
      longitude: (json['longitude'] as num?)?.toDouble() ?? 77.5946,
      buyerName: json['buyer_name'] ?? 'Prospective Buyer',
      buyerPhone: json['buyer_phone'] ?? '',
      buyerEmail: json['buyer_email'] ?? '',
      unitNumber: json['unit_number'],
      unitType: json['unit_type'],
      scheduledAt: DateTime.tryParse(json['scheduled_at'] ?? '') ?? DateTime.now(),
      durationMinutes: json['duration_minutes'] ?? 45,
      sequenceOrder: json['sequence_order'] ?? 1,
      estimatedTravelMinutes: json['estimated_travel_minutes'] ?? 15,
      status: json['status'] ?? 'scheduled',
      checkInVerified: json['check_in_verified'] ?? false,
      recoveryNotes: json['recovery_notes'],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'project_name': projectName,
      'project_address': projectAddress,
      'latitude': latitude,
      'longitude': longitude,
      'buyer_name': buyerName,
      'buyer_phone': buyerPhone,
      'buyer_email': buyerEmail,
      'unit_number': unitNumber,
      'unit_type': unitType,
      'scheduled_at': scheduledAt.toIso8601String(),
      'duration_minutes': durationMinutes,
      'sequence_order': sequenceOrder,
      'estimated_travel_minutes': estimatedTravelMinutes,
      'status': status,
      'check_in_verified': checkInVerified,
      'recovery_notes': recoveryNotes,
    };
  }
}
