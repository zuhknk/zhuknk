# LaienTech iOS App Review Analyzer

iOS App Store 评论语义分析与版本规划评估工具。

## 功能

- **自动采集**：输入 App Store 链接，自动获取评论数据（RSS Feed）
- **智能清洗**：去重、噪声过滤、语言检测
- **LLM 语义分析**：AI 驱动的主题发现、情感分析（不依赖硬编码分类）
- **PRD 生成**：基于用户反馈自动生成产品需求文档
- **测试用例**：从需求自动生成可追溯的测试用例
- **校验报告**：确定性 + LLM 双重校验，确保可追溯性

## 技术栈

| 层 | 技术 |
|---|------|
| 后端 | Python 3.10+, FastAPI, asyncio, httpx |
| 前端 | Vue 3, Vite, Pinia |
| AI | OpenAI 兼容 API（GPT-4o-mini 等） |
| 推送 | SSE (Server-Sent Events) |

## 快速开始

### 1. 配置

```bash
cp .env.example .env
# 编辑 .env 填入 LLM API Key（可选，不填则使用统计模式）
```

### 2. 启动

双击 `启动.bat` 即可，或手动启动：

```bash
# 终端 1 — 后端
cd backend
pip install -r requirements.txt
python main.py

# 终端 2 — 前端
cd frontend
npm install
npm run dev
```

浏览器访问 `http://localhost:3000`

### 3. 使用

- 粘贴 App Store 链接 → 点击"开始分析"
- 或切换到"文件导入"模式，上传 JSON/CSV 评论文件
- 等待 8 阶段管道完成，在 Tab 中查看结果

## 项目结构

```
app-review-analyzer/
├── backend/
│   ├── collectors/    # 数据采集（RSS Feed + 文件导入）
│   ├── cleaners/      # 数据清洗（去重 + 噪声过滤）
│   ├── analyzers/     # 语义分析（主题发现 + 证据验证）
│   ├── generators/    # 内容生成（PRD + 测试用例）
│   ├── validators/    # 结果校验（可追溯性 + 一致性）
│   ├── prompts/       # LLM Prompt 模板
│   ├── main.py        # FastAPI 主应用
│   ├── models.py      # 数据模型
│   ├── config.py      # 配置管理
│   └── llm_client.py  # LLM 调用基础设施
├── frontend/
│   └── src/
│       ├── components/  # Vue 组件
│       ├── stores/      # Pinia 状态管理
│       └── assets/      # 样式
├── sample_data/       # 示例数据
├── 启动.bat           # 一键启动脚本
└── .env.example       # 配置模板
```

## 数据限制

- iTunes RSS Feed 最多返回 500 条评论（10 页 × 50 条）
- 仅支持美国 App Store（`country=us`）
- 支持 `mostrecent`（最新）和 `mosthelpful`（最有帮助）两种排序

## API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/health` | GET | 健康检查 |
| `/api/analyze` | POST | 启动分析（SSE 流式返回） |