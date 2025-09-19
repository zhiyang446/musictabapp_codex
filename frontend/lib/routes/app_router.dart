import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../features/home/home_shell.dart';
import '../features/splash/splash_page.dart';

/// 建立全域路由設定的函式。
GoRouter buildAppRouter() {
  return GoRouter(
    debugLogDiagnostics: true,
    initialLocation: '/',
    routes: [
      GoRoute(
        path: '/',
        name: SplashPage.routeName,
        builder: (context, state) => const SplashPage(),
      ),
      GoRoute(
        path: '/jobs',
        name: HomeShell.routeName,
        builder: (context, state) => const HomeShell(),
        routes: [
          GoRoute(
            path: ':jobId',
            name: HomeShell.jobDetailRouteName,
            builder: (context, state) {
              final jobId = state.pathParameters['jobId'] ?? '';
              return JobDetailPlaceholder(jobId: jobId);
            },
          ),
        ],
      ),
    ],
  );
}

/// 簡易的作業詳情占位頁面。
class JobDetailPlaceholder extends StatelessWidget {
  /// 建構子，帶入作業識別碼。
  const JobDetailPlaceholder({super.key, required this.jobId});

  /// 作業識別碼。
  final String jobId;

  /// 建立作業詳情占位畫面。
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('作業詳情：$jobId')),
      body: const Center(child: Text('敬請期待轉譜結果')),
    );
  }
}
