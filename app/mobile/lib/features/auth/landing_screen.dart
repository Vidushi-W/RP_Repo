import 'package:flutter/material.dart';
import '../../core/session.dart';
import '../../core/theme.dart';
import 'auth_screen.dart';

class LandingScreen extends StatelessWidget {
  const LandingScreen({super.key, required this.session});
  final Session session;
  @override
  Widget build(BuildContext context) => Scaffold(
    body: SafeArea(
      child: SingleChildScrollView(
        padding: const EdgeInsets.fromLTRB(26, 24, 26, 20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Brand(),
            const SizedBox(height: 32),
            Container(
              height: 238,
              width: double.infinity,
              decoration: BoxDecoration(
                color: forest,
                borderRadius: BorderRadius.circular(32),
              ),
              clipBehavior: Clip.antiAlias,
              child: Stack(
                children: [
                  Positioned(
                    right: -45,
                    top: -50,
                    child: Container(
                      width: 230,
                      height: 230,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        border: Border.all(
                          color: Colors.white.withValues(alpha: .09),
                          width: 35,
                        ),
                      ),
                    ),
                  ),
                  Positioned(
                    left: 32,
                    top: 24,
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 13,
                        vertical: 7,
                      ),
                      decoration: BoxDecoration(
                        color: Colors.white.withValues(alpha: .1),
                        borderRadius: BorderRadius.circular(20),
                      ),
                      child: const Text(
                        'A little motion. A meaningful connection.',
                        style: TextStyle(fontSize: 10, color: lime),
                      ),
                    ),
                  ),
                  const Positioned(
                    left: 37,
                    top: 78,
                    child: Icon(
                      Icons.sign_language_rounded,
                      size: 92,
                      color: lime,
                    ),
                  ),
                  const Positioned(
                    left: 150,
                    top: 108,
                    child: Icon(
                      Icons.arrow_forward_rounded,
                      size: 24,
                      color: lime,
                    ),
                  ),
                  const Positioned(
                    right: 36,
                    top: 89,
                    child: Icon(
                      Icons.graphic_eq_rounded,
                      size: 66,
                      color: lime,
                    ),
                  ),
                  const Positioned(
                    left: 32,
                    bottom: 26,
                    child: Text(
                      'Sign it. Say it.\nBe part of the conversation.',
                      style: TextStyle(
                        fontSize: 18,
                        height: 1.3,
                        fontWeight: FontWeight.w500,
                        color: Colors.white,
                      ),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 28),
            const Label('MADE FOR EVERYDAY CONNECTIONS'),
            const SizedBox(height: 12),
            Text(
              'Your hands.\nYour voice.',
              style: Theme.of(context).textTheme.headlineLarge,
            ),
            const SizedBox(height: 12),
            const Text(
              'Turn your signs into spoken Sinhala. Connect with the people around you, one conversation at a time.',
              style: TextStyle(fontSize: 15, height: 1.6, color: muted),
            ),
            const SizedBox(height: 22),
            const Row(
              children: [
                Icon(Icons.accessibility_new_rounded, size: 17, color: green),
                SizedBox(width: 7),
                Text(
                  'Simple to use · Designed to include',
                  style: TextStyle(fontSize: 12, color: green),
                ),
              ],
            ),
            const SizedBox(height: 26),
            FilledButton(
              onPressed: () => _open(context, true),
              child: const Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text('Get started'),
                  SizedBox(width: 10),
                  Icon(Icons.arrow_forward_rounded, size: 20),
                ],
              ),
            ),
            const SizedBox(height: 6),
            Center(
              child: TextButton(
                onPressed: () => _open(context, false),
                child: const Text('Already have an account?  Log in'),
              ),
            ),
            const Center(
              child: Text(
                'SRI LANKAN SIGN LANGUAGE',
                style: TextStyle(fontSize: 9, letterSpacing: 2, color: muted),
              ),
            ),
          ],
        ),
      ),
    ),
  );
  void _open(BuildContext context, bool signup) => Navigator.of(context).push(
    MaterialPageRoute(
      builder: (_) => AuthScreen(session: session, signup: signup),
    ),
  );
}
