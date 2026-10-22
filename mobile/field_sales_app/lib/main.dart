import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:field_sales_app/constants/theme.dart';
import 'package:field_sales_app/services/storage_service.dart';
import 'package:field_sales_app/services/api_service.dart';
import 'package:field_sales_app/services/offline_sync_service.dart';
import 'package:field_sales_app/providers/auth_provider.dart';
import 'package:field_sales_app/providers/field_sales_provider.dart';
import 'package:field_sales_app/screens/login_screen.dart';
import 'package:field_sales_app/screens/my_day_screen.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final storage = await StorageService.init();
  final api = ApiService(storage);
  final offlineSync = OfflineSyncService(storage, api);

  runApp(
    MultiProvider(
      providers: [
        Provider<StorageService>.value(value: storage),
        Provider<ApiService>.value(value: api),
        Provider<OfflineSyncService>.value(value: offlineSync),
        ChangeNotifierProvider(create: (_) => AuthProvider(storage, api)),
        ChangeNotifierProvider(create: (_) => FieldSalesProvider(api, offlineSync)),
      ],
      child: const OctaFieldSalesApp(),
    ),
  );
}

class OctaFieldSalesApp extends StatelessWidget {
  const OctaFieldSalesApp({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();

    return MaterialApp(
      title: 'OctaOS Field Sales',
      debugShowCheckedModeBanner: false,
      theme: OctaTheme.darkTheme,
      home: auth.isAuthenticated ? const MyDayScreen() : const LoginScreen(),
    );
  }
}
