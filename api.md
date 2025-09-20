# 音樂轉譜服務 API 文件

## 認證方式
- 使用 Supabase Auth JWT，於 HTTP Header 加入 Authorization: Bearer <token>。
- 未帶入或無效 JWT 皆回傳 401 Unauthorized，並於回應標頭附加 WWW-Authenticate: Bearer。
- 後端透過 JWKSProvider 從 SUPABASE_JWKS_URL 快取 Supabase JWKS 金鑰 300 秒，依 SUPABASE_JWT_AUDIENCE（預設 authenticated）與 SUPABASE_JWT_ISSUER 驗證 JWT，無法取得或驗證失敗同樣回傳 401。

## Content-Type
- 請求與回應皆為 pplication/json，除非另有說明。

## 共用資料結構
### JobStatus
pending | processing | rendering | completed | failed

### InstrumentIdentifier
drums | bass | piano | guitar | strings | custom:<name>

### JobResource
`json
{
  "id": "uuid",
  "sourceType": "local",
  "sourceUri": "supabase://storage/bucket/object",
  "instrumentModes": ["drums", "guitar"],
  "modelProfile": "balanced",
  "status": "processing",
  "progress": 42.3,
  "errorMessage": null,
  "createdAt": "2024-05-01T12:00:00Z",
  "updatedAt": "2024-05-01T12:05:00Z"
}
`

### ScoreAssetResource
`json
{
  "id": "uuid",
  "jobId": "uuid",
  "instrument": "drums",
  "format": "pdf",
  "downloadUrl": "https://storage.supabase.co/...",
  "durationSeconds": 210,
  "pageCount": 4,
  "createdAt": "2024-05-01T12:10:00Z"
}
`

### ErrorResponse
`json
{
  "error": {
    "code": "JOB_NOT_FOUND",
    "message": "找不到指定作業"
  }
}
`

## 上傳相關 API
### POST /v1/uploads/audio
取得 Supabase 簽名網址，供前端直接上傳本地音檔。

**Request Body**
`json
{
  "fileName": "demo.wav",
  "mimeType": "audio/wav",
  "fileSize": 5242880
}
`

**Responses**
- 201 Created
`json
{
  "uploadUrl": "https://storage.supabase.co/...",
  "method": "PUT",
  "headers": {
    "Content-Type": "audio/wav"
  },
  "expiresAt": "2024-05-01T12:15:00Z",
  "storageObjectPath": "user-uuid/audio/demo.wav"
}
`
- 400 Bad Request：檔案過大或副檔名不允許。

## 作業管理 API
### POST /v1/jobs
建立新的轉譜作業。

**Request Body**
`json
{
  "sourceType": "local",
  "storageObjectPath": "user-uuid/audio/demo.wav",
  "youtubeUrl": null,
  "instrumentModes": ["drums", "bass", "piano"],
  "modelProfile": "balanced",
  "tempoHint": 120,
  "timeSignature": "4/4"
}
`
- sourceType = local 時必填 storageObjectPath
- sourceType = youtube 時必填 youtubeUrl

**Responses**
- 201 Created → JobResource
- 400 Bad Request → ErrorResponse
- 423 Locked：使用者有正在處理的高負載作業，須等待。

### GET /v1/jobs
列出登入使用者的作業。

**Query 參數**
- status (optional) 過濾狀態
- limit offset

**Responses**
- 200 OK
`json
{
  "data": [JobResource],
  "total": 25
}
`

### GET /v1/jobs/{jobId}
取得單一作業。
- 200 OK → JobResource
- 404 Not Found → ErrorResponse（作業不存在或不屬於請求者）

### GET /v1/jobs/{jobId}/assets
取得作業產出資源清單。
- 200 OK
`json
{
  "data": [ScoreAssetResource]
}
`
- 404 Not Found → ErrorResponse（作業不存在或不屬於請求者）

### GET /v1/jobs/{jobId}/events
依時間序列回傳事件紀錄。
- 200 OK
`json
{
  "data": [
    {
      "stage": "audio_ingest",
      "message": "開始下載音訊",
      "payload": {"source": "youtube"},
      "createdAt": "2024-05-01T12:00:05Z"
    }
  ]
}
`

### GET /v1/jobs/{jobId}/stream
建立 Server-Sent Events 連線，持續推送作業事件。
- Response 	ext/event-stream
- 事件格式：event:<stage>\ndata:<json>\n\n

### POST /v1/jobs/{jobId}/retry
重送失敗作業。
- 202 Accepted → JobResource
- 409 Conflict：作業非 failed 狀態。

### DELETE /v1/jobs/{jobId}
刪除作業及相關資產（背景執行）。
- 202 Accepted
- 404 Not Found

## 譜面資產下載 API
### GET /v1/assets/{assetId}/download
產生一次性下載連結。
- 302 Redirect：Location 指向 Supabase 簽名 URL
- 404 Not Found

## 系統資訊 API
### GET /v1/presets
取得公開的樂器配置。
- 200 OK
`json
{
  "data": [
    {
      "id": "uuid",
      "name": "Band Trio",
      "instrumentModes": ["drums", "bass", "guitar"],
      "tempoHint": null
    }
  ]
}
`

### GET /v1/system/health
系統健康狀態，用於監控。
- 200 OK
`json
{
  "status": "ok",
  "version": "1.0.0",
  "revision": "git-sha",
  "dependencies": {
    "supabase": "ok",
    "redis": "ok",
    "worker": "ok"
  }
}
`

## 錯誤碼列表
| 代碼 | 說明 |
| --- | --- |
| UNAUTHORIZED | Authorization Header 缺失或 JWT 驗證失敗 |
| VALIDATION_ERROR | 請求參數有誤 |
| JOB_NOT_FOUND | 找不到作業 |
| ASSET_NOT_FOUND | 找不到資產 |
| UPLOAD_LIMIT_EXCEEDED | 超出上傳限制 |
| WORKER_UNAVAILABLE | 背景工作無法取得 |
| RATE_LIMITED | 使用者觸發節流 |
