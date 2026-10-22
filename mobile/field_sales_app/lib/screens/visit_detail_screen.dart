import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:intl/intl.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:field_sales_app/constants/theme.dart';
import 'package:field_sales_app/models/visit.dart';
import 'package:field_sales_app/providers/field_sales_provider.dart';
import 'package:field_sales_app/screens/check_in_screen.dart';

class VisitDetailScreen extends StatefulWidget {
  final FieldVisit visit;

  const VisitDetailScreen({Key? key, required this.visit}) : super(key: key);

  @override
  State<VisitDetailScreen> createState() => _VisitDetailScreenState();
}

class _VisitDetailScreenState extends State<VisitDetailScreen> {
  void _showReportDelayDialog() {
    int selectedMinutes = 20;
    final reasonCtrl = TextEditingController(text: 'Showing running over scheduled time with buyer.');

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          backgroundColor: OctaTheme.surface,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
          title: const Text('Report Showing Delay', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: OctaTheme.textPrimary)),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'OctaOS AI will evaluate cascade delays on remaining visits today and formulate a recovery plan.',
                style: TextStyle(fontSize: 12, color: OctaTheme.textSecondary),
              ),
              const SizedBox(height: 16),
              const Text('Estimated Delay', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: OctaTheme.textPrimary)),
              const SizedBox(height: 8),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [15, 20, 30, 45].map((mins) {
                  final isSelected = selectedMinutes == mins;
                  return GestureDetector(
                    onTap: () => setDialogState(() => selectedMinutes = mins),
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                      decoration: BoxDecoration(
                        color: isSelected ? OctaTheme.warning : OctaTheme.surfaceElevated,
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Text(
                        '+$mins m',
                        style: TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.bold,
                          color: isSelected ? Colors.black : OctaTheme.textPrimary,
                        ),
                      ),
                    ),
                  );
                }).toList(),
              ),
              const SizedBox(height: 14),
              const Text('Reason', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: OctaTheme.textPrimary)),
              const SizedBox(height: 6),
              TextField(
                controller: reasonCtrl,
                maxLines: 2,
                decoration: InputDecoration(
                  filled: true,
                  fillColor: OctaTheme.background,
                  contentPadding: const EdgeInsets.all(10),
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: const BorderSide(color: OctaTheme.border)),
                ),
                style: const TextStyle(fontSize: 12, color: OctaTheme.textPrimary),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(ctx).pop(),
              child: const Text('Cancel', style: TextStyle(color: OctaTheme.textSecondary)),
            ),
            ElevatedButton(
              style: ElevatedButton.styleFrom(backgroundColor: OctaTheme.warning),
              onPressed: () async {
                Navigator.of(ctx).pop();
                final success = await context.read<FieldSalesProvider>().reportDelay(
                  visitId: widget.visit.id,
                  delayMinutes: selectedMinutes,
                  delayReason: reasonCtrl.text,
                );
                if (success && mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('Delay reported. AI recovery proposal generated.')),
                  );
                }
              },
              child: const Text('Submit & Trigger Recovery', style: TextStyle(color: Colors.black)),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final v = widget.visit;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Visit & Buyer Details'),
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // Project Card
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
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      v.projectName,
                      style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: OctaTheme.textPrimary),
                    ),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(
                        color: OctaTheme.primary.withOpacity(0.12),
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Text(
                        '#${v.sequenceOrder} in Route',
                        style: const TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: OctaTheme.primary),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 4),
                Text(v.projectAddress, style: const TextStyle(fontSize: 12, color: OctaTheme.textSecondary)),
                if (v.unitNumber != null) ...[
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                        decoration: BoxDecoration(
                          color: OctaTheme.surfaceElevated,
                          borderRadius: BorderRadius.circular(6),
                        ),
                        child: Text(
                          'Unit: ${v.unitNumber} (${v.unitType ?? "Configuration"})',
                          style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: OctaTheme.textPrimary),
                        ),
                      ),
                    ],
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(height: 16),

          // Buyer Profile Card
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
                const Text('PROSPECTIVE BUYER', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: OctaTheme.accent, letterSpacing: 0.8)),
                const SizedBox(height: 10),
                Text(v.buyerName, style: const TextStyle(fontSize: 15, fontWeight: FontWeight.bold, color: OctaTheme.textPrimary)),
                const SizedBox(height: 4),
                Text(v.buyerPhone.isNotEmpty ? v.buyerPhone : 'No Phone on Record', style: const TextStyle(fontSize: 12, color: OctaTheme.textSecondary)),
                if (v.buyerEmail.isNotEmpty)
                  Text(v.buyerEmail, style: const TextStyle(fontSize: 12, color: OctaTheme.textMuted)),
              ],
            ),
          ),
          const SizedBox(height: 16),

          // Showing Details Card
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
                const Text('SHOWING LOGISTICS', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: OctaTheme.textSecondary, letterSpacing: 0.8)),
                const SizedBox(height: 10),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Text('Scheduled Start:', style: TextStyle(fontSize: 12, color: OctaTheme.textSecondary)),
                    Text(DateFormat('hh:mm a, MMM d').format(v.scheduledAt), style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: OctaTheme.textPrimary)),
                  ],
                ),
                const SizedBox(height: 8),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Text('Allocated Duration:', style: TextStyle(fontSize: 12, color: OctaTheme.textSecondary)),
                    Text('${v.durationMinutes} Minutes', style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: OctaTheme.textPrimary)),
                  ],
                ),
                const SizedBox(height: 8),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Text('Estimated Travel:', style: TextStyle(fontSize: 12, color: OctaTheme.textSecondary)),
                    Text('${v.estimatedTravelMinutes} Minutes', style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: OctaTheme.primary)),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),

          // Action Buttons
          Row(
            children: [
              Expanded(
                child: OutlinedButton.icon(
                  icon: const Icon(Icons.more_time_rounded, size: 16, color: OctaTheme.warning),
                  label: const Text('Report Delay', style: TextStyle(color: OctaTheme.warning)),
                  style: OutlinedButton.styleFrom(
                    side: const BorderSide(color: OctaTheme.warning),
                    padding: const EdgeInsets.symmetric(vertical: 12),
                  ),
                  onPressed: _showReportDelayDialog,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: ElevatedButton.icon(
                  icon: const Icon(Icons.pin_drop_rounded, size: 16),
                  label: const Text('Arrive & Check In'),
                  style: ElevatedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(vertical: 12),
                  ),
                  onPressed: () {
                    Navigator.of(context).push(
                      MaterialPageRoute(builder: (_) => CheckInScreen(visit: v)),
                    );
                  },
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
