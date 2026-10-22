import 'package:flutter/material.dart';
import '../../core/session.dart';
import '../../core/theme.dart';
import 'talk_screen.dart';

class HistoryScreen extends StatefulWidget {
  const HistoryScreen({super.key, required this.session});
  final Session session;
  @override
  State<HistoryScreen> createState() => _HistoryScreenState();
}

class _HistoryScreenState extends State<HistoryScreen> {
  List<Map<String, dynamic>> rows = [];
  bool loading = true;
  String? error;
  @override
  void initState() {
    super.initState();
    load();
  }

  Future<void> load() async {
    try {
      final user = widget.session.user!['id'] as String;
      final cached = await widget.session.history.list(user);
      if (mounted) setState(() => rows = cached);
      final remote =
          await widget.session.api.request('GET', '/recognitions') as List;
      await widget.session.history.clear(user);
      for (final row in remote) {
        await widget.session.history.save(user, Map<String, dynamic>.from(row));
      }
      if (mounted) {
        setState(() {
          rows = remote.map((r) => Map<String, dynamic>.from(r)).toList();
          error = null;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(
          () => error =
              'Offline? Showing saved text. Audio needs the service connection.',
        );
      }
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Your conversations')),
    body: RefreshIndicator(
      onRefresh: load,
      child: ListView(
        padding: const EdgeInsets.all(24),
        children: [
          const Label('WORDS WORTH KEEPING'),
          const SizedBox(height: 12),
          Text(
            'A little history.\nA lot of connection.',
            style: Theme.of(context).textTheme.headlineMedium,
          ),
          const SizedBox(height: 20),
          if (error != null) Notice(error!),
          if (loading) const LinearProgressIndicator(),
          if (!loading && rows.isEmpty)
            const Notice(
              'Your conversations will appear here after you recognize a motion recording.',
            ),
          ...rows.map(
            (row) => Card(
              margin: const EdgeInsets.only(bottom: 12),
              child: ListTile(
                contentPadding: const EdgeInsets.all(16),
                title: Text(
                  row['sentence']?['text'] ??
                      (row['words'] as List? ?? []).join(' · '),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
                subtitle: Text(
                  row['sinhala'] ?? row['stage'],
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
                leading: const Icon(Icons.forum_outlined, color: green),
                onTap: () async {
                  await Navigator.push(
                    context,
                    MaterialPageRoute(
                      builder: (_) =>
                          TalkScreen(session: widget.session, previous: row),
                    ),
                  );
                  if (mounted) load();
                },
                trailing: IconButton(
                  tooltip: 'Delete conversation',
                  icon: const Icon(Icons.delete_outline, size: 19),
                  onPressed: () => remove(row),
                ),
              ),
            ),
          ),
        ],
      ),
    ),
  );
  Future<void> remove(Map<String, dynamic> row) async {
    final yes = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Delete this conversation?'),
        content: const Text('Its saved text and audio will be removed.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Keep it'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Delete'),
          ),
        ],
      ),
    );
    if (yes != true) return;
    try {
      await widget.session.api.request('DELETE', '/recognitions/${row['id']}');
      await widget.session.history.remove(
        widget.session.user!['id'],
        row['id'],
      );
      if (mounted) {
        setState(() => rows.removeWhere((r) => r['id'] == row['id']));
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(e.toString())));
      }
    }
  }
}
