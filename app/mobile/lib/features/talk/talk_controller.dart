import 'dart:async';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:path_provider/path_provider.dart';
import 'package:audioplayers/audioplayers.dart';
import '../../core/session.dart';
import 'motion_source.dart';

class TalkController extends ChangeNotifier {
  TalkController(this.session) {
    player.onPlayerStateChanged.listen((s) {
      playing = s == PlayerState.playing;
      if (!_closed) notifyListeners();
    });
  }
  final Session session;
  final player = AudioPlayer();
  Map<String, dynamic>? result;
  String? error;
  bool sending = false, playing = false, polling = false;
  bool _closed = false;
  String? _played;
  String? _audioPath;
  bool get busy =>
      sending ||
      (result != null && !['done', 'error'].contains(result!['stage']));
  String get stage => sending ? 'upload' : result?['stage'] ?? 'idle';
  Future<void> recognize(MotionSource source) async {
    if (busy) return;
    error = null;
    notifyListeners();
    try {
      final input = await source.capture();
      if (input == null || _closed) return;
      await player.stop();
      if (_audioPath != null) {
        await File(_audioPath!).delete().catchError((_) => File(_audioPath!));
      }
      _audioPath = null;
      _played = null;
      sending = true;
      result = null;
      notifyListeners();
      result = await session.api.upload(input.bytes, input.name);
      sending = false;
      if (!_closed) notifyListeners();
      await watch();
    } catch (e) {
      error = e.toString();
      sending = false;
      if (!_closed) notifyListeners();
    }
  }

  Future<void> watch() async {
    if (polling || result == null) return;
    polling = true;
    try {
      while (!_closed) {
        result = Map<String, dynamic>.from(
          await session.api.request('GET', '/recognitions/${result!['id']}'),
        );
        if (_closed) break;
        await session.history.save(session.user!['id'], result!);
        notifyListeners();
        if (['done', 'error'].contains(stage)) {
          if (result!['audio_ready'] == true && _played != result!['id']) {
            _played = result!['id'];
            await play();
          }
          break;
        }
        await Future<void>.delayed(const Duration(milliseconds: 1200));
      }
    } catch (e) {
      error = e.toString();
      if (!_closed) notifyListeners();
    } finally {
      polling = false;
      if (!_closed) notifyListeners();
    }
  }

  Future<void> play() async {
    try {
      if (playing) {
        await player.pause();
        return;
      }
      if (_audioPath == null) {
        final bytes = await session.api.audio(result!['id']);
        if (_closed) return;
        final path =
            '${(await getTemporaryDirectory()).path}/slsl-${result!['id']}.wav';
        await File(path).writeAsBytes(bytes);
        _audioPath = path;
      }
      if (!_closed) await player.play(DeviceFileSource(_audioPath!));
    } catch (_) {
      error = 'Voice could not play. Check media volume and tap Play again.';
      if (!_closed) notifyListeners();
    }
  }

  Future<void> retry() async {
    if (busy || result == null) return;
    try {
      error = null;
      _played = null;
      result = Map<String, dynamic>.from(
        await session.api.request(
          'POST',
          '/recognitions/${result!['id']}/retry',
        ),
      );
      if (!_closed) notifyListeners();
      await watch();
    } catch (e) {
      error = e.toString();
      if (!_closed) notifyListeners();
    }
  }

  Future<void> edit(String text) async {
    if (busy || result == null) return;
    try {
      await player.stop();
      if (_audioPath != null) {
        await File(_audioPath!).delete().catchError((_) => File(_audioPath!));
      }
      _audioPath = null;
      _played = null;
      error = null;
      result = Map<String, dynamic>.from(
        await session.api.request(
          'PATCH',
          '/recognitions/${result!['id']}/sinhala',
          body: {'text': text},
        ),
      );
      if (!_closed) notifyListeners();
      await watch();
    } catch (e) {
      error = e.toString();
      if (!_closed) notifyListeners();
    }
  }

  void resume(Map<String, dynamic> row) {
    result = row;
    error = null;
    notifyListeners();
    if (!['done', 'error'].contains(stage)) watch();
  }

  @override
  void dispose() {
    _closed = true;
    player.dispose();
    if (_audioPath != null) File(_audioPath!).delete().ignore();
    super.dispose();
  }
}
