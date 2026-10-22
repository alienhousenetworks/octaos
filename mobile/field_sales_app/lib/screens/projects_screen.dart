import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:field_sales_app/constants/theme.dart';
import 'package:field_sales_app/models/project.dart';
import 'package:field_sales_app/providers/field_sales_provider.dart';
import 'package:field_sales_app/screens/project_units_screen.dart';

class ProjectsScreen extends StatefulWidget {
  const ProjectsScreen({Key? key}) : super(key: key);

  @override
  State<ProjectsScreen> createState() => _ProjectsScreenState();
}

class _ProjectsScreenState extends State<ProjectsScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<FieldSalesProvider>().loadProjects();
    });
  }

  Future<void> _openDirections(double lat, double lng, String name) async {
    final uri = Uri.parse('https://www.google.com/maps/dir/?api=1&destination=$lat,$lng');
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
            const Text('My Projects & Inventory', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            Text(
              '${field.projects.length} Assigned Development Projects',
              style: const TextStyle(fontSize: 11, color: OctaTheme.textSecondary, fontWeight: FontWeight.normal),
            ),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_rounded, size: 20),
            onPressed: () => field.loadProjects(),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () => field.loadProjects(),
        color: OctaTheme.primary,
        backgroundColor: OctaTheme.surface,
        child: field.projectsLoading && field.projects.isEmpty
            ? const Center(child: CircularProgressIndicator(color: OctaTheme.primary))
            : field.projects.isEmpty
                ? Center(
                    child: Padding(
                      padding: const EdgeInsets.all(24.0),
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(Icons.apartment_rounded, size: 48, color: OctaTheme.textMuted.withOpacity(0.5)),
                          const SizedBox(height: 12),
                          const Text(
                            'No Assigned Projects Found',
                            style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold, color: OctaTheme.textPrimary),
                          ),
                          const SizedBox(height: 6),
                          const Text(
                            'Ask your sales administrator or manager to assign you to active development projects.',
                            textAlign: TextAlign.center,
                            style: TextStyle(fontSize: 12, color: OctaTheme.textSecondary),
                          ),
                        ],
                      ),
                    ),
                  )
                : ListView.separated(
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
                    itemCount: field.projects.length,
                    separatorBuilder: (_, __) => const SizedBox(height: 14),
                    itemBuilder: (context, idx) {
                      final p = field.projects[idx];
                      return _buildProjectCard(p);
                    },
                  ),
      ),
    );
  }

  Widget _buildProjectCard(RealEstateProjectModel p) {
    final bool isLead = p.assignedRole == 'primary_lead';

    return Container(
      decoration: BoxDecoration(
        color: OctaTheme.surface,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: isLead ? OctaTheme.primary.withOpacity(0.4) : OctaTheme.border,
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.2),
            blurRadius: 8,
            offset: const Offset(0, 3),
          ),
        ],
      ),
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header: Name & Role Badge
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      p.name,
                      style: const TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                        color: OctaTheme.textPrimary,
                      ),
                    ),
                    if (p.location != null)
                      Padding(
                        padding: const EdgeInsets.only(top: 2),
                        child: Row(
                          children: [
                            const Icon(Icons.location_on_rounded, size: 12, color: OctaTheme.textMuted),
                            const SizedBox(width: 3),
                            Expanded(
                              child: Text(
                                '${p.location}${p.city != null ? ', ${p.city}' : ''}',
                                style: const TextStyle(fontSize: 11, color: OctaTheme.textSecondary),
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                              ),
                            ),
                          ],
                        ),
                      ),
                  ],
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: isLead ? OctaTheme.primary.withOpacity(0.15) : OctaTheme.surfaceElevated,
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(
                    color: isLead ? OctaTheme.primary.withOpacity(0.3) : OctaTheme.border,
                  ),
                ),
                child: Text(
                  p.assignedRole.replaceAll('_', ' ').toUpperCase(),
                  style: TextStyle(
                    fontSize: 10,
                    fontWeight: FontWeight.bold,
                    color: isLead ? OctaTheme.primary : OctaTheme.textSecondary,
                    letterSpacing: 0.5,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),

          // Inventory Unit Stats Bar
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
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
                    const Text('Available Units', style: TextStyle(fontSize: 10, color: OctaTheme.textMuted)),
                    Text(
                      '${p.availableUnits} / ${p.totalUnits}',
                      style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: OctaTheme.success),
                    ),
                  ],
                ),
                if (p.reraNumber != null && p.reraNumber!.isNotEmpty)
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.end,
                    children: [
                      const Text('RERA ID', style: TextStyle(fontSize: 10, color: OctaTheme.textMuted)),
                      Text(
                        p.reraNumber!,
                        style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: OctaTheme.textPrimary),
                      ),
                    ],
                  ),
              ],
            ),
          ),
          const SizedBox(height: 12),

          // Amenities Tags
          if (p.amenities.isNotEmpty) ...[
            Wrap(
              spacing: 6,
              runSpacing: 4,
              children: p.amenities.take(4).map((a) {
                return Container(
                  padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
                  decoration: BoxDecoration(
                    color: OctaTheme.surfaceElevated,
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Text(
                    a,
                    style: const TextStyle(fontSize: 10, color: OctaTheme.textSecondary),
                  ),
                );
              }).toList(),
            ),
            const SizedBox(height: 14),
          ],

          // Action Buttons: Directions & View Inventory
          Row(
            children: [
              Expanded(
                child: OutlinedButton.icon(
                  icon: const Icon(Icons.directions_rounded, size: 14),
                  label: const Text('Directions', style: TextStyle(fontSize: 12)),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: OctaTheme.primary,
                    side: BorderSide(color: OctaTheme.primary.withOpacity(0.4)),
                    padding: const EdgeInsets.symmetric(vertical: 9),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                  ),
                  onPressed: () => _openDirections(p.latitude, p.longitude, p.name),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                flex: 2,
                child: ElevatedButton.icon(
                  icon: const Icon(Icons.grid_view_rounded, size: 14),
                  label: const Text('View Inventory Units', style: TextStyle(fontSize: 12)),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: OctaTheme.primary,
                    foregroundColor: Colors.black,
                    padding: const EdgeInsets.symmetric(vertical: 9),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                  ),
                  onPressed: () {
                    Navigator.of(context).push(
                      MaterialPageRoute(
                        builder: (_) => ProjectUnitsScreen(project: p),
                      ),
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
