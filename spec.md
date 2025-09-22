# 音樂轉譜系統規格







## 1. 架構與選型







- 前端：Flutter 3.x 搭配 Riverpod 處理狀態、Dio 處理 REST API、file_picker 與 permission_handler 支援音檔選擇與權限、youtube_explode_dart 解析 YouTube 影片、flutter_downloader 處理譜面下載。







    - 核心套件版本：`flutter_riverpod` 2.5、`go_router` 14、`dio` 5.7、`supabase_flutter` 2.7、`flutter_hooks` 0.20。







- 後端：FastAPI (Python 3.11) 搭配 Pydantic v2、SQLModel 配合 psycopg 驅動管理資料層、Uvicorn/Gunicorn 作為 ASGI 伺服器、Celery + Redis 處理離線運算；作曲模型採用 basic-pitch、Demucs/Spleeter 做音軌分離、music21 生成 MusicXML、mido/pretty_midi 產出 MIDI、MuseScore CLI 或 LilyPond 將 MusicXML 轉為 PDF。







- 儲存：Supabase Storage 儲存原始音檔與產出譜面；Supabase Postgres 儲存作業、資產與事件紀錄。







- 鑑權：Supabase Auth 提供使用者登入註冊，前端持 JWT，FastAPI 透過自訂的 JWKSProvider 快取 Supabase 提供的 JWKS 金鑰 300 秒並驗證令牌；若快取過期會自動重新拉取，任何簽章解析或 aud/iss 驗證失敗皆回應 401 Unauthorized。







- 背景工作：Celery 任務負責音訊下載、轉譜、格式輸出，並以 Webhook/輪詢回報進度。







- 環境變數：後端服務需要設定 SUPABASE_JWKS_URL、SUPABASE_JWT_ISSUER、SUPABASE_JWT_AUDIENCE、SUPABASE_STORAGE_BUCKET、SUPABASE_SERVICE_ROLE_KEY、JOB_SUBMISSION_ACTIVE_LIMIT 等參數；若缺漏 JWKS URL 或 Storage 設定啟動時應立刻失敗。







- 觀測性：結合 OpenTelemetry (OTLP) 與 Supabase Logflare 收集事件，Sentry 監控前後端錯誤。







- 佈署：Docker Compose（本機）與容器化上雲（如 AWS ECS/Fargate），Redis 與 Supabase 分別托管。







- 專案骨架：使用 Poetry 管理依賴，`backend/` 目錄採模組化結構，確保 API 與背景任務可獨立擴充。







    - `backend/app/main.py`：FastAPI 進入點與路由掛載。







    - `backend/app/api/v1/`：REST 路由模組，依資源（jobs、assets、uploads 等）拆檔。







    - `backend/app/services/`：核心業務邏輯層，封裝任務提交、資產管理與通知流程。







    - `backend/app/repositories/`：SQLModel 與 Supabase 查詢封裝，處理交易與錯誤轉換。







    - `backend/app/schemas/`：Pydantic Schema 與回應模型，對應 `api.md` 契約。







    - `backend/app/tasks/`：Celery 任務定義（音訊下載、轉譜、PDF 產生）。







    - `backend/app/models/`：SQLModel 資料表結構定義，供 ORM 與遷移共用。







    - `backend/app/core/`：設定、依賴注入、Supabase/Redis 客戶端、共用常數。







    - `backend/alembic/`：資料表遷移腳本（與 Supabase schema 對齊）。







    - `backend/pyproject.toml`：Poetry 設定與指令入口，統一管理開發命令。







## 2. 資料模型







| 資料表/集合 | 主要欄位 | 描述 |







| --- | --- | --- |







| users (Supabase Auth) | id, email, app_metadata | 使用者基本資料與權限，透過 Supabase 管理。|







| profiles | user_id(FK), display_name, avatar_url, created_at | 額外個人化資料，與 users 一對一。|







| transcription_jobs | id, user_id, source_type(enum: local,youtube), source_uri, storage_object_path, instrument_modes(jsonb), model_profile(enum), status(enum: pending,processing,rendering,completed,failed), progress(float), error_message, created_at, updated_at | 記錄一次轉譜作業及狀態。|







| job_events | id, job_id(FK), stage(enum), message, payload(jsonb), created_at | 作業生命週期事件，用於除錯與前端時間軸；建立複合索引 (job_id, created_at, id) 以支援 SSE 順序查詢。|







| score_assets | id, job_id(FK), instrument(enum), format(enum: midi,musicxml,pdf), storage_object_path, duration_seconds, page_count, created_at | 每個作業產出的檔案資源。|







| processing_metrics | id, job_id(FK), latency_ms, cpu_usage, memory_mb, model_versions(jsonb), created_at | 蒐集性能與版本資訊，用於監控與回溯。|







| presets | id, name, description, instrument_modes(jsonb), tempo_hint, visibility(enum: public,private) | 預設配置，讓使用者快速選擇常用樂器組合。|







* 所有 user_id 外鍵對應 Supabase `auth.users.id` (雲端環境由 Supabase Auth 管理)。







### 資料表欄位與索引規格







- `profiles`







  - 欄位：`user_id UUID`(PK/FK to users.id)、`display_name TEXT`、`avatar_url TEXT`、`created_at TIMESTAMPTZ`







  - 約束：`user_id` 唯一；外鍵採 `ON DELETE CASCADE`







- `transcription_jobs`







  - 欄位：`id UUID`(PK)、`user_id UUID`(FK)、`source_type TEXT CHECK (local|youtube)`、`source_uri TEXT`、`storage_object_path TEXT`、`instrument_modes JSONB`、`model_profile TEXT`、`status TEXT`、`progress REAL DEFAULT 0`、`error_message TEXT`、`created_at TIMESTAMPTZ DEFAULT now()`、`updated_at TIMESTAMPTZ DEFAULT now()`







  - 索引：`user_id`、`status`、`created_at DESC`；具備 `updated_at` 自動更新觸發器







- `job_events`







  - 欄位：`id UUID`(PK)、`job_id UUID`(FK)、`stage TEXT`、`message TEXT`、`payload JSONB`、`created_at TIMESTAMPTZ DEFAULT now()`







  - 索引：`job_id, created_at` 組合索引







- `score_assets`







  - 欄位：`id UUID`(PK)、`job_id UUID`(FK)、`instrument TEXT`、`format TEXT`、`storage_object_path TEXT`、`duration_seconds INT`、`page_count INT`、`created_at TIMESTAMPTZ DEFAULT now()`







  - 約束：對 (`job_id`,`instrument`,`format`) 建立唯一鍵避免重複輸出







- `processing_metrics`







  - 欄位：`id UUID`(PK)、`job_id UUID`(FK)、`latency_ms INT`、`cpu_usage REAL`、`memory_mb REAL`、`model_versions JSONB`、`created_at TIMESTAMPTZ DEFAULT now()`







  - 索引：`job_id`







- `presets`







  - 欄位：`id UUID`(PK)、`user_id UUID NULL`、`name TEXT`、`description TEXT`、`instrument_modes JSONB`、`tempo_hint INT`、`visibility TEXT DEFAULT "private"`







  - 約束：`visibility` ENUM(`public`,`private`)，`user_id` 為 NULL 表示公共預設；`user_id`+`name` 唯一







## 3. 關鍵流程







1. 使用者登入：Flutter 透過 Supabase Auth 登入，儲存 access token，後端在每次 API 呼叫時會解析 Authorization Header，透過 JWKSProvider 快取 Supabase JWKS 並驗證簽章、aud/iss，失敗則立即回傳 401。 







2. 上傳本地音檔：前端先呼叫 POST /v1/uploads/audio 取得簽名上傳資訊，再使用回傳的 uploadUrl 以 HTTP PUT 將音檔寫入 Supabase Storage，最後帶著 storageObjectPath 呼叫 FastAPI 建立作業紀錄。 







3. 提交 YouTube 連結：前端送出連結，後端排入下載任務 (yt-dlp)，完成後轉入音訊處理。 







4. 轉譜流程：Celery 任務依序進行音訊前處理 → 音軌分離 → 音高/節奏偵測 → 樂器分派 → 產出 MIDI/MusicXML → 呼叫 MuseScore CLI 轉出 PDF。 







5. 即時進度：FastAPI SSE 端點輪詢 job_events，初次連線時依 created_at 升冪補齊歷史事件，後續以 1 秒輪詢輸出增量事件，並每 30 秒送出 :keep-alive 心跳維持連線。








6. 成果下載：任務完成後，以 score_assets 紀錄生成檔案位置，前端透過簽名網址下載。 







7. 作業詳情：前端以 GET /v1/jobs/{job_id} 取得單筆作業資訊，服務會驗證作業歸屬於該 user_id；若查無或非本人則統一回傳 404。 







8. 資產瀏覽：前端以 GET /v1/jobs/{job_id}/assets 取得產出資源列表，僅回傳符合使用者與作業的資產，並依 created_at 升冪排序。 







9. 事件查詢：前端以 GET /v1/jobs/{job_id}/events 取得作業生命週期事件，輸出 stage、message、payload、created_at，查無或無權限則返回 404。 







10. 失敗復原：任務失敗時更新狀態與 error_message，提供重新提交或回報。 







11. 即時事件串流: GET /v1/jobs/{job_id}/stream SSE 端點需求:
    - 連線權限：需通過 JWT 驗證，job_id 不存在或不屬於該使用者時回傳 404 JOB_NOT_FOUND。
    - 初次連線：以 created_at 升冪（相同時間再依 id 升冪）回傳所有尚未傳送的 job_events，確保前端補齊歷史事件。
    - Last-Event-ID：若 Header 存在，必須為 UUID 且事件需屬於該 job；格式錯誤或查無事件時回傳 400 INVALID_LAST_EVENT_ID。
    - 續傳查詢：帶入 Last-Event-ID 時需排除該事件本身，created_at 與 id 都必須嚴格大於最後一次輸出的值。
    - 串流資料：每筆輸出三行 id:<uuid>、event:<stage>、data:<json>，其中 json 至少包含 stage、message、payload、createdAt 欄位並以 UTF-8 編碼。
    - 心跳訊號：當輪詢沒有新事件且距離最後輸出達 30 秒時，輸出 :keep-alive 空訊息維持連線。
    - 輪詢頻率：每 1 秒向資料庫查詢新事件，期間需檢查 request.is_disconnected()，為 True 時立即結束生成器。
    - 回應 Header：必須包含 Cache-Control: no-cache、Connection: keep-alive、X-Accel-Buffering: no，避免代理緩衝。
    - 錯誤結構：錯誤回應採通用 ErrorResponse，error.code 可能為 JOB_NOT_FOUND 或 INVALID_LAST_EVENT_ID。

pseudo
function stream_job_events(user, job_id, last_event_id):
    assert user.is_authenticated
    job = require_job(user, job_id)
    checkpoint = resolve_checkpoint(job, last_event_id)
    for event in query_events_after(job, checkpoint):
        yield serialize(event)
    while True:
        if request.is_disconnected():
            break
        events = query_events_after(job, checkpoint)
        if events:
            for event in events:
                checkpoint = (event.created_at, event.id)
                yield serialize(event)
        elif elapsed_since_last_send() >= 30:
            yield ':keep-alive'
        sleep(1)

## 4. 虛擬碼







`pseudo







function submit_job(user, payload):







    assert user.is_authenticated







    job = create_transcription_job(payload)







    enqueue_celery_task('process_job', job.id)







    return job







worker process_job(job_id):







    job = load_job(job_id)







    update_status(job, 'processing')







    audio_path = ensure_audio(job)







    separated_tracks = separate_stems(audio_path)







    midi_tracks = []







    for instrument in job.instrument_modes:







        track_audio = mix_for_instrument(separated_tracks, instrument)







        midi = transcribe_to_midi(track_audio, instrument)







        midi_tracks.append((instrument, midi))







    musicxml_map = render_musicxml(midi_tracks)







    assets = persist_assets(job, midi_tracks, musicxml_map)







    generate_pdfs(assets.musicxml)







    update_status(job, 'completed', assets=assets)







    notify_user(job.user_id, job)







function persist_assets(job, midi_tracks, musicxml_map):







    for (instrument, midi) in midi_tracks:







        path = upload_to_storage(midi)







        create_score_asset(job, instrument, 'midi', path)







    for (instrument, xml) in musicxml_map:







        xml_path = upload_to_storage(xml)







        create_score_asset(job, instrument, 'musicxml', xml_path)







    pdf_paths = render_pdf_from_xml(musicxml_map)







    for (instrument, pdf_path) in pdf_paths:







        create_score_asset(job, instrument, 'pdf', pdf_path)







    return fetch_assets(job.id)







function stream_job_events(user, job_id, last_event_id):

    assert user.is_authenticated

    assert user.owns(job_id)

    if last_event_id:

        anchor = fetch_event(job_id, last_event_id)

        if anchor is None:

            raise InvalidLastEventError

        cursor_created_at = anchor.created_at

        cursor_id = anchor.id

    else:

        cursor_created_at = None

        cursor_id = None

    events = fetch_events(job_id, created_after=cursor_created_at, last_event_id=cursor_id)

    send_sse(events)

    last_sent_monotonic = now_monotonic()

    while client_connected():

        new_events = fetch_events(job_id, created_after=cursor_created_at, last_event_id=cursor_id)

        if new_events:

            for event in new_events:

                cursor_created_at = event.created_at

                cursor_id = event.id

                send_sse([event])

                last_sent_monotonic = now_monotonic()

        elif now_monotonic() - last_sent_monotonic >= 30s:

            send_heartbeat()

            last_sent_monotonic = now_monotonic()

        sleep(1s)







`







## 5. 系統脈絡圖







`mermaid







graph LR







    User((使用者)) -->|操作| FlutterApp[Flutter App]







    FlutterApp -->|REST/WebSocket| FastAPI[(FastAPI API Gateway)]







    FastAPI -->|Auth/Storage API| Supabase[(Supabase 平台)]







    FastAPI -->|推送任務| CeleryWorker[Celery 工作者]







    CeleryWorker -->|讀寫| Supabase







    CeleryWorker -->|緩存| Redis[(Redis 任務佇列)]







    CeleryWorker -->|模型推論| MLModels[(音訊/樂譜模型)]







    User -->|下載成果| Supabase







`







### 背景工作任務架構







- 作業建立：`POST /v1/jobs` 接受 `sourceType`、`instrumentModes` 等參數，預設建立 `pending` 狀態作業並回傳 `JobResource`。







- Celery 啟動參數：`backend/app/core/celery_app.py` 定義 Celery 實例，Broker/Result backend 採 Redis；使用 `CELERY_` 環境變數覆寫。







- 任務流程：`process_transcription_job` 任務負責 orchestrator，呼叫子任務步驟（下載/上傳/轉譜/產出），並透過 `job_events` 紀錄進度。







- 事件推播：任務達成關鍵里程碑時呼叫 `NotificationService.emit_event`；若整合 WebSocket/SSE，可即時更新前端。







- 錯誤與重試：任務採 `autoretry_for` 搭配自訂例外分類，錯誤時更新 `transcription_jobs.status=failed` 並寫入 `error_message`。







- 排程作業：`backend/app/core/celery_beat.py` 保留擴充空間，供定期掃描卡住任務或清理暫存檔。







### 前端初始化概要







- 專案目錄：`frontend/` 採 Flutter 結構，分層為 `lib/core`（共用常數、providers）、`lib/routes`（GoRouter 設定）、`lib/features`（功能模組）與 `lib/widgets`。







- 首批頁面：`SplashPage` 顯示啟動畫面與初始化 Supabase、`AuthGate` 依登入狀態導向、`HomeShell` 提供 Tab Scaffold 與任務列表 placeholder。







- 狀態管理：使用 Riverpod + hooks 封裝 `AppBootstrapProvider`、`SupabaseClientProvider`，共用狀態集中於 `lib/core/providers.dart`。







- 路由策略：使用 `go_router` 定義 `/`（Splash）、`/jobs`（作業列表）、`/jobs/:id`（詳情 placeholder），支援深層連結。







- 主題設定：整合 `ThemeData` 與自訂 `AppColors`，確保暗/亮模式一致性；基礎元件放在 `lib/widgets` 以利重複使用。







- README：`frontend/README.md` 說明開發啟動指令（`flutter pub get`、`flutter run`）與必要工具。







## 6. 容器/部署概觀







`mermaid







graph TD







    subgraph 使用者裝置







        A[Flutter 應用] 







    end







    subgraph 雲端基礎設施







        subgraph 容器叢集







            B[fastapi-app 容器]







            C[celery-worker 容器]







            D[celery-beat 計畫排程]







        end







        E[(Redis 服務)]







        F[(Supabase 托管)]







        G[(物件儲存，用於大檔備援)]







    end







    A --> B







    B --> E







    C --> E







    B --> F







    C --> F







    C --> G







`







## 7. 模組關係圖（Backend / Frontend）







**Backend**







`mermaid







graph TD







    API[路由層]







    Service[服務層]







    Repo[Repository]







    Storage[Storage 客戶端]







    Queue[任務排程]







    ML[音訊/譜面處理模組]







    API --> Service --> Repo --> SupaDB[(Supabase Postgres)]







    Service --> Queue --> Worker[Celery Worker]







    Worker --> ML --> Storage[(Supabase Storage)]







    Worker --> Repo







`







**Frontend**







`mermaid







graph TD







    Router[路由 & Navigator]







    StateManagers[Riverpod Providers]







    Upload[上傳模組]







    JobList[作業清單]







    JobDetail[作業詳情]







    Download[下載模組]







    Auth[認證模組]







    Router --> Auth







    Router --> JobList







    Router --> JobDetail







    StateManagers --> Upload







    StateManagers --> JobList







    StateManagers --> JobDetail







    JobDetail --> Download







`







## 8. 序列圖（YouTube 轉譜流程）







`mermaid







sequenceDiagram







    participant U as 使用者







    participant F as Flutter App







    participant A as FastAPI







    participant Q as Celery Queue







    participant W as Worker







    participant S as Supabase







    U->>F: 提供 YouTube 連結 + 選擇樂器







    F->>A: POST /jobs (payload)







    A->>S: 建立 job 記錄 (status=pending)







    A->>Q: 推入 process_job 任務







    A-->>F: 回傳 job 內容







    W->>S: 取得 job & 更新 status=processing







    W->>YouTube: 下載音訊







    W->>W: 分離音軌/轉譜/生成格式







    W->>S: 上傳檔案、建立 score_assets







    W->>S: 更新 job status=completed







    F->>A: GET /jobs/{id}







    A->>S: 讀取 job + assets







    A-->>F: 回傳完成狀態與下載連結







`







### SSE 即時串流

mermaid
sequenceDiagram
    participant C as 前端客戶端
    participant A as FastAPI
    participant R as JobRepository
    participant DB as Postgres
    C->>A: GET /v1/jobs/{id}/stream (Last-Event-ID?)
    A->>R: 驗證任務擁有權
    R-->>A: 任務存在
    A->>R: 讀取 job_events (依游標)
    R->>DB: SELECT ... ORDER BY created_at, id
    R-->>A: 歷史事件列表
    A-->>C: SSE event:stage + data
    loop 每秒輪詢
        A->>R: list_events_after(cursor)
        alt 新事件
            R-->>A: 事件清單
            A-->>C: SSE event
        else 無事件且 30 秒已達
            A-->>C: :keep-alive
        end
    end


## 9. ER 圖







`mermaid







erDiagram







    USERS ||--o{ PROFILES : 擁有







    USERS ||--o{ TRANSCRIPTION_JOBS : 建立







    TRANSCRIPTION_JOBS ||--o{ JOB_EVENTS : 產生







    TRANSCRIPTION_JOBS ||--o{ SCORE_ASSETS : 生成







    TRANSCRIPTION_JOBS ||--o{ PROCESSING_METRICS : 產出







    USERS ||--o{ PRESETS : 建立







`







## 10. 類別圖（後端關鍵類別）







`mermaid







classDiagram







    class JobService {







        +create_job(data)







        +get_job(id)







        +list_jobs(user)







        +update_status(job, status, meta)







    }







    class AudioIngestor {







        +ensure_audio(job)







        +download_youtube(url)







        +normalize_audio(path)







    }







    class TranscriptionPipeline {







        +separate_stems(path)







        +transcribe(track, instrument)







        +arrange_tracks(midi_tracks)







    }







    class AssetPublisher {







        +save_midi(job, instrument, midi)







        +save_musicxml(job, instrument, xml)







        +render_pdf(xml_path)







        +register_asset(job, metadata)







    }







    class NotificationService {







        +emit_event(job, stage, message)







        +notify_user(job)







    }







    JobService --> AudioIngestor







    JobService --> TranscriptionPipeline







    JobService --> AssetPublisher







    JobService --> NotificationService







`







## 11. 流程圖（作業建立至完成）







`mermaid







flowchart TD







    A[建立作業請求] --> B{來源類型?}







    B -->|本地檔案| C[生成簽名上傳 URL]







    C --> D[上傳完成]







    B -->|YouTube| E[佇列下載任務]







    D --> F[排程 process_job]







    E --> F







    F --> G[音訊前處理]







    G --> H[分離/轉譜]







    H --> I[生成 MIDI/MusicXML]







    I --> J[渲染 PDF]







    J --> K[上傳資產]







    K --> L[更新狀態 completed]







    L --> M[通知使用者]







`







## 12. 狀態圖（Transcription Job）







`mermaid







stateDiagram-v2







    [*] --> pending







    pending --> processing: 任務開始







    processing --> rendering: 格式輸出







    rendering --> completed: 成功







    processing --> failed: 錯誤







    rendering --> failed: 產出失敗







    failed --> pending: 使用者重新提交







    completed --> [*]







`







## 13. 測試計畫







- 單元測試：ackend/tests/test_jobs.py/tests/test_security.py 驗證 Supabase JWT 解析流程，涵蓋成功、缺失 Header、錯誤 kid/sub、多 audience 等情境。







- 作業 API 測試：`backend/tests/test_jobs.py` 覆蓋列表、建立、詳情、資產列表與事件紀錄查詢等情境，包含 404 與空結果檢查。







- 執行方式：使用 poetry run pytest tests 進行整體測試；CI 可整合同指令於 PR 驗證。







- 資料隔離：測試採用 Fake service 取代資料層，確保不依賴實際資料庫或 Supabase。







