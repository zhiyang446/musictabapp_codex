/// 應用程式參數設定，集中管理後端環境資訊。
class AppConfig {
  /// Supabase 專案 URL，請替換為實際環境。
  static const String supabaseUrl = String.fromEnvironment(
    'SUPABASE_URL',
    defaultValue: 'https://yczgtraxpdgqevkazdju.supabase.co',
  );

  /// Supabase 匿名金鑰，僅用於客戶端操作。
  static const String supabaseAnonKey = String.fromEnvironment(
    'SUPABASE_ANON_KEY',
    defaultValue: '用於開發的示意金鑰，請在 build 配置中覆寫',
  );
}
