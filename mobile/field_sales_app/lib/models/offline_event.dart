import 'dart:convert';

class OfflineEvent {
  final String id;
  final String type; // check_in, outcome
  final String visitId;
  final Map<String, dynamic> payload;
  final DateTime createdAt;
  int retryCount;

  OfflineEvent({
    required this.id,
    required this.type,
    required this.visitId,
    required this.payload,
    required this.createdAt,
    this.retryCount = 0,
  });

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'type': type,
      'visit_id': visitId,
      'payload': payload,
      'created_at': createdAt.toIso8601String(),
      'retry_count': retryCount,
    };
  }

  factory OfflineEvent.fromJson(Map<String, dynamic> json) {
    return OfflineEvent(
      id: json['id'] ?? '',
      type: json['type'] ?? '',
      visitId: json['visit_id'] ?? '',
      payload: Map<String, dynamic>.from(json['payload'] ?? {}),
      createdAt: DateTime.tryParse(json['created_at'] ?? '') ?? DateTime.now(),
      retryCount: json['retry_count'] ?? 0,
    );
  }

  String serialize() => jsonEncode(toJson());

  factory OfflineEvent.deserialize(String source) => OfflineEvent.fromJson(jsonDecode(source));
}
