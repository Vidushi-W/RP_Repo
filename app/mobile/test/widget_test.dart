import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:slsl_connect/core/session.dart';
import 'package:slsl_connect/core/theme.dart';
import 'package:slsl_connect/features/auth/landing_screen.dart';
import 'package:slsl_connect/features/auth/auth_screen.dart';

void main() {
  test('strict password policy rejects weak passwords', () {
    expect(passwordError('password'), isNotNull);
    expect(passwordError('alllowercase123!'), isNotNull);
    expect(passwordError('Strong!Example94'), isNull);
  });
  testWidgets('landing routes to signup and login', (tester) async {
    tester.view.physicalSize = const Size(430, 1000);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    await tester.pumpWidget(
      MaterialApp(
        theme: appTheme,
        home: LandingScreen(session: Session()),
      ),
    );
    await tester.tap(find.text('Get started'));
    await tester.pumpAndSettle();
    expect(find.text('Username'), findsOneWidget);
    expect(find.text('Email address'), findsOneWidget);
    expect(find.text('Create account'), findsOneWidget);
    await tester.tap(find.byTooltip('Back'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Already have an account?  Log in'));
    await tester.pumpAndSettle();
    expect(find.text('Username'), findsNothing);
    expect(find.text('Email address'), findsOneWidget);
  });
}
