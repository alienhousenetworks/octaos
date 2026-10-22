import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:field_sales_app/constants/theme.dart';
import 'package:field_sales_app/providers/field_sales_provider.dart';
import 'package:field_sales_app/screens/my_day_screen.dart';
import 'package:field_sales_app/screens/projects_screen.dart';
import 'package:field_sales_app/screens/leads_screen.dart';
import 'package:field_sales_app/screens/profile_screen.dart';

class SalesHomeShell extends StatefulWidget {
  const SalesHomeShell({Key? key}) : super(key: key);

  @override
  State<SalesHomeShell> createState() => _SalesHomeShellState();
}

class _SalesHomeShellState extends State<SalesHomeShell> {
  int _currentIndex = 0;

  final List<Widget> _screens = const [
    MyDayScreen(),
    ProjectsScreen(),
    LeadsScreen(),
    ProfileScreen(),
  ];

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final field = context.read<FieldSalesProvider>();
      field.loadMyDay();
      field.loadProjects();
      field.loadLeads();
      field.loadProfile();
    });
  }

  @override
  Widget build(BuildContext context) {
    final field = context.watch<FieldSalesProvider>();

    return Scaffold(
      body: IndexedStack(
        index: _currentIndex,
        children: _screens,
      ),
      bottomNavigationBar: Container(
        decoration: const BoxDecoration(
          color: OctaTheme.surface,
          border: Border(top: BorderSide(color: OctaTheme.border, width: 1)),
        ),
        child: BottomNavigationBar(
          currentIndex: _currentIndex,
          onTap: (idx) => setState(() => _currentIndex = idx),
          backgroundColor: OctaTheme.surface,
          type: BottomNavigationBarType.fixed,
          selectedItemColor: OctaTheme.primary,
          unselectedItemColor: OctaTheme.textMuted,
          selectedLabelStyle: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold),
          unselectedLabelStyle: const TextStyle(fontSize: 11, fontWeight: FontWeight.normal),
          elevation: 0,
          items: [
            BottomNavigationBarItem(
              icon: Stack(
                clipBehavior: Clip.none,
                children: [
                  const Icon(Icons.calendar_today_rounded, size: 20),
                  if (field.visits.any((v) => v.status == 'scheduled' || v.status == 'delayed'))
                    Positioned(
                      top: -2,
                      right: -3,
                      child: Container(
                        width: 7,
                        height: 7,
                        decoration: const BoxDecoration(
                          color: OctaTheme.warning,
                          shape: BoxShape.circle,
                        ),
                      ),
                    ),
                ],
              ),
              label: 'My Day',
            ),
            const BottomNavigationBarItem(
              icon: Icon(Icons.apartment_rounded, size: 20),
              label: 'Projects',
            ),
            BottomNavigationBarItem(
              icon: Stack(
                clipBehavior: Clip.none,
                children: [
                  const Icon(Icons.people_alt_rounded, size: 20),
                  if (field.leads.isNotEmpty)
                    Positioned(
                      top: -3,
                      right: -7,
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 1),
                        decoration: BoxDecoration(
                          color: OctaTheme.primary,
                          borderRadius: BorderRadius.circular(6),
                        ),
                        child: Text(
                          '${field.leads.length}',
                          style: const TextStyle(fontSize: 8, fontWeight: FontWeight.bold, color: Colors.black),
                        ),
                      ),
                    ),
                ],
              ),
              label: 'Inquiries',
            ),
            BottomNavigationBarItem(
              icon: Stack(
                clipBehavior: Clip.none,
                children: [
                  const Icon(Icons.person_rounded, size: 20),
                  Positioned(
                    top: -1,
                    right: -2,
                    child: Container(
                      width: 6,
                      height: 6,
                      decoration: BoxDecoration(
                        color: field.isShiftActive ? OctaTheme.success : OctaTheme.textMuted,
                        shape: BoxShape.circle,
                      ),
                    ),
                  ),
                ],
              ),
              label: 'Shift Profile',
            ),
          ],
        ),
      ),
    );
  }
}
