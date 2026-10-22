class ProposedChange {
  final String visitId;
  final String action;
  final DateTime originalTime;
  final DateTime proposedTime;
  final String rationale;
  final String? customerMessageDraft;

  ProposedChange({
    required this.visitId,
    required this.action,
    required this.originalTime,
    required this.proposedTime,
    required this.rationale,
    this.customerMessageDraft,
  });

  factory ProposedChange.fromJson(Map<String, dynamic> json) {
    return ProposedChange(
      visitId: json['visit_id'] ?? '',
      action: json['action'] ?? '',
      originalTime: DateTime.tryParse(json['original_time'] ?? '') ?? DateTime.now(),
      proposedTime: DateTime.tryParse(json['proposed_time'] ?? '') ?? DateTime.now(),
      rationale: json['rationale'] ?? '',
      customerMessageDraft: json['customer_message_draft'],
    );
  }
}

class MobileRecoveryProposal {
  final String id;
  final String rationale;
  final List<ProposedChange> changes;

  MobileRecoveryProposal({
    required this.id,
    required this.rationale,
    required this.changes,
  });

  factory MobileRecoveryProposal.fromJson(Map<String, dynamic> json) {
    var rawList = json['changes'] as List? ?? json['proposed_changes'] as List? ?? [];
    return MobileRecoveryProposal(
      id: json['id'] ?? '',
      rationale: json['rationale'] ?? '',
      changes: rawList.map((c) => ProposedChange.fromJson(c)).toList(),
    );
  }
}
