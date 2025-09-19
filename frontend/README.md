# MusicTab Flutter 前端

此專案為 MusicTab 平台的 Flutter 客戶端骨架，提供登入引導、作業清單與下載入口的基礎框架。

## 開發環境需求
- Flutter SDK 3.22 以上
- Dart 3.3 以上
- 已安裝 fvm（建議）以及 `flutterfire` CLI（若要整合 Firebase Messaging）

## 安裝與啟動
```bash
flutter pub get
flutter run
```
如需指定模擬器或實機，可加入 `-d` 參數。

## 結構示意
```
lib/
  core/         # 共用常數、Provider 以及初始化流程
  routes/       # GoRouter 設定
  features/
    splash/     # 啟動畫面與初始化流程
    home/       # 作業清單與主頁骨架
  widgets/      # 共用元件（Logo、按鈕等等）
```

## 設定 Supabase
請在 `lib/core/app_config.dart` 填入 `SUPABASE_URL` 與 `SUPABASE_ANON_KEY`，或改為使用 `flutter_dotenv` 從環境變數載入。

## 測試
```bash
flutter test
```
目前提供 Home 頁面的 Widget smoke test，可依需求擴充。
