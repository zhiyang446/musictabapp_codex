# 前端 AGENT 作業指南

## 使命與範疇
- 使用 Flutter 建構跨平台（iOS/Android/Web）介面，串接後端 API 與 Supabase 服務。
- 覆蓋登入、音檔上傳、作業追蹤、譜面下載與通知等互動。

## 日常流程
1. **情境同步**：檢視 	odolist.md、spec.md、pi.md、rontend/AGENTS.md，確認需求與依賴。
2. **規格對齊**：功能調整前，與後端確認 API 契約，必要時協作更新 spec.md、pi.md。
3. **任務拆解**：將 UI/狀態/網路任務切分為獨立工作（例如：YouTube 任務建立頁、作業列表 Provider、下載模組）。
4. **開發節奏**：
   - State 使用 Riverpod，將純邏輯與 Widget 分離。
   - REST 呼叫統一由 Dio + 攔截器處理，管理 token 更新與錯誤提示。
   - 上傳音檔採用 file_picker + Supabase 簽名網址直傳流程。
   - 下載檔案整合 flutter_downloader，需處理權限申請與背景下載 UI。
   - SSE/WebSocket 事件以 stream provider 收斂，更新進度條與事件時間軸。
5. **UI/UX 守則**：
   - 採響應式布局（LayoutBuilder、Flex），確保平板/桌機體驗。
   - 錯誤訊息以繁體中文呈現，並提供重試按鈕。
   - 進度條、事件列表要依照 job_events 順序轉換。
6. **測試策略**：
   - Widget 測試：使用 lutter_test 驗證關鍵畫面行為。
   - Provider 測試：以 iverpod_test 驗證狀態轉移與錯誤處理。
   - 整合測試：lutter drive 或 integration_test 覆蓋主流程（登入→建立作業→觀察進度→下載）。
7. **品質守則**：
   - 函式層級中文註解說明用途；重要 Provider/Model 加註資料來源。
   - 共用元件集中於 lib/widgets、lib/features 分層；禁止在 UI 中直接呼叫 REST。
   - 所有第三方套件版本需登記於 pubspec.yaml 並在變更時於 spec.md 備註。
8. **驗證與交付**：
   - 開發完成執行 lutter analyze、lutter test。
   - 功能示範錄製短影片或擷取截圖，於 PR 附上。

## 溝通與交接
- 新增/調整 API 呼叫需於 PR 描述列出依賴後端的端點與參數。
- 大型 UI/資訊架構調整應先製作低保真 wireframe 與後端、產品復核。

## 常見指令與資源
- 依賴管理：lutter pub get
- 靜態檢查：lutter analyze
- 單元/Widget 測試：lutter test
- 建置測試版：lutter build apk --debug
- Supabase 用戶端：透過 supabase_flutter 管理解構與存取控制。

## 風險管理
- 行動裝置儲存權限：於 Android 33+ 使用 MediaStore 方案避免被拒。
- 大檔上傳：顯示進度與取消按鈕，失敗紀錄於本地並支援重試。
- 多平台相容性：Web 需 fallback 至 http 下載並提示使用者手動儲存。

## 升級守則
- Flutter/Dart 升級需先檢視套件支援度並更新在 spec.md。
- 發版前至少在 Android（實體或模擬器）與 Web（Chrome）進行冒煙測試，記錄結果。