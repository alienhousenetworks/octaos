class AgentProfileModel {
  final String userId;
  final String name;
  final String email;
  final String phone;
  final String role;
  final String designation;
  final bool isShiftActive;
  final String status;
  final String workingHoursStart;
  final String workingHoursEnd;
  final int maxVisitsPerDay;
  final int completedVisitsToday;
  final int totalVisitsToday;
  final int assignedProjectsCount;
  final double? lastLatitude;
  final double? lastLongitude;

  AgentProfileModel({
    required this.userId,
    required this.name,
    required this.email,
    required this.phone,
    required this.role,
    required this.designation,
    required this.isShiftActive,
    required this.status,
    required this.workingHoursStart,
    required this.workingHoursEnd,
    required this.maxVisitsPerDay,
    required this.completedVisitsToday,
    required this.totalVisitsToday,
    required this.assignedProjectsCount,
    this.lastLatitude,
    this.lastLongitude,
  });

  factory AgentProfileModel.fromJson(Map<String, dynamic> json) {
    return AgentProfileModel(
      userId: json['user_id'] ?? '',
      name: json['name'] ?? 'Showing Specialist',
      email: json['email'] ?? '',
      phone: json['phone'] ?? '',
      role: json['role'] ?? 'sales_executive',
      designation: json['designation'] ?? 'Real Estate Showing Specialist',
      isShiftActive: json['is_shift_active'] ?? false,
      status: json['status'] ?? 'off_duty',
      workingHoursStart: json['working_hours_start'] ?? '09:00',
      workingHoursEnd: json['working_hours_end'] ?? '18:00',
      maxVisitsPerDay: json['max_visits_per_day'] ?? 6,
      completedVisitsToday: json['completed_visits_today'] ?? 0,
      totalVisitsToday: json['total_visits_today'] ?? 0,
      assignedProjectsCount: json['assigned_projects_count'] ?? 0,
      lastLatitude: (json['last_latitude'] as num?)?.toDouble(),
      lastLongitude: (json['last_longitude'] as num?)?.toDouble(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'user_id': userId,
      'name': name,
      'email': email,
      'phone': phone,
      'role': role,
      'designation': designation,
      'is_shift_active': isShiftActive,
      'status': status,
      'working_hours_start': workingHoursStart,
      'working_hours_end': workingHoursEnd,
      'max_visits_per_day': maxVisitsPerDay,
      'completed_visits_today': completedVisitsToday,
      'total_visits_today': totalVisitsToday,
      'assigned_projects_count': assignedProjectsCount,
      'last_latitude': lastLatitude,
      'last_longitude': lastLongitude,
    };
  }
}
