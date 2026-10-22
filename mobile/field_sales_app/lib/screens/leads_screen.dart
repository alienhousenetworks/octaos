import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:intl/intl.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:field_sales_app/constants/theme.dart';
import 'package:field_sales_app/models/lead_item.dart';
import 'package:field_sales_app/providers/field_sales_provider.dart';

class LeadsScreen extends StatefulWidget {
  const LeadsScreen({Key? key}) : super(key: key);

  @override
  State<LeadsScreen> createState() => _LeadsScreenState();
}

class _LeadsScreenState extends State<LeadsScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<FieldSalesProvider>().loadLeads();
    });
  }

  Future<void> _makeCall(String phone) async {
    if (phone.isEmpty) return;
    final clean = phone.replaceAll(RegExp(r'[^0-9+]'), '');
    final uri = Uri.parse('tel:$clean');
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri);
    }
  }

  Future<void> _openWhatsApp(String phone, String name, String project) async {
    if (phone.isEmpty) return;
    final clean = phone.replaceAll(RegExp(r'[^0-9]'), '');
    final msg = Uri.encodeComponent(
      'Hello $name, this is your property advisor regarding your showing inquiry for $project. When would you prefer to visit the site?',
    );
    final uri = Uri.parse('https://wa.me/$clean?text=$msg');
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    }
  }

  @override
  Widget build(BuildContext context) {
    final field = context.watch<FieldSalesProvider>();

    return Scaffold(
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Priority Inquiries', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            Text(
              '${field.leads.length} Showing Inquiries & Assigned Leads',
              style: const TextStyle(fontSize: 11, color: OctaTheme.textSecondary, fontWeight: FontWeight.normal),
            ),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_rounded, size: 20),
            onPressed: () => field.loadLeads(),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () => field.loadLeads(),
        color: OctaTheme.primary,
        backgroundColor: OctaTheme.surface,
        child: field.leadsLoading && field.leads.isEmpty
            ? const Center(child: CircularProgressIndicator(color: OctaTheme.primary))
            : field.leads.isEmpty
                ? Center(
                    child: Padding(
                      padding: const EdgeInsets.all(24),
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(Icons.people_outline_rounded, size: 48, color: OctaTheme.textMuted.withOpacity(0.5)),
                          const SizedBox(height: 12),
                          const Text(
                            'No Assigned Inquiries Yet',
                            style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold, color: OctaTheme.textPrimary),
                          ),
                          const SizedBox(height: 6),
                          const Text(
                            'When buyers request showings on your assigned projects, the autonomous dispatch engine assigns them here.',
                            textAlign: TextAlign.center,
                            style: TextStyle(fontSize: 12, color: OctaTheme.textSecondary),
                          ),
                        ],
                      ),
                    ),
                  )
                : ListView.separated(
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
                    itemCount: field.leads.length,
                    separatorBuilder: (_, __) => const SizedBox(height: 12),
                    itemBuilder: (context, idx) {
                      final lead = field.leads[idx];
                      return _buildLeadCard(lead);
                    },
                  ),
      ),
    );
  }

  Widget _buildLeadCard(SalesLeadModel l) {
    return Container(
      decoration: BoxDecoration(
        color: OctaTheme.surface,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: l.hasVisitScheduled ? OctaTheme.success.withOpacity(0.35) : OctaTheme.border,
        ),
      ),
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Buyer Name & Intent Score
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      l.name,
                      style: const TextStyle(fontSize: 15, fontWeight: FontWeight.bold, color: OctaTheme.textPrimary),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      l.projectName,
                      style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: OctaTheme.primary),
                    ),
                  ],
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: OctaTheme.primary.withOpacity(0.12),
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(color: OctaTheme.primary.withOpacity(0.3)),
                ),
                child: Text(
                  'Score ${l.score}',
                  style: const TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: OctaTheme.primary),
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),

          // Showing Status Banner
          if (l.hasVisitScheduled && l.visitScheduledAt != null)
            Container(
              margin: const EdgeInsets.only(bottom: 10),
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
              decoration: BoxDecoration(
                color: OctaTheme.success.withOpacity(0.12),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: OctaTheme.success.withOpacity(0.3)),
              ),
              child: Row(
                children: [
                  const Icon(Icons.calendar_today_rounded, size: 12, color: OctaTheme.success),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Text(
                      'Showing Scheduled: ${DateFormat('EEE, MMM d · hh:mm a').format(l.visitScheduledAt!)}',
                      style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: OctaTheme.success),
                    ),
                  ),
                ],
              ),
            ),

          // Preference Grid
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: OctaTheme.background,
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: OctaTheme.border),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('Unit Need', style: TextStyle(fontSize: 10, color: OctaTheme.textMuted)),
                    Text(l.unitPreference, style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: OctaTheme.textPrimary)),
                  ],
                ),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.center,
                  children: [
                    const Text('Budget', style: TextStyle(fontSize: 10, color: OctaTheme.textMuted)),
                    Text(l.budget, style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: OctaTheme.textPrimary)),
                  ],
                ),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    const Text('Timeline', style: TextStyle(fontSize: 10, color: OctaTheme.textMuted)),
                    Text(l.purchaseTimeline, style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: OctaTheme.textPrimary)),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 10),

          // Why / Rationale
          Text(
            '"${l.why}"',
            style: const TextStyle(fontSize: 11, fontStyle: FontStyle.italic, color: OctaTheme.textSecondary),
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
          ),
          const SizedBox(height: 12),

          // Contact Actions
          Row(
            children: [
              if (l.phone.isNotEmpty) ...[
                Expanded(
                  child: OutlinedButton.icon(
                    icon: const Icon(Icons.call_rounded, size: 14),
                    label: const Text('Call', style: TextStyle(fontSize: 12)),
                    style: OutlinedButton.styleFrom(
                      foregroundColor: OctaTheme.primary,
                      side: BorderSide(color: OctaTheme.primary.withOpacity(0.4)),
                      padding: const EdgeInsets.symmetric(vertical: 8),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                    ),
                    onPressed: () => _makeCall(l.phone),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: OutlinedButton.icon(
                    icon: const Icon(Icons.chat_bubble_outline_rounded, size: 14),
                    label: const Text('WhatsApp', style: TextStyle(fontSize: 12)),
                    style: OutlinedButton.styleFrom(
                      foregroundColor: OctaTheme.success,
                      side: BorderSide(color: OctaTheme.success.withOpacity(0.4)),
                      padding: const EdgeInsets.symmetric(vertical: 8),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                    ),
                    onPressed: () => _openWhatsApp(l.phone, l.name, l.projectName),
                  ),
                ),
              ] else ...[
                const Expanded(
                  child: Text('No buyer contact phone available', style: TextStyle(fontSize: 11, color: OctaTheme.textMuted)),
                ),
              ],
            ],
          ),
        ],
      ),
    );
  }
}
