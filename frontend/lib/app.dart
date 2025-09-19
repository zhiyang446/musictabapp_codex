import 'package:flutter/material.dart';
import 'package:flutter_hooks/flutter_hooks.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'core/theme.dart';
import 'routes/app_router.dart';

/// 應用程式根元件，負責注入主題與路由。
class MusicTabApp extends HookConsumerWidget {
  /// 建構子。
  const MusicTabApp({super.key});

  /// 建立 MaterialApp router 佈局。
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final router = useMemoized(buildAppRouter);
    useListenable(router.routerDelegate);

    return MaterialApp.router(
      title: 'MusicTab',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.lightTheme(),
      routerConfig: router,
    );
  }
}
