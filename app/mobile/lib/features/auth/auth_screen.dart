import 'package:flutter/material.dart';
import '../../core/session.dart';
import '../../core/theme.dart';

String? passwordError(String value) {
  if (value.length < 12 || value.length > 128) return 'Use 12–128 characters.';
  if (!RegExp(r'[A-Z]').hasMatch(value) ||
      !RegExp(r'[a-z]').hasMatch(value) ||
      !RegExp(r'[0-9]').hasMatch(value) ||
      !RegExp(r'[^a-zA-Z0-9\s]').hasMatch(value)) {
    return 'Add uppercase, lowercase, a number and a symbol.';
  }
  return null;
}

class AuthScreen extends StatefulWidget {
  const AuthScreen({super.key, required this.session, required this.signup});
  final Session session;
  final bool signup;
  @override
  State<AuthScreen> createState() => _AuthScreenState();
}

class _AuthScreenState extends State<AuthScreen> {
  final form = GlobalKey<FormState>();
  final name = TextEditingController(),
      email = TextEditingController(),
      password = TextEditingController();
  bool hidden = true, busy = false;
  String? error;
  @override
  void dispose() {
    name.dispose();
    email.dispose();
    password.dispose();
    super.dispose();
  }

  Future<void> submit() async {
    if (!form.currentState!.validate()) return;
    setState(() {
      busy = true;
      error = null;
    });
    try {
      await widget.session.authenticate(
        widget.signup,
        name.text.trim(),
        email.text,
        password.text,
      );
      if (mounted) Navigator.of(context).popUntil((r) => r.isFirst);
    } catch (e) {
      if (mounted) setState(() => error = e.toString());
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(),
    body: SafeArea(
      child: SingleChildScrollView(
        padding: const EdgeInsets.fromLTRB(26, 4, 26, 32),
        child: AutofillGroup(
          child: Form(
            key: form,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Brand(small: true),
                const SizedBox(height: 32),
                Label(
                  widget.signup
                      ? 'A NEW CONNECTION STARTS HERE'
                      : 'GOOD TO SEE YOU AGAIN',
                ),
                const SizedBox(height: 12),
                Text(
                  widget.signup
                      ? 'Make room for\nyour voice.'
                      : 'Welcome\nback.',
                  style: Theme.of(context).textTheme.headlineLarge,
                ),
                const SizedBox(height: 14),
                Text(
                  widget.signup
                      ? 'Create your account and start your first conversation.'
                      : 'Log in to pick up where you left off.',
                ),
                const SizedBox(height: 28),
                if (widget.signup) ...[
                  TextFormField(
                    controller: name,
                    textCapitalization: TextCapitalization.words,
                    autofillHints: const [AutofillHints.nickname],
                    decoration: const InputDecoration(
                      labelText: 'Username',
                      prefixIcon: Icon(Icons.person_outline),
                    ),
                    validator: (v) => (v ?? '').trim().length < 2
                        ? 'Enter at least two characters.'
                        : null,
                  ),
                  const SizedBox(height: 16),
                ],
                TextFormField(
                  controller: email,
                  keyboardType: TextInputType.emailAddress,
                  autofillHints: const [AutofillHints.email],
                  autocorrect: false,
                  decoration: const InputDecoration(
                    labelText: 'Email address',
                    prefixIcon: Icon(Icons.mail_outline),
                  ),
                  validator: (v) =>
                      RegExp(
                        r'^[^\s@]+@[^\s@]+\.[^\s@]+$',
                      ).hasMatch((v ?? '').trim())
                      ? null
                      : 'Enter a valid email address.',
                ),
                const SizedBox(height: 16),
                TextFormField(
                  controller: password,
                  obscureText: hidden,
                  autocorrect: false,
                  enableSuggestions: false,
                  autofillHints: [
                    widget.signup
                        ? AutofillHints.newPassword
                        : AutofillHints.password,
                  ],
                  decoration: InputDecoration(
                    labelText: 'Password',
                    prefixIcon: const Icon(Icons.lock_outline),
                    suffixIcon: IconButton(
                      tooltip: hidden ? 'Show password' : 'Hide password',
                      onPressed: () => setState(() => hidden = !hidden),
                      icon: Icon(
                        hidden
                            ? Icons.visibility_outlined
                            : Icons.visibility_off_outlined,
                      ),
                    ),
                  ),
                  validator: (v) => widget.signup
                      ? passwordError(v ?? '')
                      : ((v ?? '').isEmpty ? 'Enter your password.' : null),
                  onFieldSubmitted: (_) => busy ? null : submit(),
                ),
                if (widget.signup)
                  const Padding(
                    padding: EdgeInsets.only(top: 12),
                    child: Text(
                      '12+ characters with uppercase, lowercase, a number and a symbol. Avoid your name or email.',
                      style: TextStyle(fontSize: 12, color: muted),
                    ),
                  ),
                if (error != null) Notice(error!, error: true),
                const SizedBox(height: 26),
                FilledButton(
                  onPressed: busy ? null : submit,
                  child: busy
                      ? const SizedBox(
                          width: 22,
                          height: 22,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : Text(widget.signup ? 'Create account' : 'Log in'),
                ),
                const SizedBox(height: 22),
                const Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(Icons.shield_outlined, size: 18, color: green),
                    SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        'Your password is protected. Your conversations belong to you.',
                        style: TextStyle(fontSize: 12, color: muted),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    ),
  );
}
