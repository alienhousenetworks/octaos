class RealEstateProjectModel {
  final String id;
  final String name;
  final String? code;
  final String? location;
  final String? city;
  final String address;
  final double latitude;
  final double longitude;
  final String? reraNumber;
  final List<String> amenities;
  final int totalUnits;
  final int availableUnits;
  final String status;
  final String assignedRole;
  final int unitsCount;

  RealEstateProjectModel({
    required this.id,
    required this.name,
    this.code,
    this.location,
    this.city,
    required this.address,
    required this.latitude,
    required this.longitude,
    this.reraNumber,
    required this.amenities,
    required this.totalUnits,
    required this.availableUnits,
    required this.status,
    required this.assignedRole,
    required this.unitsCount,
  });

  factory RealEstateProjectModel.fromJson(Map<String, dynamic> json) {
    return RealEstateProjectModel(
      id: json['id'] ?? '',
      name: json['name'] ?? 'Project',
      code: json['code'],
      location: json['location'],
      city: json['city'],
      address: json['address'] ?? json['location'] ?? 'Site Location',
      latitude: (json['latitude'] as num?)?.toDouble() ?? 12.9716,
      longitude: (json['longitude'] as num?)?.toDouble() ?? 77.5946,
      reraNumber: json['rera_number'],
      amenities: (json['amenities'] as List<dynamic>?)
              ?.map((e) => e.toString())
              .toList() ??
          [],
      totalUnits: json['total_units'] ?? 0,
      availableUnits: json['available_units'] ?? 0,
      status: json['status'] ?? 'active',
      assignedRole: json['assigned_role'] ?? 'specialist',
      unitsCount: json['units_count'] ?? 0,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'code': code,
      'location': location,
      'city': city,
      'address': address,
      'latitude': latitude,
      'longitude': longitude,
      'rera_number': reraNumber,
      'amenities': amenities,
      'total_units': totalUnits,
      'available_units': availableUnits,
      'status': status,
      'assigned_role': assignedRole,
      'units_count': unitsCount,
    };
  }
}
