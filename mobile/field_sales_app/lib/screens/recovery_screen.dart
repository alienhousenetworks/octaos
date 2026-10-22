import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:intl/intl.dart';
import 'package:field_sales_app/constants/theme.dart';
import 'package:field_sales_app/models/recovery_proposal.dart';
import 'package:field_sales_app/providers/field_sales_provider.dart';

class RecoveryScreen extends StatefulWidget {
  final MobileRecoveryProposal proposal;

  const RecoveryScreen({Key? key, required this.proposal}) : super(key: key);

  @override
  State<RecoveryScreen> createState() => _RecoveryScreenState();
}

class _RecoveryScreenState extends State<RecoveryScreen> {
  bool _applying = false;

  @override
  Widget build(BuildContext context) {
    final field = context.read<FieldSalesProvider>();

    return Scaffold(
      appBar: AppBar(
        title: const Text('AI Schedule Recovery'),
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // Banner Card
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: OctaTheme.warning.withOpacity(0.12),
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: OctaTheme.warning.withOpacity(0.4)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Row(
                  children: [
                    Icon(Icons.auto_fix_high_rounded, color: OctaTheme.warning, size: 20),
                    SizedBox(width: 8),
                    Text(
                      'Autonomous Schedule Optimization',
                      style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: OctaTheme.warning),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Text(
                  widget.proposal.rationale,
                  style: const TextStyle(fontSize: 12, color: OctaTheme.textPrimary, height: 1.4),
                ),
              ],
            ),
          ),
          const SizedBox(height: 20),

          const Text(
            'PROPOSED ROUTE CHANGES',
            style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: OctaTheme.textSecondary, letterSpacing: 0.8),
          ),
          const SizedBox(height: 10),

          // Changes Diff List
          ...widget.proposal.changes.map((change) {
            return Container(
              margin: const EdgeInsets.only(bottom: 12),
              padding: const EdgeInsets.all(14),
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
                      Text(
                        change.action.replaceAll('_', ' ').toUpperCase(),
                        style: const TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: OctaTheme.primary),
                      ),
                      Row(
                        children: [
                          Text(
                            DateFormat('hh:mm a').format(change.originalTime),
                            style: const TextStyle(fontSize: 11, color: OctaTheme.textMuted, decoration: TextDecoration.lineThrough),
                          ),
                          const SizedBox(width: 6),
                          const Icon(Icons.arrow_forward_rounded, size: 12, color: OctaTheme.success),
                          const SizedBox(width: 6),
                          Text(
                            DateFormat('hh:mm a').format(change.proposedTime),
                            style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: OctaTheme.success),
                          ),
                        ],
                      ),
                    ],
                  ),
                  const SizedBox(height: 6),
                  Text(change.rationale, style: const TextStyle(fontSize: 11, color: OctaTheme.textSecondary)),
                  if (change.customerMessageDraft != null) ...[
                    const SizedBox(height: 8),
                    Container(
                      padding: const EdgeInsets.all(8),
                      decoration: BoxDecoration(
                        color: OctaTheme.surfaceElevated,
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Text(
                        '💬 Proposed message to buyer: "${change.customerMessageDraft}"',
                        style: const TextStyle(fontSize: 10, color: OctaTheme.textPrimary, fontStyle: FontStyle.italic),
                      ),
                    ),
                  ],
                ],
              ),
            );
          }).toList(),

          const SizedBox(height: 24),

          // Accept button
          SizedBox(
            height: 46,
            child: ElevatedButton.icon(
              icon: const Icon(Icons.check_circle_outline_rounded, size: 18),
              label: _applying
                  ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.black))
                  : const Text('Accept & Update My Route'),
              onPressed: _applying
                  ? null
                  : () async {
                      setState(() => _applying = true);
                      final success = await field.approveProposal(widget.proposal.id);
                      setState(() => _applying = false);
                      if (success && mounted) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(content: Text('Schedule updated successfully.')),
                        );
                        Navigator.of(context).pop();
                      }
                    },
            ),
          ),
        ],
      ),
    );
  }
}
