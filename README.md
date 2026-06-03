# ProLab MP Analyzer Pro

公众号数据分析助手 — 商业付费版

> 全功能数据采集 · 7 项数学模型 · AI 智能报告 · 定时自动拉取

**让数据驱动你的公众号运营决策。**

---

## ✨ 功能亮点

### 📊 全功能仪表盘
本地 Web 服务 (localhost)，所有数据一目了然

### 📥 智能数据采集
- 自动定时拉取公众号全量文章数据
- Chrome 插件一键采集（商业版独占）
- AI 驱动的相关阅读 RAG 推荐（商业版独占）

### 📈 7 项数学模型分析
| 模型 | 说明 |
|------|------|
| **R₀ 传播指数** | SIR 模型评估内容扩散潜力与传播力 |
| **熵 H(X)** | 内容多样性/信息量度量 |
| **生存分析 (Cox)** | 文章生命周期与衰减预测 |
| **Prophet 预测** | 粉丝增长趋势与关键节点预测 |
| **DID 因果推断** | 内容策略/改版效果量化评估 |
| **图论内容网络** | 话题关联图谱与内容生态分析 |
| **HMM 粉丝状态** | 粉丝行为模式与状态转移建模 |

### 🤖 AI 智能报告
- 自动生成运营周报/月报
- 内容策略优化建议
- 竞品对比分析

---

## 🚀 安装

### 前置要求
- Python 3.10+
- 自备 DeepSeek API Key

### 快速开始

```bash
# 克隆仓库
git clone https://github.com/Tylenoler/prolab-mp-analyzer-pro.git
cd prolab-mp-analyzer-pro

# 安装依赖
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 配置
cp .env.example .env
# 编辑 .env 填入你的 API Key

# 启动
python run.py
```

打开浏览器访问 `http://localhost:8080` 即可。

---

## 📁 项目结构

```
prolab-mp-analyzer-pro/
├── src/
│   ├── core/          # 核心逻辑
│   ├── analysis/      # 数学模型引擎
│   ├── collector/     # 数据采集（含 CDP 自动化）
│   ├── web/           # Web 仪表盘
│   └── pro/           # 商业版独占功能
│       ├── scheduler/ # 定时任务调度
│       ├── rag/       # 相关阅读推荐
│       └── reports/   # AI 报告生成
├── chrome-ext/       # Chrome 插件（商业版）
├── tests/
├── requirements.txt
└── README.md
```

---

## 💳 定价

| 版本 | 价格 | 说明 |
|------|------|------|
| **社区版** | 免费 (BYOK) | 基础功能，自带 API Key |
| **Pro 版** | **¥39/月** 或 **¥299/年** | 全功能 + 定时任务 + AI 报告 |

年付相当于 **一杯咖啡钱用一年** ☕

---

## 🔒 隐私与安全

- 全部数据本地存储，不上传任何第三方
- 仅 DeepSeek API 调用需要网络请求
- 支持离线使用（不含 AI 功能）

---

## 📞 支持

- 提交 Issue：[GitHub Issues](https://github.com/Tylenoler/prolab-mp-analyzer-pro/issues)
- 公众号：普罗工坊 ProLab
