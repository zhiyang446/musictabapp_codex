import 'package:flutter/material.dart';

import 'job_list_page.dart';

/// HomeShell 為主框架頁面，提供底部導覽與作業列表進入點。
class HomeShell extends StatefulWidget {
  /// 路由名稱常數。
  static const String routeName = 'home';

  /// 作業詳情路由名稱常數。
  static const String jobDetailRouteName = 'job-detail';

  /// 建構子。
  const HomeShell({super.key});

  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  /// 目前的底部導覽索引。
  int _currentIndex = 0;

  /// 建立帶有底部導覽的 Scaffold。
  @override
  Widget build(BuildContext context) {
    final pages = <Widget>[
      const JobListPage(),
      const Center(child: Text('通知中心（施工中）')),
      const Center(child: Text('設定（施工中）')),
    ];

    return Scaffold(
      appBar: AppBar(title: const Text('MusicTab')),
      body: AnimatedSwitcher(
        duration: const Duration(milliseconds: 250),
        child: pages[_currentIndex],
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _currentIndex,
        onDestinationSelected: (index) {
          setState(() {
            _currentIndex = index;
          });
        },
        destinations: const [
          NavigationDestination(icon: Icon(Icons.library_music_outlined), label: '作業'),
          NavigationDestination(icon: Icon(Icons.notifications_outlined), label: '通知'),
          NavigationDestination(icon: Icon(Icons.settings_outlined), label: '設定'),
        ],
      ),
    );
  }
}
