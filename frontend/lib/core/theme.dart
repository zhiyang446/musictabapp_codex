import 'package:flutter/material.dart';

/// App 主題與色票定義。
class AppTheme {
  /// 提供亮色主題設定。
  static ThemeData lightTheme() {
    return ThemeData(
      colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF5D5FEF)),
      useMaterial3: true,
      visualDensity: VisualDensity.adaptivePlatformDensity,
    );
  }
}
