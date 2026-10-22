import 'package:flutter/material.dart';
import '../../core/session.dart';
import '../../core/theme.dart';
import '../gloves/glove_screen.dart';
import 'motion_source.dart';
import 'talk_controller.dart';

class TalkScreen extends StatefulWidget {
  const TalkScreen({super.key, required this.session, this.previous});
  final Session session;
  final Map<String, dynamic>? previous;
  @override
  State<TalkScreen> createState() => _TalkScreenState();
}

class _TalkScreenState extends State<TalkScreen> {
  late final controller = TalkController(widget.session);
  @override
  void initState() {
    super.initState();
    if (widget.previous != null) controller.resume(widget.previous!);
  }

  @override
  void dispose() {
    controller.dispose();
    super.dispose();
  }

  static const stages = [
    'queued',
    'motion',
    'sentence',
    'translation',
    'voice',
  ];
  static const names = [
    'Waiting for the model…',
    'Predicting motion…',
    'Analyzing your words…',
    'Translating to Sinhala…',
    'Preparing your voice…',
  ];
  @override
  Widget build(BuildContext context) => ListenableBuilder(
    listenable: controller,
    builder: (context, _) {
      final row = controller.result;
      final words = (row?['words'] as List?) ?? [];
      final emotion = row?['expression']?['label'];
      final sentence = row?['sentence'];
      final stage = controller.stage;
      final active = stages.indexOf(stage);
      return Scaffold(
        appBar: AppBar(
          title: const Text(
            'Talk to someone',
            style: TextStyle(fontSize: 19, fontWeight: FontWeight.w600),
          ),
        ),
        body: SafeArea(
          child: SingleChildScrollView(
            padding: const EdgeInsets.fromLTRB(24, 12, 24, 36),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Label('FROM YOUR HANDS TO THEIR EARS'),
                const SizedBox(height: 12),
                Text(
                  'A conversation,\nin your own way.',
                  style: Theme.of(context).textTheme.headlineMedium,
                ),
                const SizedBox(height: 12),
                const Text(
                  'Add a motion recording. We’ll find your words and speak them in Sinhala.',
                ),
                const SizedBox(height: 22),
                Container(
                  padding: const EdgeInsets.all(22),
                  decoration: BoxDecoration(
                    color: forest,
                    borderRadius: BorderRadius.circular(26),
                  ),
                  child: Column(
                    children: [
                      const Row(
                        children: [
                          Icon(
                            Icons.sign_language_rounded,
                            color: lime,
                            size: 34,
                          ),
                          SizedBox(width: 14),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  'Start with your motion',
                                  style: TextStyle(
                                    color: Colors.white,
                                    fontSize: 18,
                                    fontWeight: FontWeight.w600,
                                  ),
                                ),
                                SizedBox(height: 4),
                                Text(
                                  'CSV input is ready to use',
                                  style: TextStyle(
                                    color: Color(0xFFBBD0BC),
                                    fontSize: 12,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 22),
                      FilledButton.icon(
                        style: FilledButton.styleFrom(
                          backgroundColor: lime,
                          foregroundColor: forest,
                        ),
                        onPressed: controller.busy
                            ? null
                            : () => controller.recognize(CsvMotionSource()),
                        icon: const Icon(Icons.upload_file_outlined),
                        label: Text(
                          row == null
                              ? 'Choose a motion CSV'
                              : 'Choose another CSV',
                        ),
                      ),
                      const SizedBox(height: 8),
                      TextButton.icon(
                        style: TextButton.styleFrom(foregroundColor: lime),
                        onPressed: () => Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (_) => const GloveScreen(),
                          ),
                        ),
                        icon: const Icon(Icons.bluetooth, size: 19),
                        label: const Text('Connect your gloves'),
                      ),
                    ],
                  ),
                ),
                if (controller.error != null) ...[
                  Notice(controller.error!, error: true),
                  if (row != null && !['done', 'error'].contains(stage))
                    TextButton(
                      onPressed: controller.polling ? null : controller.watch,
                      child: const Text('Reconnect to this recognition'),
                    ),
                ],
                if (controller.busy) ...[
                  const SizedBox(height: 20),
                  Semantics(
                    liveRegion: true,
                    child: Container(
                      padding: const EdgeInsets.all(18),
                      decoration: BoxDecoration(
                        color: lime.withValues(alpha: .55),
                        borderRadius: BorderRadius.circular(20),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              const SizedBox(
                                width: 19,
                                height: 19,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2,
                                ),
                              ),
                              const SizedBox(width: 14),
                              Expanded(
                                child: Text(
                                  stage == 'upload'
                                      ? 'Sending your recording…'
                                      : active >= 0
                                      ? names[active]
                                      : 'Processing…',
                                  style: const TextStyle(
                                    fontWeight: FontWeight.w700,
                                    color: forest,
                                  ),
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 16),
                          Row(
                            children: List.generate(
                              4,
                              (i) => Expanded(
                                child: Container(
                                  height: 4,
                                  margin: const EdgeInsets.symmetric(
                                    horizontal: 3,
                                  ),
                                  decoration: BoxDecoration(
                                    color: i < (active < 1 ? 0 : active)
                                        ? green
                                        : Colors.white,
                                    borderRadius: BorderRadius.circular(4),
                                  ),
                                ),
                              ),
                            ),
                          ),
                          const SizedBox(height: 10),
                          const Text(
                            'Motion  →  Words  →  Sinhala  →  Voice',
                            style: TextStyle(fontSize: 10, color: green),
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
                if (row != null) ...[
                  const SizedBox(height: 24),
                  Row(
                    children: [
                      const Expanded(child: Label('YOUR CONVERSATION')),
                      if (row['model'] != null)
                        Text(
                          'Model v${row['model']['version']}',
                          style: const TextStyle(fontSize: 10, color: muted),
                        ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  outputCard(
                    '01',
                    'Recognized words',
                    words.isEmpty
                        ? const Text('Your words will appear here.')
                        : Wrap(
                            spacing: 7,
                            runSpacing: 7,
                            children: words
                                .map(
                                  (w) => Container(
                                    padding: const EdgeInsets.symmetric(
                                      horizontal: 12,
                                      vertical: 7,
                                    ),
                                    decoration: BoxDecoration(
                                      color: const Color(0xFFEEF2E7),
                                      borderRadius: BorderRadius.circular(9),
                                    ),
                                    child: Text(
                                      '$w',
                                      style: const TextStyle(
                                        color: forest,
                                        fontSize: 13,
                                        fontWeight: FontWeight.w700,
                                      ),
                                    ),
                                  ),
                                )
                                .toList(),
                          ),
                  ),
                  if (sentence != null)
                    outputCard(
                      '02',
                      'Your sentence',
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            sentence['text'].toString().isEmpty
                                ? 'No supported words were recognized.'
                                : sentence['text'],
                            style: const TextStyle(
                              fontSize: 20,
                              color: ink,
                              height: 1.4,
                            ),
                          ),
                          if (emotion != null)
                            Padding(
                              padding: const EdgeInsets.only(top: 8),
                              child: Chip(
                                avatar: const Icon(
                                  Icons.bolt_rounded,
                                  size: 16,
                                ),
                                label: Text('$emotion expression'),
                              ),
                            ),
                          const SizedBox(height: 8),
                          Text(
                            sentence['status'] == 'suggested'
                                ? 'AI-generated phrasing · Check the meaning'
                                : 'Word-based output · Check the meaning',
                            style: const TextStyle(fontSize: 11, color: muted),
                          ),
                        ],
                      ),
                    ),
                  if (row['sinhala'] != null)
                    outputCard(
                      '03',
                      'සිංහල · Sinhala',
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            row['sinhala'],
                            style: const TextStyle(
                              fontSize: 24,
                              color: ink,
                              height: 1.7,
                            ),
                          ),
                          const SizedBox(height: 12),
                          Text(
                            row['edited'] == true
                                ? 'Edited by you'
                                : 'Automatic translation can make mistakes.',
                            style: const TextStyle(fontSize: 11, color: muted),
                          ),
                          TextButton.icon(
                            onPressed: controller.busy ? null : edit,
                            icon: const Icon(Icons.edit_outlined, size: 16),
                            label: const Text(
                              'Edit Sinhala & regenerate voice',
                            ),
                          ),
                        ],
                      ),
                    ),
                  if (row['audio_ready'] == true)
                    Container(
                      padding: const EdgeInsets.all(20),
                      margin: const EdgeInsets.only(top: 2),
                      decoration: BoxDecoration(
                        color: lime,
                        borderRadius: BorderRadius.circular(22),
                      ),
                      child: Row(
                        children: [
                          IconButton.filled(
                            tooltip: controller.playing
                                ? 'Pause voice'
                                : 'Play voice',
                            onPressed: controller.play,
                            icon: Icon(
                              controller.playing
                                  ? Icons.pause_rounded
                                  : Icons.play_arrow_rounded,
                            ),
                          ),
                          const SizedBox(width: 14),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  controller.playing
                                      ? 'Speaking in Sinhala'
                                      : 'Your voice is ready',
                                  style: const TextStyle(
                                    fontSize: 16,
                                    fontWeight: FontWeight.w700,
                                    color: forest,
                                  ),
                                ),
                                Text(
                                  emotion == 'angry'
                                      ? 'Angry-style voice · simulated tone'
                                      : 'Natural voice · no emotion effect',
                                  style: const TextStyle(
                                    fontSize: 11,
                                    color: green,
                                  ),
                                ),
                              ],
                            ),
                          ),
                          const Icon(Icons.graphic_eq_rounded, color: green),
                        ],
                      ),
                    ),
                  if (row['error'] != null) Notice(row['error'], error: true),
                  if (row['stage'] == 'error' &&
                      row['sentence']?['text'] != null)
                    OutlinedButton.icon(
                      onPressed: controller.retry,
                      icon: const Icon(Icons.refresh_rounded),
                      label: const Text('Try again'),
                    ),

                  if (row['notice'] != null) Notice(row['notice']),
                ],
                const SizedBox(height: 20),
                const Notice(
                  'Voice plays automatically when ready. You can pause or replay it. Use your phone’s media volume.',
                ),
                if (row == null)
                  const Padding(
                    padding: EdgeInsets.only(top: 8),
                    child: Text(
                      'Motion CSV: time + 22 sensor channels. Your recording stays separate from admin training data.',
                      style: TextStyle(fontSize: 11, color: muted),
                    ),
                  ),
              ],
            ),
          ),
        ),
      );
    },
  );
  Widget outputCard(String number, String title, Widget child) => Container(
    width: double.infinity,
    padding: const EdgeInsets.all(20),
    margin: const EdgeInsets.only(bottom: 12),
    decoration: BoxDecoration(
      color: Colors.white,
      borderRadius: BorderRadius.circular(22),
      border: Border.all(color: const Color(0xFFE5EADF)),
    ),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Text(number, style: const TextStyle(fontSize: 10, color: muted)),
            const SizedBox(width: 10),
            Text(
              title,
              style: const TextStyle(
                fontSize: 12,
                color: muted,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
        const SizedBox(height: 14),
        child,
      ],
    ),
  );
  Future<void> edit() async {
    final text = TextEditingController(text: controller.result!['sinhala']);
    final value = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Edit Sinhala'),
        content: TextField(
          controller: text,
          maxLines: 5,
          decoration: const InputDecoration(labelText: 'Sinhala sentence'),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, text.text),
            child: const Text('Save & speak'),
          ),
        ],
      ),
    );
    // Dialog route animations can still read its controller; dispose after removal.
    await Future<void>.delayed(const Duration(milliseconds: 300));
    text.dispose();
    if (value != null && mounted) await controller.edit(value);
  }
}
