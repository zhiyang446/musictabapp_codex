# 後端 AGENT 作業指南

## 使命與範疇
- 維護 FastAPI + Supabase + Celery 後端服務的 API、任務排程、模型推論與資產管理。
- 確保 spec.md、pi.md 更新同步，並帶動背景任務、儲存層與監控機制的演進。

## 日常流程
1. **情境同步**：閱讀 	odolist.md、spec.md、pi.md 與 ackend/AGENTS.md，釐清需求與限制。
2. **規格補強**：任何行為（含重構）先於 spec.md／pi.md 更新影響範圍，確認資料模型與端點敘述完整。
3. **任務拆解**：於 	odolist.md 建立可獨立開發的子任務，標記狀態並在進出任務時更新。
4. **實作節奏**：
   - 建立/更新 FastAPI 路由、Pydantic Schema、Service、Repository。
   - Celery 任務需具備重試、錯誤處理與進度事件推送。
   - 與 Supabase 溝通時採用官方 SDK 或 REST，確保權限與儲存 Bucket 正確。
5. **測試策略**：
   - 單元測試：pytest + pytest-asyncio 覆蓋 service、repository。
   - 整合測試：使用 TestClient 模擬 API 呼叫，對外部資源以 mock/fake 取代。
   - 背景任務：以 Celery 單元測試或 worker stub 驗證流程，撰寫對進度事件的斷言。
6. **品質守則**：
   - 函式層級中文註解、重要變數加註用途。
   - 保持非同步路由 async 定義；IO-bound 服務採 await。
   - 例外統一轉換為 HTTPException 或自定義錯誤碼。
7. **驗證與交付**：
   - 手動執行重點 API（如建立作業、查詢資產）。
   - 測試通過後在 PR 描述更新重點、測試指令與相關規格連結。

## 溝通與交接
- 重大改動（資料表、工作流）需同步前端 AGENT 以利 UI 調整。
- 背景任務新增事件時更新事件列表文件，並通知監控團隊檢查告警規則。

## 常見指令與資源
- 啟動本地 API：uvicorn app.main:app --reload
- 執行測試：pytest
- 啟動 Celery Worker：celery -A app.worker worker -l info
- 啟動 Celery Beat：celery -A app.worker beat -l info
- 觀測：整合 OTLP 或 Sentry DSN 需設定於 .env 並在 spec.md 追蹤。

## 風險管理
- YouTube 下載風險：監控 yt-dlp 版本與 YouTube API 變動。
- 大檔處理：使用暫存資料夾與串流上傳避免記憶體爆量。
- 模型版本：於 processing_metrics 紀錄版本，方便回溯輸出差異。

## 升級守則
- 依賴升級需先於 spec.md 更新版本策略與回滾方案。
- 佈署前需在 staging 跑完整流程（local upload + youtube link）。