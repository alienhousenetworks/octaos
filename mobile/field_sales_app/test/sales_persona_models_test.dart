import 'package:flutter_test/flutter_test.dart';
import 'package:field_sales_app/constants/api_endpoints.dart';
import 'package:field_sales_app/models/project.dart';
import 'package:field_sales_app/models/unit.dart';
import 'package:field_sales_app/models/lead_item.dart';
import 'package:field_sales_app/models/agent_profile.dart';

void main() {
  group('Sales Persona Models & Endpoints Tests', () {
    test('ApiEndpoints constants are properly defined', () {
      expect(ApiEndpoints.agentProjects, '/sales-os/field-sales/agent/projects');
      expect(ApiEndpoints.agentLeads, '/sales-os/field-sales/agent/leads');
      expect(ApiEndpoints.agentProfile, '/sales-os/field-sales/agent/profile');
    });

    test('RealEstateProjectModel parses JSON correctly', () {
      final json = {
        'id': 'proj_101',
        'name': 'Skyline Terraces',
        'location': 'Whitefield',
        'city': 'Bengaluru',
        'address': 'ECC Road, Whitefield',
        'latitude': 12.9698,
        'longitude': 77.7499,
        'rera_number': 'PRM/KA/RERA/1251/446/PR/120224/006500',
        'amenities': ['Infinity Pool', 'Clubhouse', 'EV Charging'],
        'total_units': 150,
        'available_units': 42,
        'status': 'active',
        'assigned_role': 'primary_lead',
        'units_count': 150,
      };

      final project = RealEstateProjectModel.fromJson(json);
      expect(project.id, 'proj_101');
      expect(project.name, 'Skyline Terraces');
      expect(project.assignedRole, 'primary_lead');
      expect(project.availableUnits, 42);
      expect(project.amenities.length, 3);
    });

    test('RealEstateUnitModel parses and computes availability', () {
      final json = {
        'id': 'unit_301',
        'project_id': 'proj_101',
        'unit_number': 'T1-1204',
        'unit_type': '3BHK',
        'floor': 12,
        'carpet_sqft': 1680.0,
        'base_price': 18500000.0,
        'status': 'available',
        'version': 1,
      };

      final unit = RealEstateUnitModel.fromJson(json);
      expect(unit.unitNumber, 'T1-1204');
      expect(unit.unitType, '3BHK');
      expect(unit.isAvailable, true);
      expect(unit.isHold, false);
      expect(unit.basePrice, 18500000.0);
    });

    test('SalesLeadModel parses buyer preferences and visit status', () {
      final json = {
        'id': 'lead_501',
        'name': 'Rahul Sharma',
        'phone': '+919876543210',
        'email': 'rahul@example.com',
        'status': 'visit_scheduled',
        'score': 92,
        'project_name': 'Skyline Terraces',
        'unit_preference': '3BHK Luxury',
        'budget': '₹2.0 Cr',
        'purchase_purpose': 'Self-Use',
        'purchase_timeline': '30 Days',
        'why': 'AI matched showing inquiry with primary lead specialist',
        'has_visit_scheduled': true,
        'visit_scheduled_at': '2026-10-23T14:30:00Z',
        'visit_status': 'scheduled',
      };

      final lead = SalesLeadModel.fromJson(json);
      expect(lead.name, 'Rahul Sharma');
      expect(lead.score, 92);
      expect(lead.hasVisitScheduled, true);
      expect(lead.visitScheduledAt, isNotNull);
    });

    test('AgentProfileModel parses capacity and operational telemetry', () {
      final json = {
        'user_id': 'user_88',
        'name': 'Marcus Vance',
        'email': 'marcus@octaos.com',
        'phone': '+919988776655',
        'role': 'specialist',
        'designation': 'Real Estate Showing Specialist',
        'is_shift_active': true,
        'status': 'available',
        'working_hours_start': '09:00',
        'working_hours_end': '18:00',
        'max_visits_per_day': 6,
        'completed_visits_today': 2,
        'total_visits_today': 4,
        'assigned_projects_count': 3,
        'last_latitude': 12.9716,
        'last_longitude': 77.5946,
      };

      final profile = AgentProfileModel.fromJson(json);
      expect(profile.name, 'Marcus Vance');
      expect(profile.isShiftActive, true);
      expect(profile.completedVisitsToday, 2);
      expect(profile.maxVisitsPerDay, 6);
      expect(profile.assignedProjectsCount, 3);
    });
  });
}
