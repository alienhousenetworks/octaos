class SalesLeadModel {
  final String id;
  final String name;
  final String phone;
  final String email;
  final String status;
  final int score;
  final String projectName;
  final String unitPreference;
  final String budget;
  final String purchasePurpose;
  final String purchaseTimeline;
  final String why;
  final bool hasVisitScheduled;
  final DateTime? visitScheduledAt;
  final String? visitStatus;

  SalesLeadModel({
    required this.id,
    required this.name,
    required this.phone,
    required this.email,
    required this.status,
    required this.score,
    required this.projectName,
    required this.unitPreference,
    required this.budget,
    required this.purchasePurpose,
    required this.purchaseTimeline,
    required this.why,
    required this.hasVisitScheduled,
    this.visitScheduledAt,
    this.visitStatus,
  });

  factory SalesLeadModel.fromJson(Map<String, dynamic> json) {
    return SalesLeadModel(
      id: json['id'] ?? '',
      name: json['name'] ?? 'Prospective Buyer',
      phone: json['phone'] ?? '',
      email: json['email'] ?? '',
      status: json['status'] ?? 'inquiry',
      score: json['score'] ?? 50,
      projectName: json['project_name'] ?? 'Featured Residence',
      unitPreference: json['unit_preference'] ?? '3BHK Luxury',
      budget: json['budget'] ?? '₹1.5Cr - ₹2.5Cr',
      purchasePurpose: json['purchase_purpose'] ?? 'Self-Use',
      purchaseTimeline: json['purchase_timeline'] ?? '30 Days',
      why: json['why'] ?? 'Matched showing inquiry',
      hasVisitScheduled: json['has_visit_scheduled'] ?? false,
      visitScheduledAt: json['visit_scheduled_at'] != null
          ? DateTime.tryParse(json['visit_scheduled_at'])
          : null,
      visitStatus: json['visit_status'],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'phone': phone,
      'email': email,
      'status': status,
      'score': score,
      'project_name': projectName,
      'unit_preference': unitPreference,
      'budget': budget,
      'purchase_purpose': purchasePurpose,
      'purchase_timeline': purchaseTimeline,
      'why': why,
      'has_visit_scheduled': hasVisitScheduled,
      'visit_scheduled_at': visitScheduledAt?.toIso8601String(),
      'visit_status': visitStatus,
    };
  }
}
