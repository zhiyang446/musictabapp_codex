import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:musictab_frontend/app.dart';

void main() {
  testWidgets('首頁載入顯示 MusicTab 標題', (tester) async {
    await tester.pumpWidget(const ProviderScope(child: MusicTabApp()));
    await tester.pumpAndSettle();

    expect(find.text('MusicTab'), findsWidgets);
  });
}
