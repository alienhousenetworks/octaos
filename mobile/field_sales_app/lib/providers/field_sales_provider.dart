import 'package:flutter/foundation.dart';
import 'package:field_sales_app/models/visit.dart';
import 'package:field_sales_app/models/recovery_proposal.dart';
import 'package:field_sales_app/models/project.dart';
import 'package:field_sales_app/models/unit.dart';
import 'package:field_sales_app/models/lead_item.dart';
import 'package:field_sales_app/models/agent_profile.dart';
import 'package:field_sales_app/services/api_service.dart';
import 'package:field_sales_app/services/offline_sync_service.dart';

class FieldSalesProvider extends ChangeNotifier {
  final ApiService api;
  final OfflineSyncService offlineSync;

  bool _isLoading = false;
  String? _errorMessage;

  List<FieldVisit> _visits = [];
  bool _isShiftActive = false;
  String _agentStatus = 'off_duty';
  MobileRecoveryProposal? _pendingProposal;

  // Real estate sales persona collections
  List<RealEstateProjectModel> _projects = [];
  bool _projectsLoading = false;
  List<SalesLeadModel> _leads = [];
  bool _leadsLoading = false;
  AgentProfileModel? _profile;
  bool _profileLoading = false;

  FieldSalesProvider(this.api, this.offlineSync);

  bool get isLoading => _isLoading;
  String? get errorMessage => _errorMessage;
  List<FieldVisit> get visits => _visits;
  bool get isShiftActive => _isShiftActive;
  String get agentStatus => _agentStatus;
  MobileRecoveryProposal? get pendingProposal => _pendingProposal;
  int get pendingOfflineCount => offlineSync.getPendingEvents().length;

  List<RealEstateProjectModel> get projects => _projects;
  bool get projectsLoading => _projectsLoading;
  List<SalesLeadModel> get leads => _leads;
  bool get leadsLoading => _leadsLoading;
  AgentProfileModel? get profile => _profile;
  bool get profileLoading => _profileLoading;

  FieldVisit? get nextVisit {
    try {
      return _visits.firstWhere(
        (v) => v.status == 'scheduled' || v.status == 'delayed' || v.status == 'en_route',
      );
    } catch (_) {
      return null;
    }
  }

  Future<void> loadMyDay() async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      final res = await api.get('/sales-os/field-sales/agent/my-day');
      _isShiftActive = res['is_shift_active'] ?? false;
      _agentStatus = res['agent_status'] ?? 'off_duty';

      final rawVisits = res['visits'] as List? ?? [];
      _visits = rawVisits.map((v) => FieldVisit.fromJson(v)).toList();

      if (res['pending_proposal'] != null) {
        _pendingProposal = MobileRecoveryProposal.fromJson(res['pending_proposal']);
      } else {
        _pendingProposal = null;
      }

      _isLoading = false;
      notifyListeners();
    } catch (e) {
      _isLoading = false;
      _errorMessage = e.toString();
      notifyListeners();
    }
  }

  Future<bool> toggleShift(bool active) async {
    try {
      final res = await api.post('/sales-os/field-sales/agent/shift', {
        'is_active': active,
        'status': active ? 'available' : 'off_duty',
      });
      _isShiftActive = res['is_shift_active'] ?? active;
      _agentStatus = res['status'] ?? (active ? 'available' : 'off_duty');
      notifyListeners();
      return true;
    } catch (e) {
      _errorMessage = e.toString();
      notifyListeners();
      return false;
    }
  }

  Future<void> reportLocation({
    required double latitude,
    required double longitude,
    double accuracy = 10.0,
    int? batteryLevel,
    double? speed,
    double? heading,
  }) async {
    try {
      await api.post('/sales-os/field-sales/agent/location', {
        'latitude': latitude,
        'longitude': longitude,
        'accuracy': accuracy,
        'battery_level': batteryLevel,
        'speed': speed,
        'heading': heading,
      });
    } catch (_) {
      // Background location failure is non-fatal
    }
  }

  Future<bool> performCheckIn({
    required String visitId,
    required double latitude,
    required double longitude,
    required double accuracy,
    String? manualExceptionReason,
  }) async {
    final payload = {
      'latitude': latitude,
      'longitude': longitude,
      'accuracy': accuracy,
      'manual_exception_reason': manualExceptionReason,
    };

    try {
      await api.post('/sales-os/field-sales/visits/$visitId/check-in', payload);
      await loadMyDay();
      return true;
    } catch (e) {
      // If network failure, queue offline
      await offlineSync.enqueueEvent(
        type: 'check_in',
        visitId: visitId,
        payload: payload,
      );
      // Optimistically update local visit state
      _updateLocalVisitStatus(visitId, 'arrived');
      notifyListeners();
      return true;
    }
  }

  Future<bool> submitOutcome({
    required String visitId,
    required String status,
    String? tourFeedback,
    String? buyerInterestLevel,
    List<String> buyerObjections = const [],
    String? agreedNextStep,
  }) async {
    final payload = {
      'status': status,
      'tour_feedback': tourFeedback,
      'buyer_interest_level': buyerInterestLevel,
      'buyer_objections': buyerObjections,
      'agreed_next_step': agreedNextStep,
    };

    try {
      await api.post('/sales-os/field-sales/visits/$visitId/outcome', payload);
      await loadMyDay();
      return true;
    } catch (e) {
      // Offline fallback
      await offlineSync.enqueueEvent(
        type: 'outcome',
        visitId: visitId,
        payload: payload,
      );
      _updateLocalVisitStatus(visitId, status);
      notifyListeners();
      return true;
    }
  }

  Future<bool> reportDelay({
    required String visitId,
    required int delayMinutes,
    required String delayReason,
  }) async {
    try {
      await api.post('/sales-os/field-sales/ai/recover', {
        'visit_id': visitId,
        'delay_minutes': delayMinutes,
        'delay_reason': delayReason,
      });
      await loadMyDay();
      return true;
    } catch (e) {
      _errorMessage = e.toString();
      notifyListeners();
      return false;
    }
  }

  Future<bool> approveProposal(String proposalId) async {
    try {
      await api.post('/sales-os/field-sales/ai/proposals/$proposalId/approve', {});
      await loadMyDay();
      return true;
    } catch (e) {
      _errorMessage = e.toString();
      notifyListeners();
      return false;
    }
  }

  Future<int> triggerOfflineSync() async {
    try {
      final synced = await offlineSync.syncPending();
      if (synced > 0) {
        await loadMyDay();
      }
      return synced;
    } catch (e) {
      _errorMessage = e.toString();
      notifyListeners();
      return 0;
    }
  }

  Future<void> loadProjects() async {
    _projectsLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      final res = await api.get('/sales-os/field-sales/agent/projects');
      if (res is List) {
        _projects = res.map((p) => RealEstateProjectModel.fromJson(p)).toList();
      }
      _projectsLoading = false;
      notifyListeners();
    } catch (e) {
      _projectsLoading = false;
      _errorMessage = e.toString();
      notifyListeners();
    }
  }

  Future<List<RealEstateUnitModel>> loadProjectUnits(String projectId) async {
    try {
      final res = await api.get('/sales-os/field-sales/agent/projects/$projectId/units');
      if (res is List) {
        return res.map((u) => RealEstateUnitModel.fromJson(u)).toList();
      }
      return [];
    } catch (e) {
      _errorMessage = e.toString();
      notifyListeners();
      return [];
    }
  }

  Future<bool> reserveUnitOnSite({
    required String unitId,
    required String leadId,
    double depositAmount = 0.0,
    String? notes,
  }) async {
    try {
      await api.post('/sales-os/field-sales/agent/units/$unitId/hold', {
        'lead_id': leadId,
        'deposit_amount': depositAmount,
        'notes': notes ?? 'Reserved on-site via Mobile Sales App',
      });
      await loadProjects();
      return true;
    } catch (e) {
      _errorMessage = e.toString();
      notifyListeners();
      return false;
    }
  }

  Future<void> loadLeads() async {
    _leadsLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      final res = await api.get('/sales-os/field-sales/agent/leads');
      if (res is List) {
        _leads = res.map((l) => SalesLeadModel.fromJson(l)).toList();
      }
      _leadsLoading = false;
      notifyListeners();
    } catch (e) {
      _leadsLoading = false;
      _errorMessage = e.toString();
      notifyListeners();
    }
  }

  Future<void> loadProfile() async {
    _profileLoading = true;
    notifyListeners();

    try {
      final res = await api.get('/sales-os/field-sales/agent/profile');
      if (res is Map<String, dynamic>) {
        _profile = AgentProfileModel.fromJson(res);
        _isShiftActive = _profile!.isShiftActive;
        _agentStatus = _profile!.status;
      }
      _profileLoading = false;
      notifyListeners();
    } catch (e) {
      _profileLoading = false;
      _errorMessage = e.toString();
      notifyListeners();
    }
  }

  void _updateLocalVisitStatus(String visitId, String newStatus) {
    final idx = _visits.indexWhere((v) => v.id == visitId);
    if (idx != -1) {
      final old = _visits[idx];
      _visits[idx] = FieldVisit(
        id: old.id,
        projectName: old.projectName,
        projectAddress: old.projectAddress,
        latitude: old.latitude,
        longitude: old.longitude,
        buyerName: old.buyerName,
        buyerPhone: old.buyerPhone,
        buyerEmail: old.buyerEmail,
        unitNumber: old.unitNumber,
        unitType: old.unitType,
        scheduledAt: old.scheduledAt,
        durationMinutes: old.durationMinutes,
        sequenceOrder: old.sequenceOrder,
        estimatedTravelMinutes: old.estimatedTravelMinutes,
        status: newStatus,
        checkInVerified: old.checkInVerified,
        recoveryNotes: old.recoveryNotes,
      );
    }
  }
}
