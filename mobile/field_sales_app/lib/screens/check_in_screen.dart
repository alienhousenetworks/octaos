import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:geolocator/geolocator.dart';
import 'package:field_sales_app/constants/theme.dart';
import 'package:field_sales_app/models/visit.dart';
import 'package:field_sales_app/services/location_service.dart';
import 'package:field_sales_app/providers/field_sales_provider.dart';

class CheckInScreen extends StatefulWidget {
  final FieldVisit visit;

  const CheckInScreen({Key? key, required this.visit}) : super(key: key);

  @override
  State<CheckInScreen> createState() => _CheckInScreenState();
}

class _CheckInScreenState extends State<CheckInScreen> {
  final LocationService _locationService = LocationService();

  bool _loadingLocation = true;
  Position? _currentPosition;
  double _distanceToProperty = 0.0;
  bool _isWithinGeofence = false;
  String? _locationError;

  // Manual exception override
  final _exceptionCtrl = TextEditingController();
  bool _showExceptionField = false;

  // Outcome submission state
  bool _isCheckedIn = false;
  String _outcomeStatus = 'completed';
  String _buyerInterest = 'high';
  final List<String> _selectedObjections = [];
  final _feedbackCtrl = TextEditingController();
  final _nextStepCtrl = TextEditingController(text: 'Send price sheet and floor plan via WhatsApp');
  bool _submitting = false;

  final List<String> _commonObjections = [
    'Price per sqft above budget',
    'Preferred higher floor',
    'Layout / room sizing concern',
    'Possession timeline delivery',
    'Insufficient parking spots',
  ];

  @override
  void initState() {
    super.initState();
    _isCheckedIn = widget.visit.status == 'arrived' || widget.visit.checkInVerified;
    _captureDeviceLocation();
  }

  Future<void> _captureDeviceLocation() async {
    setState(() {
      _loadingLocation = true;
      _locationError = null;
    });

    try {
      final pos = await _locationService.getCurrentPosition();
      if (pos != null) {
        final dist = LocationService.calculateDistanceMeters(
          pos.latitude,
          pos.longitude,
          widget.visit.latitude,
          widget.visit.longitude,
        );
        final inFence = dist <= LocationService.geofenceRadiusMeters;

        setState(() {
          _currentPosition = pos;
          _distanceToProperty = dist;
          _isWithinGeofence = inFence;
          _showExceptionField = !inFence;
          _loadingLocation = false;
        });
      }
    } catch (e) {
      setState(() {
        _locationError = e.toString();
        _showExceptionField = true;
        _loadingLocation = false;
      });
    }
  }

  Future<void> _handleCheckIn() async {
    if (_currentPosition == null && _exceptionCtrl.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please provide an exception reason if GPS is unavailable.')),
      );
      return;
    }

    if (!_isWithinGeofence && _exceptionCtrl.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Outside property geofence. A manual exception reason is required.')),
      );
      return;
    }

    setState(() => _submitting = true);
    final field = context.read<FieldSalesProvider>();

    final success = await field.performCheckIn(
      visitId: widget.visit.id,
      latitude: _currentPosition?.latitude ?? widget.visit.latitude,
      longitude: _currentPosition?.longitude ?? widget.visit.longitude,
      accuracy: _currentPosition?.accuracy ?? 25.0,
      manualExceptionReason: _isWithinGeofence ? null : _exceptionCtrl.text.trim(),
    );

    setState(() {
      _submitting = false;
      if (success) _isCheckedIn = true;
    });
  }

  Future<void> _handleCompleteShowing() async {
    setState(() => _submitting = true);
    final field = context.read<FieldSalesProvider>();

    final success = await field.submitOutcome(
      visitId: widget.visit.id,
      status: _outcomeStatus,
      tourFeedback: _feedbackCtrl.text.trim(),
      buyerInterestLevel: _buyerInterest,
      buyerObjections: _selectedObjections,
      agreedNextStep: _nextStepCtrl.text.trim(),
    );

    setState(() => _submitting = false);
    if (success && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Showing outcome logged successfully.')),
      );
      Navigator.of(context).pop();
    }
  }

  @override
  Widget build(BuildContext context) {
    final v = widget.visit;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Arrival & Showing Outcome'),
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // Step 1: GPS Arrival Check-in Card
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: OctaTheme.surface,
              borderRadius: BorderRadius.circular(14),
              border: Border.all(
                color: _isCheckedIn ? OctaTheme.success.withOpacity(0.5) : OctaTheme.border,
              ),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Text('STEP 1: ARRIVAL GEOFENCE CHECK', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: OctaTheme.textSecondary, letterSpacing: 0.8)),
                    if (_isCheckedIn)
                      const Row(
                        children: [
                          Icon(Icons.check_circle_rounded, size: 14, color: OctaTheme.success),
                          SizedBox(width: 4),
                          Text('Checked In', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: OctaTheme.success)),
                        ],
                      ),
                  ],
                ),
                const SizedBox(height: 12),
                Text(v.projectName, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: OctaTheme.textPrimary)),
                Text(v.projectAddress, style: const TextStyle(fontSize: 12, color: OctaTheme.textSecondary)),
                const SizedBox(height: 16),

                // Distance / Location Status Meter
                if (_loadingLocation)
                  const Row(
                    children: [
                      SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: OctaTheme.primary)),
                      SizedBox(width: 12),
                      Text('Querying device GPS satellites...', style: TextStyle(fontSize: 12, color: OctaTheme.textSecondary)),
                    ],
                  )
                else if (_locationError != null)
                  Container(
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: OctaTheme.danger.withOpacity(0.12),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Row(
                      children: [
                        const Icon(Icons.location_off_rounded, size: 16, color: OctaTheme.danger),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            'GPS Signal Weak: $_locationError',
                            style: const TextStyle(fontSize: 11, color: OctaTheme.danger),
                          ),
                        ),
                      ],
                    ),
                  )
                else ...[
                  Row(
                    children: [
                      Icon(
                        _isWithinGeofence ? Icons.verified_user_rounded : Icons.fmd_bad_rounded,
                        color: _isWithinGeofence ? OctaTheme.success : OctaTheme.warning,
                        size: 20,
                      ),
                      const SizedBox(width: 10),
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            _isWithinGeofence ? 'Verified Inside Property Perimeter' : 'Outside 250m Perimeter',
                            style: TextStyle(
                              fontSize: 13,
                              fontWeight: FontWeight.bold,
                              color: _isWithinGeofence ? OctaTheme.success : OctaTheme.warning,
                            ),
                          ),
                          Text(
                            'Distance: ${_distanceToProperty.toStringAsFixed(1)}m • Accuracy: ±${_currentPosition?.accuracy.toStringAsFixed(1)}m',
                            style: const TextStyle(fontSize: 11, color: OctaTheme.textMuted),
                          ),
                        ],
                      ),
                    ],
                  ),
                ],

                // Manual Exception input if outside or GPS error
                if (_showExceptionField && !_isCheckedIn) ...[
                  const SizedBox(height: 14),
                  const Text('Manual Exception Reason (Audit Required)', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: OctaTheme.warning)),
                  const SizedBox(height: 6),
                  TextField(
                    controller: _exceptionCtrl,
                    decoration: InputDecoration(
                      hintText: 'e.g. Inside basement parking / gate security deadzone',
                      hintStyle: const TextStyle(fontSize: 11, color: OctaTheme.textMuted),
                      filled: true,
                      fillColor: OctaTheme.background,
                      contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: const BorderSide(color: OctaTheme.border)),
                    ),
                    style: const TextStyle(fontSize: 12, color: OctaTheme.textPrimary),
                  ),
                ],

                if (!_isCheckedIn) ...[
                  const SizedBox(height: 16),
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton(
                      onPressed: _submitting ? null : _handleCheckIn,
                      child: _submitting
                          ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.black))
                          : const Text('Confirm GPS Arrival'),
                    ),
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(height: 20),

          // Step 2: Showing Outcome Form (Unlocked after arrival or always accessible)
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: OctaTheme.surface,
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: OctaTheme.border),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('STEP 2: RECORD SHOWING OUTCOME', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: OctaTheme.accent, letterSpacing: 0.8)),
                const SizedBox(height: 14),

                // Outcome Status
                const Text('Showing Status', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: OctaTheme.textPrimary)),
                const SizedBox(height: 8),
                Row(
                  children: [
                    {'id': 'completed', 'label': 'Completed'},
                    {'id': 'no_show', 'label': 'No-Show'},
                    {'id': 'rescheduled', 'label': 'Rescheduled'},
                  ].map((st) {
                    final isSel = _outcomeStatus == st['id'];
                    return Expanded(
                      child: GestureDetector(
                        onTap: () => setState(() => _outcomeStatus = st['id']!),
                        child: Container(
                          margin: const EdgeInsets.symmetric(horizontal: 3),
                          padding: const EdgeInsets.symmetric(vertical: 8),
                          decoration: BoxDecoration(
                            color: isSel ? OctaTheme.primary : OctaTheme.surfaceElevated,
                            borderRadius: BorderRadius.circular(8),
                          ),
                          alignment: Alignment.center,
                          child: Text(
                            st['label']!,
                            style: TextStyle(
                              fontSize: 11,
                              fontWeight: FontWeight.bold,
                              color: isSel ? Colors.black : OctaTheme.textPrimary,
                            ),
                          ),
                        ),
                      ),
                    );
                  }).toList(),
                ),
                const SizedBox(height: 16),

                // Buyer Interest Level
                const Text('Buyer Interest Rating', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: OctaTheme.textPrimary)),
                const SizedBox(height: 8),
                Row(
                  children: [
                    {'id': 'high', 'label': '🔥 High Interest'},
                    {'id': 'medium', 'label': '⚡ Medium'},
                    {'id': 'cold', 'label': '❄️ Cold'},
                  ].map((il) {
                    final isSel = _buyerInterest == il['id'];
                    return Expanded(
                      child: GestureDetector(
                        onTap: () => setState(() => _buyerInterest = il['id']!),
                        child: Container(
                          margin: const EdgeInsets.symmetric(horizontal: 3),
                          padding: const EdgeInsets.symmetric(vertical: 8),
                          decoration: BoxDecoration(
                            color: isSel ? OctaTheme.accent : OctaTheme.surfaceElevated,
                            borderRadius: BorderRadius.circular(8),
                          ),
                          alignment: Alignment.center,
                          child: Text(
                            il['label']!,
                            style: TextStyle(
                              fontSize: 11,
                              fontWeight: FontWeight.bold,
                              color: isSel ? Colors.white : OctaTheme.textPrimary,
                            ),
                          ),
                        ),
                      ),
                    );
                  }).toList(),
                ),
                const SizedBox(height: 16),

                // Common Objections Checkboxes
                const Text('Buyer Objections & Feedback', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: OctaTheme.textPrimary)),
                const SizedBox(height: 6),
                ..._commonObjections.map((obj) {
                  final isChecked = _selectedObjections.contains(obj);
                  return CheckboxListTile(
                    dense: true,
                    contentPadding: EdgeInsets.zero,
                    title: Text(obj, style: const TextStyle(fontSize: 11, color: OctaTheme.textPrimary)),
                    value: isChecked,
                    activeColor: OctaTheme.accent,
                    onChanged: (val) {
                      setState(() {
                        if (val == true) {
                          _selectedObjections.add(obj);
                        } else {
                          _selectedObjections.remove(obj);
                        }
                      });
                    },
                  );
                }).toList(),
                const SizedBox(height: 12),

                // Tour Notes
                const Text('Tour Notes & Specific Feedback', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: OctaTheme.textPrimary)),
                const SizedBox(height: 6),
                TextField(
                  controller: _feedbackCtrl,
                  maxLines: 2,
                  decoration: InputDecoration(
                    hintText: 'e.g. Liked 3BHK tower A, wants higher floor unit reservation',
                    hintStyle: const TextStyle(fontSize: 11, color: OctaTheme.textMuted),
                    filled: true,
                    fillColor: OctaTheme.background,
                    contentPadding: const EdgeInsets.all(10),
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: const BorderSide(color: OctaTheme.border)),
                  ),
                  style: const TextStyle(fontSize: 12, color: OctaTheme.textPrimary),
                ),
                const SizedBox(height: 14),

                // Agreed Next Step
                const Text('Agreed Next Step', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: OctaTheme.textPrimary)),
                const SizedBox(height: 6),
                TextField(
                  controller: _nextStepCtrl,
                  decoration: InputDecoration(
                    filled: true,
                    fillColor: OctaTheme.background,
                    contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: const BorderSide(color: OctaTheme.border)),
                  ),
                  style: const TextStyle(fontSize: 12, color: OctaTheme.textPrimary),
                ),
                const SizedBox(height: 20),

                // Complete Showing Button
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton(
                    style: ElevatedButton.styleFrom(backgroundColor: OctaTheme.success),
                    onPressed: _submitting ? null : _handleCompleteShowing,
                    child: _submitting
                        ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.black))
                        : const Text('Complete Visit & Record Outcome', style: TextStyle(color: Colors.black)),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
