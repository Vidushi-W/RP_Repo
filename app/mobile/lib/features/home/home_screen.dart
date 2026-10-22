import 'package:flutter/material.dart';
import '../../core/session.dart';
import '../../core/theme.dart';
import '../talk/talk_screen.dart';
import '../talk/history_screen.dart';
import '../gloves/glove_screen.dart';
import '../shared/future_feature_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key, required this.session});
  final Session session;
  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  void open(Widget page) =>
      Navigator.of(context).push(MaterialPageRoute(builder: (_) => page));
  String get greeting => DateTime.now().hour < 12
      ? 'Good morning'
      : DateTime.now().hour < 17
      ? 'Good afternoon'
      : 'Good evening';
  @override
  Widget build(BuildContext context) {
    final name = widget.session.user!['username'] as String;
    return Scaffold(
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(24, 23, 24, 26),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  const Brand(small: true),
                  const Spacer(),
                  IconButton.filledTonal(
                    tooltip: 'Your account',
                    onPressed: account,
                    icon: Text(
                      name[0].toUpperCase(),
                      style: const TextStyle(fontWeight: FontWeight.bold),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 30),
              Text(
                '$greeting,',
                style: const TextStyle(fontSize: 16, color: muted),
              ),
              Text(
                '$name 👋',
                style: Theme.of(context).textTheme.headlineMedium,
              ),
              const SizedBox(height: 8),
              const Text('A good day starts with a little connection.'),
              const SizedBox(height: 26),
              Container(
                padding: const EdgeInsets.all(23),
                decoration: BoxDecoration(
                  color: forest,
                  borderRadius: BorderRadius.circular(26),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Row(
                      children: [
                        Icon(
                          Icons.auto_awesome_outlined,
                          color: lime,
                          size: 18,
                        ),
                        SizedBox(width: 8),
                        Text(
                          'LET YOUR HANDS DO THE TALKING',
                          style: TextStyle(
                            color: lime,
                            fontSize: 9,
                            fontWeight: FontWeight.w600,
                            letterSpacing: 1,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 18),
                    const Text(
                      'Every sign is a\nchance to connect.',
                      style: TextStyle(
                        fontSize: 26,
                        color: Colors.white,
                        fontWeight: FontWeight.w600,
                        height: 1.2,
                        letterSpacing: -.5,
                      ),
                    ),
                    const SizedBox(height: 16),
                    Row(
                      children: [
                        const Expanded(
                          child: Text(
                            'Your words, spoken in Sinhala.',
                            style: TextStyle(
                              color: Color(0xFFB9D0BD),
                              fontSize: 12,
                            ),
                          ),
                        ),
                        IconButton.filled(
                          tooltip: 'Start talking',
                          style: IconButton.styleFrom(
                            backgroundColor: lime,
                            foregroundColor: forest,
                          ),
                          onPressed: () =>
                              open(TalkScreen(session: widget.session)),
                          icon: const Icon(Icons.arrow_forward),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 20),
              InkWell(
                borderRadius: BorderRadius.circular(17),
                onTap: () => open(const GloveScreen()),
                child: Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: const Color(0xFFE9EEDF),
                    borderRadius: BorderRadius.circular(17),
                  ),
                  child: const Row(
                    children: [
                      Icon(Icons.bluetooth_rounded, color: green),
                      SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'Your gloves',
                              style: TextStyle(
                                fontWeight: FontWeight.w700,
                                color: ink,
                              ),
                            ),
                            Text(
                              'Connect a device · CSV input available',
                              style: TextStyle(fontSize: 11, color: muted),
                            ),
                          ],
                        ),
                      ),
                      Icon(Icons.chevron_right, color: green),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 28),
              const Row(
                children: [
                  Text(
                    'How can we help today?',
                    style: TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.w700,
                      color: ink,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 14),
              LayoutBuilder(
                builder: (context, c) => GridView.count(
                  crossAxisCount: 2,
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  crossAxisSpacing: 12,
                  mainAxisSpacing: 12,
                  childAspectRatio: c.maxWidth < 340 ? 0.94 : 1.05,
                  children: [
                    feature(
                      'Talk to someone',
                      'Turn signs into a voice',
                      Icons.forum_rounded,
                      true,
                      () => open(TalkScreen(session: widget.session)),
                    ),
                    feature(
                      'Listen to something',
                      'Bring sound into view',
                      Icons.hearing_rounded,
                      false,
                      () =>
                          future('Listen to something', Icons.hearing_rounded),
                    ),
                    feature(
                      'Learn sign language',
                      'Build a new connection',
                      Icons.menu_book_rounded,
                      false,
                      () => future(
                        'Learn sign language',
                        Icons.menu_book_rounded,
                      ),
                    ),
                    feature(
                      'Emergency',
                      'Support when it matters',
                      Icons.health_and_safety_outlined,
                      false,
                      () =>
                          future('Emergency', Icons.health_and_safety_outlined),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 26),
              Row(
                children: [
                  const Expanded(
                    child: Text(
                      'Your recent conversations',
                      style: TextStyle(
                        fontSize: 17,
                        fontWeight: FontWeight.w700,
                        color: ink,
                      ),
                    ),
                  ),
                  TextButton(
                    onPressed: () =>
                        open(HistoryScreen(session: widget.session)),
                    child: const Text('View all'),
                  ),
                ],
              ),
              const Text(
                'Revisit the words you’ve shared, all in one place.',
                style: TextStyle(fontSize: 13),
              ),
            ],
          ),
        ),
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: 0,
        onDestinationSelected: (index) {
          if (index == 1) open(HistoryScreen(session: widget.session));
          if (index == 2) account();
        },
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.home_outlined),
            selectedIcon: Icon(Icons.home_rounded),
            label: 'Home',
          ),
          NavigationDestination(
            icon: Icon(Icons.history_rounded),
            label: 'Conversations',
          ),
          NavigationDestination(
            icon: Icon(Icons.person_outline),
            label: 'Account',
          ),
        ],
      ),
    );
  }

  Widget feature(
    String title,
    String subtitle,
    IconData icon,
    bool active,
    VoidCallback tap,
  ) => Material(
    color: active ? lime : Colors.white,
    borderRadius: BorderRadius.circular(22),
    child: InkWell(
      onTap: tap,
      borderRadius: BorderRadius.circular(22),
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(icon, color: forest, size: 28),
                const Spacer(),
                Icon(
                  active ? Icons.north_east : Icons.lock_outline_rounded,
                  size: 16,
                  color: muted,
                ),
              ],
            ),
            const Spacer(),
            Text(
              title,
              style: const TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.w700,
                color: ink,
                height: 1.2,
              ),
            ),
            const SizedBox(height: 5),
            Text(
              active ? subtitle : 'Coming later',
              style: const TextStyle(fontSize: 11, color: muted),
            ),
          ],
        ),
      ),
    ),
  );
  void future(String title, IconData icon) =>
      open(FutureFeatureScreen(title: title, icon: icon));
  Future<void> account() async {
    final logout = await showModalBottomSheet<bool>(
      context: context,
      showDragHandle: true,
      builder: (ctx) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(24, 10, 24, 30),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                widget.session.user!['username'],
                style: Theme.of(ctx).textTheme.titleLarge,
              ),
              Text(widget.session.user!['email']),
              const SizedBox(height: 20),
              const Text(
                'Your voice, your pace.',
                style: TextStyle(fontSize: 20, color: forest),
              ),
              const SizedBox(height: 20),
              OutlinedButton(
                onPressed: () => Navigator.pop(ctx, true),
                child: const Text('Log out'),
              ),
            ],
          ),
        ),
      ),
    );
    if (logout == true) {
      try {
        await widget.session.logout();
      } catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(
            context,
          ).showSnackBar(SnackBar(content: Text(e.toString())));
        }
      }
    }
  }
}
