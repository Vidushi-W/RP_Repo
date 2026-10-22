import 'package:flutter/material.dart';
import '../../core/theme.dart';

/// Replace this route with a teammate's independently owned feature module.
class FutureFeatureScreen extends StatelessWidget {
  const FutureFeatureScreen({
    super.key,
    required this.title,
    required this.icon,
  });
  final String title;
  final IconData icon;
  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: Text(title)),
    body: Padding(
      padding: const EdgeInsets.all(28),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(icon, size: 76, color: green),
          const SizedBox(height: 26),
          Text(
            'More ways to connect.',
            style: Theme.of(context).textTheme.headlineMedium,
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 14),
          Text(
            '$title is reserved for the next team module. This feature is not available yet.',
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 30),
          OutlinedButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Back to home'),
          ),
        ],
      ),
    ),
  );
}
