import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:field_sales_app/constants/theme.dart';
import 'package:field_sales_app/providers/auth_provider.dart';
import 'package:field_sales_app/providers/field_sales_provider.dart';
import 'package:field_sales_app/screens/offline_sync_screen.dart';
import 'package:field_sales_app/screens/login_screen.dart';

class ProfileScreen extends StatefulWidget {
  const ProfileScreen({Key? key}) : super(key: key);

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<FieldSalesProvider>().loadProfile();
    });
  }

  @override
  Widget build(BuildContext context) {
    final field = context.watch<FieldSalesProvider>();
    final auth = context.read<AuthProvider>();
    final profile = field.profile;

    final name = profile?.name ?? 'Showing Specialist';
    final email = profile?.email ?? auth.userId ?? '';
    final role = profile?.role.replaceAll('_', ' ').toUpperCase() ?? 'SALES SPECIALIST';
    final completed = profile?.completedVisitsToday ?? 0;
    final maxVisits = profile?.maxVisitsPerDay ?? 6;
    final capacityPercent = (completed / max(1, maxVisits)).clamp(0.0, 1.0);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Agent Profile & Shift', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
        actions: [
          IconButton(
            icon: const Icon(Icons.cloud_sync_rounded, size: 22),
            onPressed: () {
              Navigator.of(context).push(
                MaterialPageRoute(builder: (_) => const OfflineSyncScreen()),
              );
            },
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () => field.loadProfile(),
        color: OctaTheme.primary,
        backgroundColor: OctaTheme.surface,
        child: ListView(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 20),
          children: [
            // User Hero Card
            Container(
              decoration: BoxDecoration(
                color: OctaTheme.surface,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: OctaTheme.border),
              ),
              padding: const EdgeInsets.all(20),
              child: Column(
                children: [
                  Container(
                    width: 64,
                    height: 64,
                    decoration: BoxDecoration(
                      color: OctaTheme.primary.withOpacity(0.15),
                      shape: BoxShape.circle,
                      border: Border.all(color: OctaTheme.primary.withOpacity(0.4)),
                    ),
                    alignment: Alignment.center,
                    child: Text(
                      name.isNotEmpty ? name[0].toUpperCase() : 'S',
                      style: const TextStyle(fontSize: 26, fontWeight: FontWeight.bold, color: OctaTheme.primary),
                    ),
                  ),
                  const SizedBox(height: 12),
                  Text(
                    name,
                    style: const TextStyle(fontSize: 17, fontWeight: FontWeight.bold, color: OctaTheme.textPrimary),
                  ),
                  const SizedBox(height: 3),
                  Text(
                    email,
                    style: const TextStyle(fontSize: 12, color: OctaTheme.textSecondary),
                  ),
                  const SizedBox(height: 8),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 3),
                    decoration: BoxDecoration(
                      color: OctaTheme.surfaceElevated,
                      borderRadius: BorderRadius.circular(6),
                      border: Border.all(color: OctaTheme.border),
                    ),
                    child: Text(
                      role,
                      style: const TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: OctaTheme.primary),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),

            // Shift Status & Toggle
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
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
                            field.isShiftActive ? 'On Duty (Shift Active)' : 'Shift Inactive (Off Duty)',
                            style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: OctaTheme.textPrimary),
                          ),
                          Text(
                            field.isShiftActive ? 'Autonomous dispatch can assign showings' : 'Excluded from auto-dispatch routing',
                            style: const TextStyle(fontSize: 11, color: OctaTheme.textSecondary),
                          ),
                        ],
                      ),
                    ],
                  ),
                  Switch(
                    value: field.isShiftActive,
                    activeColor: OctaTheme.success,
                    onChanged: (val) async {
                      await field.toggleShift(val);
                      await field.loadProfile();
                    },
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),

            // Daily Showing Capacity Progress
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: OctaTheme.surface,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: OctaTheme.border),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text('Daily Showing Capacity', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: OctaTheme.textPrimary)),
                      Text(
                        '$completed / $maxVisits Showings',
                        style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: OctaTheme.primary),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  ClipRRect(
                    borderRadius: BorderRadius.circular(4),
                    child: LinearProgressIndicator(
                      value: capacityPercent,
                      backgroundColor: OctaTheme.surfaceElevated,
                      valueColor: const AlwaysStoppedAnimation<Color>(OctaTheme.primary),
                      minHeight: 6,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    maxVisits - completed > 0
                        ? '${maxVisits - completed} capacity slots remaining before daily quota limit.'
                        : 'Daily showing capacity reached. Autonomous dispatch will hold new requests.',
                    style: const TextStyle(fontSize: 11, color: OctaTheme.textSecondary),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),

            // Operational Parameters
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: OctaTheme.surface,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: OctaTheme.border),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('OPERATIONAL TELEMETRY', style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: OctaTheme.textMuted, letterSpacing: 0.8)),
                  const SizedBox(height: 12),
                  _buildParamRow(
                    'Working Hours',
                    '${profile?.workingHoursStart ?? '09:00'} - ${profile?.workingHoursEnd ?? '18:00'}',
                    Icons.access_time_rounded,
                  ),
                  const Divider(color: OctaTheme.border, height: 16),
                  _buildParamRow(
                    'Assigned Projects',
                    '${profile?.assignedProjectsCount ?? field.projects.length} Development Sites',
                    Icons.apartment_rounded,
                  ),
                  const Divider(color: OctaTheme.border, height: 16),
                  _buildParamRow(
                    'GPS Telemetry',
                    (profile != null && profile.lastLatitude != null && profile.lastLongitude != null)
                        ? '${profile.lastLatitude!.toStringAsFixed(4)}, ${profile.lastLongitude!.toStringAsFixed(4)}'
                        : 'GPS Location Active',
                    Icons.gps_fixed_rounded,
                  ),
                ],
              ),
            ),
            const SizedBox(height: 24),

            // Logout Action
            OutlinedButton.icon(
              icon: const Icon(Icons.logout_rounded, size: 16),
              label: const Text('Sign Out of OctaOS Field', style: TextStyle(fontWeight: FontWeight.bold)),
              style: OutlinedButton.styleFrom(
                foregroundColor: OctaTheme.danger,
                side: BorderSide(color: OctaTheme.danger.withOpacity(0.4)),
                padding: const EdgeInsets.symmetric(vertical: 14),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
              ),
              onPressed: () async {
                await auth.logout();
                if (mounted) {
                  Navigator.of(context).pushAndRemoveUntil(
                    MaterialPageRoute(builder: (_) => const LoginScreen()),
                    (route) => false,
                  );
                }
              },
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildParamRow(String label, String value, IconData icon) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Row(
          children: [
            Icon(icon, size: 16, color: OctaTheme.textSecondary),
            const SizedBox(width: 8),
            Text(label, style: const TextStyle(fontSize: 12, color: OctaTheme.textSecondary)),
          ],
        ),
        Text(value, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: OctaTheme.textPrimary)),
      ],
    );
  }

  int max(int a, int b) => a > b ? a : b;
}
