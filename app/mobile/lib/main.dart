import 'package:flutter/material.dart';
import 'core/session.dart';
import 'core/theme.dart';
import 'features/auth/landing_screen.dart';
import 'features/home/home_screen.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const SlslApp());
}

class SlslApp extends StatefulWidget {
  const SlslApp({super.key});
  @override
  State<SlslApp> createState() => _SlslAppState();
}

class _SlslAppState extends State<SlslApp> {
  final session = Session();
  @override
  void initState() {
    super.initState();
    session.restore();
  }

  @override
  void dispose() {
    session.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => ListenableBuilder(
    listenable: session,
    builder: (context, _) => MaterialApp(
      title: 'SLSL Connect',
      debugShowCheckedModeBanner: false,
      theme: appTheme,
      home: session.restoring
          ? const Scaffold(body: Center(child: CircularProgressIndicator()))
          : session.user == null
          ? LandingScreen(session: session)
          : HomeScreen(session: session),
    ),
  );
}
