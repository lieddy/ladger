# 房产记账工具 — 持久化说明

当你把本项目发布到 Streamlit Cloud（streamlit.io）时，请注意平台的文件系统是短暂（ephemeral）的：

- 应用写入到容器内的本地文件（例如 `user_data/xxx.json`）在应用重启、部署或容器回收后会丢失。

本仓库现在的行为：

- 默认会把用户数据保存为 `user_data/{username}.json`（本地回退方案）。
- 我在代码中添加了可选的远程持久化支持（使用 Supabase）。当你在 Streamlit Secrets 中配置 `SUPABASE_URL` 与 `SUPABASE_KEY` 并安装依赖后，应用会优先把数据存取到 Supabase 的 `ledgers` 表（请自行在 Supabase 控制台创建表）。

推荐方案（从易到难）：

1. Supabase（推荐）
   - 创建一个 Supabase 项目并在 SQL Editor 中创建一个表，例如：

```sql
create table ledgers (
  username text primary key,
  data jsonb
);
```

   - 在 Streamlit Cloud 的设置 -> Secrets 中添加：

```
SUPABASE_URL = "https://your-project.supabase.co"
SUPABASE_KEY = "public-or-service-role-key"
```

   - 部署前确保 `requirements.txt` 中有 `supabase`，或在 Streamlit 的依赖设置里添加。

2. Google Sheets / Airtable / S3 / 外部数据库
   - 这些也是可行方案，但需要不同的凭据和额外配置。

如果不想使用远程服务：

- 本地开发时仍会用 `user_data/` 中的 JSON 文件，但部署到 Streamlit Cloud 时这些文件不会跨重启保留。

代码变更说明

- `real_estate_ledger.py`：增加了可选的 Supabase 支持。如果在 `st.secrets` 中配置了 `SUPABASE_URL` 与 `SUPABASE_KEY`，应用会尝试使用 Supabase（表 `ledgers`）进行 load / upsert；否则会回退使用本地 JSON 文件。

小结

- 若要在 streamlit.io 上保持数据，请配置一个外部持久化（我推荐 Supabase）。我已经把示例代码和说明放在仓库里；如果你希望我为 Airtable/Google Sheets/GitHub Gist 编写示例实现，我可以继续实现并将其集成为可选后端。
