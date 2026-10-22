class RealEstateUnitModel {
  final String id;
  final String projectId;
  final String unitNumber;
  final String unitType;
  final String? tower;
  final int? floor;
  final double? carpetSqft;
  final double basePrice;
  final String status; // available, confirmed_hold, hold_requested, booked, sold
  final int version;

  RealEstateUnitModel({
    required this.id,
    required this.projectId,
    required this.unitNumber,
    required this.unitType,
    this.tower,
    this.floor,
    this.carpetSqft,
    required this.basePrice,
    required this.status,
    required this.version,
  });

  factory RealEstateUnitModel.fromJson(Map<String, dynamic> json) {
    return RealEstateUnitModel(
      id: json['id'] ?? '',
      projectId: json['project_id'] ?? '',
      unitNumber: json['unit_number'] ?? '',
      unitType: json['unit_type'] ?? 'Apartment',
      tower: json['tower'],
      floor: json['floor'] as int?,
      carpetSqft: (json['carpet_sqft'] as num?)?.toDouble(),
      basePrice: (json['base_price'] as num?)?.toDouble() ?? 0.0,
      status: json['status'] ?? 'available',
      version: json['version'] ?? 1,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'project_id': projectId,
      'unit_number': unitNumber,
      'unit_type': unitType,
      'tower': tower,
      'floor': floor,
      'carpet_sqft': carpetSqft,
      'base_price': basePrice,
      'status': status,
      'version': version,
    };
  }

  bool get isAvailable => status == 'available';
  bool get isHold => status == 'confirmed_hold' || status == 'hold_requested';
  bool get isBooked => status == 'booked' || status == 'sold';
}
