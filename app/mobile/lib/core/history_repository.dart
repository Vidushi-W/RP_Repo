import 'dart:convert';
import 'package:sqflite/sqflite.dart';

class HistoryRepository {
  Database? _db;
  Future<Database> get db async => _db ??= await openDatabase(
    '${await getDatabasesPath()}/slsl-client.db',
    version: 1,
    onCreate: (d, _) async {
      await d.execute(
        'CREATE TABLE history (id TEXT PRIMARY KEY,user_id TEXT NOT NULL,payload TEXT NOT NULL)',
      );
    },
  );
  Future<void> save(String user, Map<String, dynamic> row) async =>
      (await db).insert('history', {
        'id': row['id'],
        'user_id': user,
        'payload': jsonEncode(row),
      }, conflictAlgorithm: ConflictAlgorithm.replace);
  Future<List<Map<String, dynamic>>> list(String user) async =>
      (await (await db).query(
            'history',
            where: 'user_id = ?',
            whereArgs: [user],
          ))
          .map(
            (r) =>
                Map<String, dynamic>.from(jsonDecode(r['payload'] as String)),
          )
          .toList()
        ..sort((a, b) => (b['created'] as num).compareTo(a['created'] as num));
  Future<void> remove(String user, String id) async {
    await (await db).delete(
      'history',
      where: 'user_id = ? AND id = ?',
      whereArgs: [user, id],
    );
  }

  Future<void> clear(String user) async {
    await (await db).delete('history', where: 'user_id = ?', whereArgs: [user]);
  }
}
