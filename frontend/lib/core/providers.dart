import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import 'app_config.dart';

/// 控制 Supabase 初始化僅執行一次的旗標。
class _SupabaseGuard {
  static bool initialized = false;
}

/// 負責初始化 Supabase 的 FutureProvider。
final appBootstrapProvider = FutureProvider<void>((ref) async {
  if (_SupabaseGuard.initialized) {
    return;
  }
  await Supabase.initialize(
    url: AppConfig.supabaseUrl,
    anonKey: AppConfig.supabaseAnonKey,
  );
  _SupabaseGuard.initialized = true;
});

/// 供全域存取 SupabaseClient 的 Provider。
final supabaseClientProvider = Provider<SupabaseClient>((ref) {
  if (!_SupabaseGuard.initialized) {
    throw StateError('Supabase 尚未初始化，請先讀取 appBootstrapProvider。');
  }
  return Supabase.instance.client;
});
