import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'api.dart';
import 'history_repository.dart';

class Session extends ChangeNotifier {
  final api = Api();
  final history = HistoryRepository();
  final _secure = const FlutterSecureStorage();
  Map<String, dynamic>? user;
  bool restoring = true;
  Future<void> restore() async {
    try {
      api.token = await _secure.read(key: 'session_token');
      if (api.token != null) {
        final result = await api.request('GET', '/auth/me');
        user = Map<String, dynamic>.from(result);
        await _secure.write(key: 'profile', value: jsonEncode(user));
      }
    } catch (e) {
      if (e is ApiError && e.status == 0) {
        final cached = await _secure.read(key: 'profile');
        if (cached != null) {
          user = Map<String, dynamic>.from(jsonDecode(cached));
        }
      } else {
        api.token = null;
        await _secure.deleteAll();
      }
    } finally {
      restoring = false;
      notifyListeners();
    }
  }

  Future<void> authenticate(
    bool signup,
    String name,
    String email,
    String password,
  ) async {
    final result = await api.request(
      'POST',
      signup ? '/auth/signup' : '/auth/login',
      body: {
        if (signup) 'username': name,
        'email': email.trim(),
        'password': password,
      },
    );
    api.token = result['token'];
    user = Map<String, dynamic>.from(result['user']);
    await _secure.write(key: 'session_token', value: api.token);
    await _secure.write(key: 'profile', value: jsonEncode(user));
    notifyListeners();
  }

  Future<void> logout() async {
    // A remote session must be revoked before local sign-out succeeds.
    await api.request('POST', '/auth/logout');
    if (user != null) await history.clear(user!['id']);
    await _secure.deleteAll();
    api.token = null;
    user = null;
    notifyListeners();
  }
}
