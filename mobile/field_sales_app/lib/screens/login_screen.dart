import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:field_sales_app/constants/theme.dart';
import 'package:field_sales_app/constants/api_endpoints.dart';
import 'package:field_sales_app/providers/auth_provider.dart';
import 'package:field_sales_app/screens/sales_home_shell.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({Key? key}) : super(key: key);

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _emailCtrl = TextEditingController(text: 'salesperson@octaos.com');
  final _passwordCtrl = TextEditingController(text: 'password123');
  final _tenantCtrl = TextEditingController(text: 'default');
  final _serverCtrl = TextEditingController(text: ApiEndpoints.defaultBaseUrl);
  bool _showServerConfig = false;

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();

    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 32),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                // OctaOS Field Logo / Header
                Center(
                  child: Container(
                    width: 64,
                    height: 64,
                    decoration: BoxDecoration(
                      color: OctaTheme.primary.withOpacity(0.12),
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(color: OctaTheme.primary.withOpacity(0.3)),
                    ),
                    child: const Icon(
                      Icons.navigation_rounded,
                      size: 32,
                      color: OctaTheme.primary,
                    ),
                  ),
                ),
                const SizedBox(height: 20),
                const Text(
                  'OctaOS Field Sales',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontSize: 22,
                    fontWeight: FontWeight.bold,
                    color: OctaTheme.textPrimary,
                    letterSpacing: -0.5,
                  ),
                ),
                const SizedBox(height: 6),
                const Text(
                  'Smart Visit Scheduling & GPS Dispatch',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontSize: 13,
                    color: OctaTheme.textSecondary,
                  ),
                ),
                const SizedBox(height: 36),

                // Error Message Display
                if (auth.errorMessage != null)
                  Container(
                    margin: const EdgeInsets.only(bottom: 20),
                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                    decoration: BoxDecoration(
                      color: OctaTheme.danger.withOpacity(0.12),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: OctaTheme.danger.withOpacity(0.35)),
                    ),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Padding(
                          padding: EdgeInsets.only(top: 1),
                          child: Icon(Icons.error_outline_rounded, size: 16, color: OctaTheme.danger),
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Text(
                            auth.errorMessage!,
                            style: const TextStyle(color: OctaTheme.danger, fontSize: 12, height: 1.35),
                          ),
                        ),
                      ],
                    ),
                  ),

                // Tenant ID
                const Text('Tenant Organization', style: TextStyle(fontSize: 12, color: OctaTheme.textSecondary)),
                const SizedBox(height: 6),
                TextField(
                  controller: _tenantCtrl,
                  decoration: InputDecoration(
                    prefixIcon: const Icon(Icons.business_rounded, size: 18, color: OctaTheme.textMuted),
                    filled: true,
                    fillColor: OctaTheme.surface,
                    contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: const BorderSide(color: OctaTheme.border)),
                    enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: const BorderSide(color: OctaTheme.border)),
                  ),
                  style: const TextStyle(fontSize: 13, color: OctaTheme.textPrimary),
                ),
                const SizedBox(height: 16),

                // Email
                const Text('Work Email', style: TextStyle(fontSize: 12, color: OctaTheme.textSecondary)),
                const SizedBox(height: 6),
                TextField(
                  controller: _emailCtrl,
                  keyboardType: TextInputType.emailAddress,
                  decoration: InputDecoration(
                    prefixIcon: const Icon(Icons.email_outlined, size: 18, color: OctaTheme.textMuted),
                    filled: true,
                    fillColor: OctaTheme.surface,
                    contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: const BorderSide(color: OctaTheme.border)),
                    enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: const BorderSide(color: OctaTheme.border)),
                  ),
                  style: const TextStyle(fontSize: 13, color: OctaTheme.textPrimary),
                ),
                const SizedBox(height: 16),

                // Password
                const Text('Password', style: TextStyle(fontSize: 12, color: OctaTheme.textSecondary)),
                const SizedBox(height: 6),
                TextField(
                  controller: _passwordCtrl,
                  obscureText: true,
                  decoration: InputDecoration(
                    prefixIcon: const Icon(Icons.lock_outline_rounded, size: 18, color: OctaTheme.textMuted),
                    filled: true,
                    fillColor: OctaTheme.surface,
                    contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: const BorderSide(color: OctaTheme.border)),
                    enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: const BorderSide(color: OctaTheme.border)),
                  ),
                  style: const TextStyle(fontSize: 13, color: OctaTheme.textPrimary),
                ),
                const SizedBox(height: 12),

                // Server Config Toggle
                GestureDetector(
                  onTap: () => setState(() => _showServerConfig = !_showServerConfig),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.end,
                    children: [
                      Text(
                        _showServerConfig ? 'Hide Server URL' : 'Configure Server URL',
                        style: const TextStyle(fontSize: 11, color: OctaTheme.primary, fontWeight: FontWeight.w500),
                      ),
                    ],
                  ),
                ),

                if (_showServerConfig) ...[
                  const SizedBox(height: 12),
                  const Text('API Endpoint', style: TextStyle(fontSize: 12, color: OctaTheme.textSecondary)),
                  const SizedBox(height: 6),
                  TextField(
                    controller: _serverCtrl,
                    decoration: InputDecoration(
                      prefixIcon: const Icon(Icons.dns_rounded, size: 18, color: OctaTheme.textMuted),
                      filled: true,
                      fillColor: OctaTheme.surface,
                      contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: const BorderSide(color: OctaTheme.border)),
                      enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: const BorderSide(color: OctaTheme.border)),
                    ),
                    style: const TextStyle(fontSize: 12, color: OctaTheme.textPrimary),
                  ),
                ],

                const SizedBox(height: 28),

                // Sign In Button
                SizedBox(
                  height: 46,
                  child: ElevatedButton(
                    onPressed: auth.isLoading
                        ? null
                        : () async {
                            final success = await auth.login(
                              email: _emailCtrl.text,
                              password: _passwordCtrl.text,
                              tenantId: _tenantCtrl.text,
                              customBaseUrl: _serverCtrl.text,
                            );
                            if (success && mounted) {
                              Navigator.of(context).pushReplacement(
                                MaterialPageRoute(builder: (_) => const SalesHomeShell()),
                              );
                            }
                          },
                    child: auth.isLoading
                        ? const SizedBox(
                            width: 20,
                            height: 20,
                            child: CircularProgressIndicator(strokeWidth: 2, color: OctaTheme.background),
                          )
                        : const Text('Sign In to Field Sales'),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
