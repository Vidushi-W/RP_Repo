import 'package:flutter/material.dart';
import '../../core/theme.dart';
import 'glove_service.dart';

class GloveScreen extends StatefulWidget {
  const GloveScreen({super.key});
  @override
  State<GloveScreen> createState() => _GloveScreenState();
}

class _GloveScreenState extends State<GloveScreen> {
  final service = GloveService();
  List<Map<String, dynamic>> devices = [];
  bool scanning = false;
  String? connected, error;
  Future<void> scan() async {
    setState(() {
      scanning = true;
      error = null;
    });
    try {
      final result = await service.scan();
      if (mounted) setState(() => devices = result);
    } catch (e) {
      if (mounted) {
        setState(
          () => error =
              'Bluetooth is unavailable or permission was denied. Turn on Bluetooth and try on a physical Android phone.',
        );
      }
    } finally {
      if (mounted) setState(() => scanning = false);
    }
  }

  @override
  void dispose() {
    service.disconnect().catchError((_) {});
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Your gloves')),
    body: ListView(
      padding: const EdgeInsets.all(24),
      children: [
        const Icon(Icons.bluetooth_rounded, size: 70, color: green),
        const SizedBox(height: 24),
        Text(
          'A connection\nwithin reach.',
          style: Theme.of(context).textTheme.headlineMedium,
        ),
        const SizedBox(height: 14),
        const Text(
          'Find nearby Bluetooth Low Energy devices. Only connect to gloves your team has identified.',
        ),
        const SizedBox(height: 20),
        const Notice(
          'Your team has not selected a glove protocol yet. Device discovery and connection are available; live motion decoding will be added when the hardware format is defined. Use CSV input for recognition now.',
        ),
        const SizedBox(height: 16),
        FilledButton.icon(
          onPressed: scanning ? null : scan,
          icon: scanning
              ? const SizedBox(
                  width: 18,
                  height: 18,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : const Icon(Icons.bluetooth_searching),
          label: Text(scanning ? 'Looking for devices…' : 'Find nearby gloves'),
        ),
        if (error != null) Notice(error!, error: true),
        if (!scanning && devices.isEmpty)
          const Padding(
            padding: EdgeInsets.only(top: 20),
            child: Text(
              'No devices listed. Keep your gloves nearby and in pairing mode.',
            ),
          ),
        if (connected != null)
          Notice(
            'Connected to $connected. Sensor decoding is not configured yet.',
          ),
        ...devices.map(
          (d) => Card(
            child: ListTile(
              title: Text(d['name'] as String),
              subtitle: Text('${d['id']} · ${d['rssi']} dBm'),
              trailing: const Icon(Icons.chevron_right),
              onTap: () async {
                try {
                  await service.connect(d['id']);
                  if (mounted) setState(() => connected = d['name']);
                } catch (e) {
                  if (mounted) {
                    setState(
                      () => error =
                          'Could not connect to this device. Please try again.',
                    );
                  }
                }
              },
            ),
          ),
        ),
      ],
    ),
  );
}
