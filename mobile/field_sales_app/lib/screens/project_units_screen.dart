import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:intl/intl.dart';
import 'package:field_sales_app/constants/theme.dart';
import 'package:field_sales_app/models/project.dart';
import 'package:field_sales_app/models/unit.dart';
import 'package:field_sales_app/providers/field_sales_provider.dart';

class ProjectUnitsScreen extends StatefulWidget {
  final RealEstateProjectModel project;

  const ProjectUnitsScreen({Key? key, required this.project}) : super(key: key);

  @override
  State<ProjectUnitsScreen> createState() => _ProjectUnitsScreenState();
}

class _ProjectUnitsScreenState extends State<ProjectUnitsScreen> {
  List<RealEstateUnitModel> _units = [];
  bool _isLoading = true;
  String _selectedType = 'All';
  String _selectedStatus = 'All';

  @override
  void initState() {
    super.initState();
    _loadUnits();
  }

  Future<void> _loadUnits() async {
    setState(() => _isLoading = true);
    final field = context.read<FieldSalesProvider>();
    final list = await field.loadProjectUnits(widget.project.id);
    if (mounted) {
      setState(() {
        _units = list;
        _isLoading = false;
      });
    }
  }

  String _formatPrice(double price) {
    if (price >= 10000000) {
      return '₹${(price / 10000000).toStringAsFixed(2)} Cr';
    } else if (price >= 100000) {
      return '₹${(price / 100000).toStringAsFixed(2)} L';
    } else {
      return '₹${NumberFormat('#,##,###').format(price.toInt())}';
    }
  }

  void _showReserveHoldDialog(RealEstateUnitModel unit) {
    final field = context.read<FieldSalesProvider>();
    final leads = field.leads;
    String selectedLeadId = leads.isNotEmpty ? leads.first.id : '';
    final depositCtrl = TextEditingController(text: '50000');
    final notesCtrl = TextEditingController(text: 'Site visit holding request');
    bool submitting = false;

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: OctaTheme.surface,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
      ),
      builder: (ctx) => StatefulBuilder(
        builder: (context, setModalState) => Padding(
          padding: EdgeInsets.only(
            left: 20,
            right: 20,
            top: 20,
            bottom: MediaQuery.of(ctx).viewInsets.bottom + 20,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Reserve Unit ${unit.unitNumber}',
                        style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: OctaTheme.textPrimary),
                      ),
                      Text(
                        '${unit.unitType} · Floor ${unit.floor ?? 1} · ${_formatPrice(unit.basePrice)}',
                        style: const TextStyle(fontSize: 12, color: OctaTheme.textSecondary),
                      ),
                    ],
                  ),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: OctaTheme.warning.withOpacity(0.15),
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: const Text(
                      '48h Hold Lock',
                      style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: OctaTheme.warning),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 16),

              const Text('Select Interested Buyer / Lead', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: OctaTheme.textPrimary)),
              const SizedBox(height: 6),
              if (leads.isEmpty)
                const Text('No assigned leads found. Defaulting to on-site prospective buyer.', style: TextStyle(fontSize: 11, color: OctaTheme.textMuted))
              else
                DropdownButtonFormField<String>(
                  value: selectedLeadId.isNotEmpty ? selectedLeadId : leads.first.id,
                  dropdownColor: OctaTheme.surfaceElevated,
                  decoration: InputDecoration(
                    filled: true,
                    fillColor: OctaTheme.background,
                    contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: const BorderSide(color: OctaTheme.border)),
                  ),
                  items: leads.map((l) {
                    return DropdownMenuItem(
                      value: l.id,
                      child: Text(
                        '${l.name} (${l.budget})',
                        style: const TextStyle(fontSize: 12, color: OctaTheme.textPrimary),
                      ),
                    );
                  }).toList(),
                  onChanged: (val) {
                    if (val != null) setModalState(() => selectedLeadId = val);
                  },
                ),
              const SizedBox(height: 12),

              const Text('Token Deposit Amount (₹)', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: OctaTheme.textPrimary)),
              const SizedBox(height: 6),
              TextField(
                controller: depositCtrl,
                keyboardType: TextInputType.number,
                decoration: InputDecoration(
                  filled: true,
                  fillColor: OctaTheme.background,
                  contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: const BorderSide(color: OctaTheme.border)),
                ),
                style: const TextStyle(fontSize: 12, color: OctaTheme.textPrimary),
              ),
              const SizedBox(height: 12),

              const Text('Showing Remarks / Notes', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: OctaTheme.textPrimary)),
              const SizedBox(height: 6),
              TextField(
                controller: notesCtrl,
                maxLines: 2,
                decoration: InputDecoration(
                  filled: true,
                  fillColor: OctaTheme.background,
                  contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: const BorderSide(color: OctaTheme.border)),
                ),
                style: const TextStyle(fontSize: 12, color: OctaTheme.textPrimary),
              ),
              const SizedBox(height: 16),

              Row(
                children: [
                  Expanded(
                    child: OutlinedButton(
                      style: OutlinedButton.styleFrom(
                        side: const BorderSide(color: OctaTheme.border),
                        padding: const EdgeInsets.symmetric(vertical: 12),
                      ),
                      onPressed: () => Navigator.of(ctx).pop(),
                      child: const Text('Cancel', style: TextStyle(color: OctaTheme.textSecondary)),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: ElevatedButton(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: OctaTheme.warning,
                        foregroundColor: Colors.black,
                        padding: const EdgeInsets.symmetric(vertical: 12),
                      ),
                      onPressed: submitting
                          ? null
                          : () async {
                              setModalState(() => submitting = true);
                              final dep = double.tryParse(depositCtrl.text) ?? 0.0;
                              final lead = selectedLeadId.isNotEmpty
                                  ? selectedLeadId
                                  : (leads.isNotEmpty ? leads.first.id : 'walk_in_lead');
                              final ok = await field.reserveUnitOnSite(
                                unitId: unit.id,
                                leadId: lead,
                                depositAmount: dep,
                                notes: notesCtrl.text,
                              );
                              if (mounted) {
                                Navigator.of(ctx).pop();
                                if (ok) {
                                  ScaffoldMessenger.of(context).showSnackBar(
                                    SnackBar(
                                      content: Text('Unit ${unit.unitNumber} hold locked for 48 hours.'),
                                      backgroundColor: OctaTheme.success,
                                    ),
                                  );
                                  _loadUnits();
                                } else {
                                  ScaffoldMessenger.of(context).showSnackBar(
                                    SnackBar(
                                      content: Text(field.errorMessage ?? 'Failed to reserve unit hold.'),
                                      backgroundColor: OctaTheme.danger,
                                    ),
                                  );
                                }
                              }
                            },
                      child: submitting
                          ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.black))
                          : const Text('Confirm 48h Hold', style: TextStyle(fontWeight: FontWeight.bold)),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final filteredUnits = _units.filterUnits(_selectedType, _selectedStatus);
    final unitTypes = ['All', ..._units.map((u) => u.unitType).toSet()];

    return Scaffold(
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(widget.project.name, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
            Text(
              '${_units.length} Units Inventory',
              style: const TextStyle(fontSize: 11, color: OctaTheme.textSecondary, fontWeight: FontWeight.normal),
            ),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_rounded, size: 20),
            onPressed: _loadUnits,
          ),
        ],
      ),
      body: Column(
        children: [
          // Filter Chips Scrollable
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
            decoration: const BoxDecoration(
              color: OctaTheme.surface,
              border: Border(bottom: BorderSide(color: OctaTheme.border)),
            ),
            child: SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: unitTypes.map((type) {
                  final isSelected = _selectedType == type;
                  return Padding(
                    padding: const EdgeInsets.only(right: 6),
                    child: ChoiceChip(
                      label: Text(type),
                      selected: isSelected,
                      selectedColor: OctaTheme.primary,
                      backgroundColor: OctaTheme.surfaceElevated,
                      labelStyle: TextStyle(
                        fontSize: 11,
                        fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                        color: isSelected ? Colors.black : OctaTheme.textSecondary,
                      ),
                      onSelected: (val) {
                        setState(() => _selectedType = type);
                      },
                    ),
                  );
                }).toList(),
              ),
            ),
          ),

          // Units List
          Expanded(
            child: _isLoading
                ? const Center(child: CircularProgressIndicator(color: OctaTheme.primary))
                : filteredUnits.isEmpty
                    ? Center(
                        child: Padding(
                          padding: const EdgeInsets.all(24),
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Icon(Icons.inventory_2_outlined, size: 40, color: OctaTheme.textMuted.withOpacity(0.5)),
                              const SizedBox(height: 10),
                              const Text('No Units Found', style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: OctaTheme.textPrimary)),
                              const SizedBox(height: 4),
                              Text(
                                _selectedType == 'All'
                                    ? 'No units have been configured for this project yet.'
                                    : 'No $_selectedType units match current filters.',
                                style: const TextStyle(fontSize: 12, color: OctaTheme.textSecondary),
                              ),
                            ],
                          ),
                        ),
                      )
                    : ListView.separated(
                        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                        itemCount: filteredUnits.length,
                        separatorBuilder: (_, __) => const SizedBox(height: 10),
                        itemBuilder: (context, idx) {
                          final u = filteredUnits[idx];
                          return _buildUnitCard(u);
                        },
                      ),
          ),
        ],
      ),
    );
  }

  Widget _buildUnitCard(RealEstateUnitModel u) {
    Color statusColor;
    String statusLabel;
    if (u.isAvailable) {
      statusColor = OctaTheme.success;
      statusLabel = 'AVAILABLE';
    } else if (u.isHold) {
      statusColor = OctaTheme.warning;
      statusLabel = 'ON HOLD';
    } else {
      statusColor = OctaTheme.primary;
      statusLabel = 'BOOKED';
    }

    return Container(
      decoration: BoxDecoration(
        color: OctaTheme.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: OctaTheme.border),
      ),
      padding: const EdgeInsets.all(14),
      child: Column(
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                children: [
                  Container(
                    width: 36,
                    height: 36,
                    decoration: BoxDecoration(
                      color: OctaTheme.primary.withOpacity(0.12),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: OctaTheme.primary.withOpacity(0.2)),
                    ),
                    alignment: Alignment.center,
                    child: Text(
                      u.unitNumber,
                      style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: OctaTheme.primary),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Text(
                            u.unitType,
                            style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: OctaTheme.textPrimary),
                          ),
                          if (u.floor != null)
                            Text(' · Floor ${u.floor}', style: const TextStyle(fontSize: 11, color: OctaTheme.textSecondary)),
                        ],
                      ),
                      if (u.carpetSqft != null)
                        Text('${u.carpetSqft!.toInt()} sqft carpet', style: const TextStyle(fontSize: 11, color: OctaTheme.textMuted)),
                    ],
                  ),
                ],
              ),
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Text(
                    _formatPrice(u.basePrice),
                    style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: OctaTheme.textPrimary),
                  ),
                  const SizedBox(height: 2),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                    decoration: BoxDecoration(
                      color: statusColor.withOpacity(0.12),
                      borderRadius: BorderRadius.circular(4),
                      border: Border.all(color: statusColor.withOpacity(0.3)),
                    ),
                    child: Text(
                      statusLabel,
                      style: TextStyle(fontSize: 9, fontWeight: FontWeight.bold, color: statusColor),
                    ),
                  ),
                ],
              ),
            ],
          ),
          if (u.isAvailable) ...[
            const SizedBox(height: 10),
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                ElevatedButton.icon(
                  icon: const Icon(Icons.lock_clock_rounded, size: 13),
                  label: const Text('Reserve 48h Hold', style: TextStyle(fontSize: 11)),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: OctaTheme.warning,
                    foregroundColor: Colors.black,
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
                  ),
                  onPressed: () => _showReserveHoldDialog(u),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }
}

extension UnitFilterExt on List<RealEstateUnitModel> {
  List<RealEstateUnitModel> filterUnits(String type, String status) {
    return where((u) {
      if (type != 'All' && u.unitType != type) return false;
      if (status == 'Available' && !u.isAvailable) return false;
      if (status == 'Hold' && !u.isHold) return false;
      if (status == 'Booked' && !u.isBooked) return false;
      return true;
    }).toList();
  }
}
