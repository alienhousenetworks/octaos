import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:intl/intl.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:field_sales_app/constants/theme.dart';
import 'package:field_sales_app/models/visit.dart';
import 'package:field_sales_app/providers/field_sales_provider.dart';
import 'package:field_sales_app/providers/auth_provider.dart';
import 'package:field_sales_app/screens/visit_detail_screen.dart';
import 'package:field_sales_app/screens/check_in_screen.dart';
import 'package:field_sales_app/screens/recovery_screen.dart';
import 'package:field_sales_app/screens/offline_sync_screen.dart';
import 'package:field_sales_app/screens/login_screen.dart';

class MyDayScreen extends StatefulWidget {
  const MyDayScreen({Key? key}) : super(key: key);

  @override
  State<MyDayScreen> createState() => _MyDayScreenState();
}

class _MyDayScreenState extends State<MyDayScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<FieldSalesProvider>().loadMyDay();
    });
  }

  Future<void> _launchNavigation(double lat, double lng, String label) async {
    final googleMapsUrl = Uri.parse('https://www.google.com/maps/dir/?api=1&destination=$lat,$lng');
    if (await canLaunchUrl(googleMapsUrl)) {
      await launchUrl(googleMapsUrl, mode: LaunchMode.externalApplication);
    }
  }

  Future<void> _callCustomer(String phone) async {
    if (phone.isEmpty) return;
    final telUrl = Uri.parse('tel:$phone');
    if (await canLaunchUrl(telUrl)) {
      await launchUrl(telUrl);
    }
  }

  @override
  Widget build(BuildContext context) {
    final field = context.watch<FieldSalesProvider>();
    final auth = context.read<AuthProvider>();

    final nextVisit = field.nextVisit;
    final proposal = field.pendingProposal;

    return Scaffold(
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('My Day', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            Text(
              DateFormat('EEEE, MMM d').format(DateTime.now()),
              style: const TextStyle(fontSize: 11, color: OctaTheme.textSecondary, fontWeight: FontWeight.normal),
            ),
          ],
        ),
        actions: [
          // Offline sync button with badge
          Stack(
            alignment: Alignment.center,
            children: [
              IconButton(
                icon: const Icon(Icons.cloud_sync_rounded, size: 22),
                onPressed: () {
                  Navigator.of(context).push(
                    MaterialPageRoute(builder: (_) => const OfflineSyncScreen()),
                  );
                },
              ),
              if (field.pendingOfflineCount > 0)
                Positioned(
                  top: 8,
                  right: 8,
                  child: Container(
                    padding: const EdgeInsets.all(4),
                    decoration: const BoxDecoration(
                      color: OctaTheme.warning,
                      shape: BoxShape.circle,
                    ),
                    child: Text(
                      '${field.pendingOfflineCount}',
                      style: const TextStyle(fontSize: 9, fontWeight: FontWeight.bold, color: Colors.black),
                    ),
                  ),
                ),
            ],
          ),
          IconButton(
            icon: const Icon(Icons.logout_rounded, size: 20),
            onPressed: () async {
              await auth.logout();
              if (mounted) {
                Navigator.of(context).pushReplacement(
                  MaterialPageRoute(builder: (_) => const LoginScreen()),
                );
              }
            },
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () => field.loadMyDay(),
        color: OctaTheme.primary,
        backgroundColor: OctaTheme.surface,
        child: ListView(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
          children: [
            // Shift Toggle Card
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              decoration: BoxDecoration(
                color: OctaTheme.surface,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: OctaTheme.border),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Row(
                    children: [
                      Container(
                        width: 10,
                        height: 10,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          color: field.isShiftActive ? OctaTheme.success : OctaTheme.textMuted,
                        ),
                      ),
                      const SizedBox(width: 10),
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            field.isShiftActive ? 'On Duty (Shift Active)' : 'Shift Ended',
                            style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: OctaTheme.textPrimary),
                          ),
                          Text(
                            field.isShiftActive ? 'GPS location shared with dispatch' : 'Location tracking paused',
                            style: const TextStyle(fontSize: 11, color: OctaTheme.textSecondary),
                          ),
                        ],
                      ),
                    ],
                  ),
                  Switch(
                    value: field.isShiftActive,
                    activeColor: OctaTheme.success,
                    onChanged: (val) => field.toggleShift(val),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),

            // AI Schedule Recovery Notification Alert
            if (proposal != null) ...[
              GestureDetector(
                onTap: () {
                  Navigator.of(context).push(
                    MaterialPageRoute(builder: (_) => RecoveryScreen(proposal: proposal)),
                  );
                },
                child: Container(
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: OctaTheme.warning.withOpacity(0.12),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: OctaTheme.warning.withOpacity(0.4)),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.auto_fix_high_rounded, color: OctaTheme.warning, size: 22),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text(
                              'AI Schedule Update Available',
                              style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: OctaTheme.warning),
                            ),
                            const SizedBox(height: 2),
                            Text(
                              proposal.rationale,
                              maxLines: 2,
                              overflow: TextOverflow.ellipsis,
                              style: const TextStyle(fontSize: 11, color: OctaTheme.textPrimary),
                            ),
                          ],
                        ),
                      ),
                      const Icon(Icons.chevron_right_rounded, color: OctaTheme.warning),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),
            ],

            // Next Appointment Hero Card
            if (nextVisit != null) ...[
              const Text('NEXT APPOINTMENT', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: OctaTheme.primary, letterSpacing: 0.8)),
              const SizedBox(height: 8),
              Container(
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    colors: [OctaTheme.surfaceElevated, OctaTheme.surface],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: OctaTheme.primary.withOpacity(0.3)),
                ),
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                          decoration: BoxDecoration(
                            color: OctaTheme.primary.withOpacity(0.15),
                            borderRadius: BorderRadius.circular(6),
                          ),
                          child: Row(
                            children: [
                              const Icon(Icons.schedule_rounded, size: 12, color: OctaTheme.primary),
                              const SizedBox(width: 4),
                              Text(
                                DateFormat('hh:mm a').format(nextVisit.scheduledAt),
                                style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: OctaTheme.primary),
                              ),
                            ],
                          ),
                        ),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                          decoration: BoxDecoration(
                            color: OctaTheme.accent.withOpacity(0.15),
                            borderRadius: BorderRadius.circular(6),
                          ),
                          child: Text(
                            '~${nextVisit.estimatedTravelMinutes}m transit',
                            style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: OctaTheme.accent),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),
                    Text(
                      nextVisit.projectName,
                      style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: OctaTheme.textPrimary),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      nextVisit.projectAddress,
                      style: const TextStyle(fontSize: 12, color: OctaTheme.textSecondary),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'Buyer: ${nextVisit.buyerName}',
                      style: const TextStyle(fontSize: 12, color: OctaTheme.textMuted),
                    ),
                    const SizedBox(height: 16),

                    // Hero Action Buttons
                    Row(
                      children: [
                        Expanded(
                          child: OutlinedButton.icon(
                            icon: const Icon(Icons.navigation_rounded, size: 16, color: OctaTheme.primary),
                            label: const Text('Navigate', style: TextStyle(fontSize: 12, color: OctaTheme.primary)),
                            style: OutlinedButton.styleFrom(
                              side: const BorderSide(color: OctaTheme.primary),
                              padding: const EdgeInsets.symmetric(vertical: 10),
                              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                            ),
                            onPressed: () => _launchNavigation(nextVisit.latitude, nextVisit.longitude, nextVisit.projectName),
                          ),
                        ),
                        const SizedBox(width: 8),
                        if (nextVisit.buyerPhone.isNotEmpty)
                          IconButton(
                            icon: const Icon(Icons.phone_rounded, color: OctaTheme.success, size: 20),
                            style: IconButton.styleFrom(
                              backgroundColor: OctaTheme.success.withOpacity(0.12),
                              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                            ),
                            onPressed: () => _callCustomer(nextVisit.buyerPhone),
                          ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: ElevatedButton.icon(
                            icon: const Icon(Icons.pin_drop_rounded, size: 16, color: OctaTheme.background),
                            label: const Text('Check In', style: TextStyle(fontSize: 12)),
                            style: ElevatedButton.styleFrom(
                              backgroundColor: OctaTheme.primary,
                              padding: const EdgeInsets.symmetric(vertical: 10),
                              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                            ),
                            onPressed: () {
                              Navigator.of(context).push(
                                MaterialPageRoute(builder: (_) => CheckInScreen(visit: nextVisit)),
                              );
                            },
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 24),
            ],

            // Today's Route Timeline Header
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text('TODAY\'S ITINERARY', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: OctaTheme.textSecondary, letterSpacing: 0.8)),
                Text('${field.visits.length} showings', style: const TextStyle(fontSize: 11, color: OctaTheme.textMuted)),
              ],
            ),
            const SizedBox(height: 10),

            // Visits List
            if (field.visits.isEmpty)
              Container(
                padding: const EdgeInsets.symmetric(vertical: 36),
                alignment: Alignment.center,
                child: const Text('No site visits assigned for today.', style: TextStyle(fontSize: 13, color: OctaTheme.textMuted)),
              )
            else
              ...field.visits.map((visit) {
                final isDone = visit.status == 'completed';
                final isDelayed = visit.status == 'delayed';

                return Container(
                  margin: const EdgeInsets.only(bottom: 10),
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: OctaTheme.surface,
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: OctaTheme.border),
                  ),
                  child: InkWell(
                    onTap: () {
                      Navigator.of(context).push(
                        MaterialPageRoute(builder: (_) => VisitDetailScreen(visit: visit)),
                      );
                    },
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        // Sequence pill
                        Container(
                          width: 28,
                          height: 28,
                          decoration: BoxDecoration(
                            color: isDone ? OctaTheme.success.withOpacity(0.15) : OctaTheme.primary.withOpacity(0.15),
                            borderRadius: BorderRadius.circular(8),
                          ),
                          alignment: Alignment.center,
                          child: Text(
                            '#${visit.sequenceOrder}',
                            style: TextStyle(
                              fontSize: 11,
                              fontWeight: FontWeight.bold,
                              color: isDone ? OctaTheme.success : OctaTheme.primary,
                            ),
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                visit.projectName,
                                style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: OctaTheme.textPrimary),
                              ),
                              const SizedBox(height: 2),
                              Text(
                                'Buyer: ${visit.buyerName}',
                                style: const TextStyle(fontSize: 11, color: OctaTheme.textSecondary),
                              ),
                              const SizedBox(height: 4),
                              Row(
                                children: [
                                  Icon(Icons.access_time_rounded, size: 12, color: isDelayed ? OctaTheme.warning : OctaTheme.textMuted),
                                  const SizedBox(width: 4),
                                  Text(
                                    DateFormat('hh:mm a').format(visit.scheduledAt),
                                    style: TextStyle(
                                      fontSize: 11,
                                      fontWeight: FontWeight.w600,
                                      color: isDelayed ? OctaTheme.warning : OctaTheme.textPrimary,
                                    ),
                                  ),
                                  const SizedBox(width: 8),
                                  Text(
                                    '(${visit.durationMinutes}m showing)',
                                    style: const TextStyle(fontSize: 10, color: OctaTheme.textMuted),
                                  ),
                                ],
                              ),
                            ],
                          ),
                        ),
                        // Status badge
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                          decoration: BoxDecoration(
                            color: isDone
                                ? OctaTheme.success.withOpacity(0.15)
                                : isDelayed
                                ? OctaTheme.warning.withOpacity(0.15)
                                : OctaTheme.primary.withOpacity(0.15),
                            borderRadius: BorderRadius.circular(6),
                          ),
                          child: Text(
                            visit.status.toUpperCase(),
                            style: TextStyle(
                              fontSize: 9,
                              fontWeight: FontWeight.bold,
                              color: isDone ? OctaTheme.success : isDelayed ? OctaTheme.warning : OctaTheme.primary,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                );
              }).toList(),
          ],
        ),
      ),
    );
  }
}
