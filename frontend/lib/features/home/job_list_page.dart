import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// 模擬作業列表資料的 Provider。
final mockJobsProvider = Provider<List<String>>((ref) {
  return const [
    'Demo Job #1',
    'Demo Job #2',
    'Demo Job #3',
  ];
});

/// 作業列表頁面，展示使用者近期提交的轉譜作業。
class JobListPage extends ConsumerWidget {
  /// 建構子。
  const JobListPage({super.key});

  /// 建立列表畫面內容。
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final jobs = ref.watch(mockJobsProvider);

    return ListView.separated(
      padding: const EdgeInsets.all(16),
      itemCount: jobs.length,
      separatorBuilder: (_, __) => const Divider(),
      itemBuilder: (context, index) {
        final jobName = jobs[index];
        return ListTile(
          title: Text(jobName),
          subtitle: const Text('狀態：準備中，點擊查看詳情'),
          onTap: () {},
          trailing: const Icon(Icons.chevron_right),
        );
      },
    );
  }
}
