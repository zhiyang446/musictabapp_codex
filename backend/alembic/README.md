# Alembic 遷移說明

- 將 SQLModel 定義同步至 Supabase 資料庫時，請使用 `poetry run alembic revision --autogenerate -m "描述"` 建立版本檔案。
- 遷移前請確認 `.env` 已設定 `SUPABASE_URL`，並與 Supabase 專案資料庫連線字串一致。
- 如果 Supabase 已存在變更，請先透過 `supabase db pull` 匯入 schema 後再執行遷移以避免衝突。
