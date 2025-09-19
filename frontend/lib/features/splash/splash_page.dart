import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/providers.dart';
import '../../routes/app_router.dart';

/// 啟動畫面，展示 Logo 並進行初始化流程。
class SplashPage extends ConsumerWidget {
  /// 路由名稱常數。
  static const String routeName = 'splash';

  /// 建構子。
  const SplashPage({super.key});

  /// 建立啟動畫面內容。
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final bootstrap = ref.watch(appBootstrapProvider);

    ref.listen(appBootstrapProvider, (previous, next) {
      next.whenData((_) {
        if (context.mounted) {
          context.goNamed(HomeShell.routeName);
        }
      });
    });

    return Scaffold(
      body: Center(
        child: bootstrap.when(
          data: (_) => const CircularProgressIndicator(),
          loading: () => const CircularProgressIndicator(),
          error: (error, stackTrace) => Text('初始化失敗：$error'),
        ),
      ),
    );
  }
}
