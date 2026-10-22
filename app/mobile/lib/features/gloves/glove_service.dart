import 'package:flutter/services.dart';

/// Replace or extend this transport when the team finalizes the glove protocol.
/// No invented UUIDs, sensor mappings or fake motion streams are used here.
class GloveService {
  static const _channel = MethodChannel('lk.slsl/connect/gloves');
  Future<List<Map<String, dynamic>>> scan() async {
    final devices = await _channel.invokeListMethod<dynamic>('scan');
    return (devices ?? []).map((d) => Map<String, dynamic>.from(d)).toList();
  }

  Future<void> connect(String id) =>
      _channel.invokeMethod('connect', {'id': id});
  Future<void> disconnect() => _channel.invokeMethod('disconnect');
}
