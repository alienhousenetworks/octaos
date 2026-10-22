import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:intl/intl.dart';
import 'package:field_sales_app/constants/theme.dart';
import 'package:field_sales_app/providers/field_sales_provider.dart';

class OfflineSyncScreen extends StatefulWidget {
  const OfflineSyncScreen({Key? key}) : super(key: key);

  @override
  State<OfflineSyncScreen> createState() => _OfflineSyncScreenState();
}

class _OfflineSyncScreenState extends State<OfflineSyncScreen> {
  bool _syncing = false;

  @override
  Widget build(BuildContext context) {
    final field = context.watch<FieldSalesProvider>();
    final pendingCount = field.pendingOfflineCount;
    final events = field.offlineSync.getPendingEvents();

    return Scaffold(
      appBar: AppBar(
        title: const Text('Offline Sync Queue'),
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: OctaTheme.surface,
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: OctaTheme.border),
            ),
            child: Row(
              children: [
                Icon(
                  pendingCount > 0 ? Icons.cloud_queue_rounded : Icons.cloud_done_rounded,
                  color: pendingCount > 0 ? OctaTheme.warning : OctaTheme.success,
                  size: 28,
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        pendingCount > 0 ? '$pendingCount Event(s) Awaiting Sync' : 'All Events Synchronized',
                        style: const TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: OctaTheme.textPrimary),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        pendingCount > 0
                            ? 'Check-ins and outcomes queued locally while cellular signal was weak.'
                            : 'All local records have been verified by the OctaOS backend.',
                        style: const TextStyle(fontSize: 11, color: OctaTheme.textSecondary),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 20),

          if (pendingCount > 0) ...[
            SizedBox(
              height: 44,
              child: ElevatedButton.icon(
                icon: const Icon(Icons.sync_rounded, size: 16),
                label: _syncing
                    ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.black))
                    : const Text('Sync All Events Now'),
                onPressed: _syncing
                    ? null
                    : () async {
                        setState(() => _syncing = true);
                        final count = await field.triggerOfflineSync();
                        setState(() => _syncing = false);
                        if (mounted) {
                          ScaffoldMessenger.of(context).showSnackBar(
                            SnackBar(content: Text('Successfully synchronized $count offline event(s).')),
                          );
                        }
                      },
              ),
            ),
            const SizedBox(height: 24),
          ],

          const Text(
            'QUEUED EVENTS',
            style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: OctaTheme.textSecondary, letterSpacing: 0.8),
          ),
          const SizedBox(height: 10),

          if (events.isEmpty)
            Container(
              padding: const EdgeInsets.symmetric(vertical: 40),
              alignment: Alignment.center,
              child: const Text('Queue is empty.', style: TextStyle(color: OctaTheme.textMuted, fontSize: 13)),
            )
          else
            ...events.map((e) {
              return Container(
                margin: const EdgeInsets.only(bottom: 10),
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: OctaTheme.surface,
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: OctaTheme.border),
                ),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          e.type.toUpperCase(),
                          style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: OctaTheme.primary),
                        ),
                        const SizedBox(height: 2),
                        Text('Visit ID: ${e.visitId.substring(0, e.visitId.length > 8 ? 8 : e.visitId.length)}', style: const TextStyle(fontSize: 11, color: OctaTheme.textSecondary)),
                      ],
                    ),
                    Text(
                      DateFormat('hh:mm a').format(e.createdAt),
                      style: const TextStyle(fontSize: 11, color: OctaTheme.textMuted),
                    ),
                  ],
                ),
              );
            }).toList(),
        ],
      ),
    );
  }
}
