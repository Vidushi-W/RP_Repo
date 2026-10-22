import 'package:flutter/material.dart';

const forest = Color(0xFF173F35),
    green = Color(0xFF2D6B50),
    lime = Color(0xFFD9EBC1),
    paper = Color(0xFFF6F7F1),
    ink = Color(0xFF193C33),
    muted = Color(0xFF65776C);
final appTheme = ThemeData(
  useMaterial3: true,
  scaffoldBackgroundColor: paper,
  colorScheme: ColorScheme.fromSeed(
    seedColor: green,
    primary: forest,
    surface: paper,
  ),
  textTheme: const TextTheme(
    headlineLarge: TextStyle(
      fontSize: 38,
      fontWeight: FontWeight.w700,
      height: 1.12,
      letterSpacing: -1.4,
      color: ink,
    ),
    headlineMedium: TextStyle(
      fontSize: 29,
      fontWeight: FontWeight.w700,
      letterSpacing: -.8,
      color: ink,
    ),
    titleLarge: TextStyle(
      fontSize: 21,
      fontWeight: FontWeight.w700,
      color: ink,
    ),
    bodyLarge: TextStyle(fontSize: 16, height: 1.5, color: ink),
    bodyMedium: TextStyle(fontSize: 14, height: 1.5, color: muted),
  ),
  appBarTheme: const AppBarTheme(
    backgroundColor: paper,
    foregroundColor: forest,
    scrolledUnderElevation: 0,
    centerTitle: false,
  ),
  inputDecorationTheme: InputDecorationTheme(
    filled: true,
    fillColor: Colors.white,
    contentPadding: const EdgeInsets.all(18),
    border: OutlineInputBorder(
      borderRadius: BorderRadius.circular(16),
      borderSide: const BorderSide(color: Color(0xFFDDE4D8)),
    ),
    enabledBorder: OutlineInputBorder(
      borderRadius: BorderRadius.circular(16),
      borderSide: const BorderSide(color: Color(0xFFDDE4D8)),
    ),
  ),
  filledButtonTheme: FilledButtonThemeData(
    style: FilledButton.styleFrom(
      minimumSize: const Size.fromHeight(56),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
      textStyle: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
    ),
  ),
  outlinedButtonTheme: OutlinedButtonThemeData(
    style: OutlinedButton.styleFrom(
      minimumSize: const Size.fromHeight(54),
      side: const BorderSide(color: Color(0xFFCCD8CA)),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
    ),
  ),
  cardTheme: CardThemeData(
    elevation: 0,
    color: Colors.white,
    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)),
  ),
);

class Brand extends StatelessWidget {
  const Brand({super.key, this.small = false});
  final bool small;
  @override
  Widget build(BuildContext context) => Row(
    mainAxisSize: MainAxisSize.min,
    children: [
      Container(
        padding: EdgeInsets.all(small ? 9 : 11),
        decoration: BoxDecoration(
          color: forest,
          borderRadius: BorderRadius.circular(14),
        ),
        child: Icon(
          Icons.sign_language_rounded,
          color: lime,
          size: small ? 20 : 25,
        ),
      ),
      const SizedBox(width: 10),
      Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'slsl connect',
            style: TextStyle(
              fontSize: small ? 18 : 22,
              fontWeight: FontWeight.w800,
              letterSpacing: -.8,
              color: forest,
            ),
          ),
          if (!small)
            const Text(
              'YOUR WORDS. YOUR WORLD.',
              style: TextStyle(
                fontSize: 8.5,
                letterSpacing: 1.5,
                fontWeight: FontWeight.w600,
                color: muted,
              ),
            ),
        ],
      ),
    ],
  );
}

class Label extends StatelessWidget {
  const Label(this.text, {super.key});
  final String text;
  @override
  Widget build(BuildContext context) => Text(
    text,
    style: const TextStyle(
      fontSize: 10,
      fontWeight: FontWeight.w800,
      letterSpacing: 1.5,
      color: green,
    ),
  );
}

class Notice extends StatelessWidget {
  const Notice(this.text, {super.key, this.error = false});
  final String text;
  final bool error;
  @override
  Widget build(BuildContext context) => Container(
    width: double.infinity,
    padding: const EdgeInsets.all(14),
    margin: const EdgeInsets.symmetric(vertical: 8),
    decoration: BoxDecoration(
      color: error ? const Color(0xFFFFEDE9) : const Color(0xFFEAF0E1),
      borderRadius: BorderRadius.circular(14),
    ),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(
          error ? Icons.info_outline : Icons.lightbulb_outline,
          size: 18,
          color: error ? Colors.brown : green,
        ),
        const SizedBox(width: 10),
        Expanded(
          child: Text(
            text,
            style: TextStyle(
              fontSize: 13,
              color: error ? Colors.brown : forest,
              height: 1.5,
            ),
          ),
        ),
      ],
    ),
  );
}
