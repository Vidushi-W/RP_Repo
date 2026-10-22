import 'dart:convert';
import 'dart:typed_data';
import 'package:http/http.dart' as http;

const apiBase = String.fromEnvironment(
  'API_BASE_URL',
  defaultValue: 'http://10.0.2.2:8010',
);

class ApiError implements Exception {
  ApiError(this.message, this.status);
  final String message;
  final int status;
  @override
  String toString() => message;
}

class Api {
  String? token;
  Map<String, String> get headers => {
    'Content-Type': 'application/json',
    if (token != null) 'Authorization': 'Bearer $token',
  };
  dynamic decode(http.Response response) {
    dynamic data;
    try {
      data = jsonDecode(utf8.decode(response.bodyBytes));
    } catch (_) {
      data = null;
    }
    if (response.statusCode >= 400) {
      final detail = data is Map ? data['detail'] : null;
      throw ApiError(
        detail is String
            ? detail
            : 'The request could not be completed. Please check your input.',
        response.statusCode,
      );
    }
    return data;
  }

  Future<dynamic> request(
    String method,
    String path, {
    Map<String, dynamic>? body,
  }) async {
    try {
      final request = http.Request(method, Uri.parse('$apiBase$path'))
        ..headers.addAll(headers);
      if (body != null) request.body = jsonEncode(body);
      return decode(
        await http.Response.fromStream(
          await request.send().timeout(const Duration(seconds: 20)),
        ),
      );
    } on ApiError {
      rethrow;
    } catch (_) {
      throw ApiError(
        'Cannot reach your SLSL service. Check the connection and try again.',
        0,
      );
    }
  }

  Future<Map<String, dynamic>> upload(Uint8List bytes, String name) async {
    try {
      final request = http.MultipartRequest(
        'POST',
        Uri.parse('$apiBase/recognitions'),
      );
      request.headers['Authorization'] = 'Bearer $token';
      request.files.add(
        http.MultipartFile.fromBytes('file', bytes, filename: name),
      );
      return Map<String, dynamic>.from(
        decode(
          await http.Response.fromStream(
            await request.send().timeout(const Duration(seconds: 40)),
          ),
        ),
      );
    } on ApiError {
      rethrow;
    } catch (_) {
      throw ApiError('Recording could not be sent. Check your connection.', 0);
    }
  }

  Future<Uint8List> audio(String id) async {
    final response = await http
        .get(Uri.parse('$apiBase/recognitions/$id/audio'), headers: headers)
        .timeout(const Duration(seconds: 30));
    if (response.statusCode != 200) {
      decode(response);
      throw ApiError('Audio is not ready.', response.statusCode);
    }
    return response.bodyBytes;
  }
}
