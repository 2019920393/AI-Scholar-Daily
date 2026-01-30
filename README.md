# 📚 AI-Scholar-Daily

> 每日 AI 论文智能推送助手 | 专注于**边缘智能**与 **Transformer** 领域

自动获取 arXiv 最新 AI 论文，利用 LLM 进行智能摘要和相关性评分，每天早晨 8:00 通过 Telegram 推送到你的手机。

## ✨ 核心功能

- 🔍 **智能筛选** - 基于研究关键词自动过滤高相关性论文
- 🤖 **LLM 摘要** - 使用 OpenAI 兼容 API 生成论文摘要和评分
- 📱 **Telegram 推送** - 精美 Markdown 格式，随时随地阅读
- ⚡ **零服务器** - 基于 GitHub Actions，完全免费运行

## 🚀 快速开始

### 1. Fork 本仓库

### 2. 配置 GitHub Secrets

在仓库的 `Settings > Secrets and variables > Actions` 中添加：

| Secret 名称 | 说明 |
|------------|------|
| `LLM_API_KEY` | OpenAI 兼容 API Key (Gemini/DeepSeek) |
| `LLM_BASE_URL` | API Base URL |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token |
| `TELEGRAM_CHAT_ID` | 你的 Telegram Chat ID |

### 3. 启用 GitHub Actions

进入 `Actions` 标签页，点击 "I understand my workflows, go ahead and enable them"

### 4. 手动测试

点击 `Daily AI Scholar` workflow，选择 `Run workflow` 进行测试

## 📁 项目结构

```
AI-Scholar-Daily/
├── .github/workflows/
│   └── daily_run.yml       # 定时任务配置
├── src/
│   ├── config.py           # 配置管理
│   ├── fetcher.py          # 论文获取
│   ├── summarizer.py       # LLM 摘要
│   └── notifier.py         # Telegram 推送
├── .env.example            # 环境变量模板
├── main.py                 # 入口文件
└── requirements.txt        # 依赖列表
```

## ⚙️ 本地开发

```bash
# 克隆仓库
git clone https://github.com/YOUR_USERNAME/AI-Scholar-Daily.git
cd AI-Scholar-Daily

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 填写你的 API Keys

# 运行
python main.py
```

## 🎯 研究关键词

当前配置的核心关键词（可在 `src/config.py` 中修改）：

- **核心领域**: Edge Intelligence, Transformer, Network Optimization
- **相关领域**: Federated Learning, IoT, Mobile Computing, Attention Mechanism

## 📝 推送示例

```
📚 AI-Scholar-Daily | 2026-01-30

---

### 1. EdgeFormer: Efficient Transformer Inference on Edge Devices
👤 作者: Zhang et al.
⭐ 相关度: 9/10
💡 核心贡献: 提出了一种针对边缘设备的 Transformer 推理加速方法
🔗 边缘智能启发: 可用于移动端实时 NLP/CV 任务

---
```

## 📄 License

MIT License

---

**Made with ❤️ for USTC researchers**
