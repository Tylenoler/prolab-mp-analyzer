# ProLab MP Analyzer

公众号数据分析助手 — 开源社区版

> 自带 Key（BYOK），本地运行，数据隐私无忧。
>
> 免费开源，社区驱动。

---

## ✨ 功能

### 数据采集
- ✅ 手动采集公众号文章数据
- ✅ 本地 Web 仪表盘

### 7 项数学模型
- ✅ **R₀ 传播指数** — SIR 模型评估内容扩散潜力
- ✅ **熵 H(X)** — 内容多样性/信息量评估
- ✅ **生存分析（Cox）** — 文章生命周期预测
- ✅ **Prophet 预测** — 粉丝增长趋势预测
- ✅ **DID 因果推断** — 内容策略效果评估
- ✅ **图论内容网络** — 话题关联与内容图谱
- ✅ **HMM 粉丝状态** — 粉丝行为状态建模

---

## 🔄 版本对比

| 功能 | 社区版（免费） | Pro 版（付费） |
|------|:---------:|:-----------:|
| 本地仪表盘 | ✅ | ✅ |
| 7 项数学模型分析 | ✅ | ✅ |
| 手动数据采集 | ✅ | ✅ |
| **定时自动拉取** | ❌ | ✅ |
| **Chrome 插件采集** | ❌ | ✅ |
| **AI 相关阅读 RAG** | ❌ | ✅ |
| **AI 运营报告** | ❌ | ✅ |
| **技术优先支持** | ❌ | ✅ |
| 费用 | 免费（自带 API Key） | ¥39/月 或 ¥299/年 |

> 💡 **升级 Pro**：[https://github.com/Tylenoler/prolab-mp-analyzer-pro](https://github.com/Tylenoler/prolab-mp-analyzer-pro)

---

## 🚀 快速开始

### 前置要求

- Python 3.10+
- DeepSeek API Key

### 安装

```bash
git clone https://github.com/Tylenoler/prolab-mp-analyzer.git
cd prolab-mp-analyzer

python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 配置

```bash
export DEEPSEEK_API_KEY=your_ke...
```

### 启动

```bash
python run.py
```

访问 `http://localhost:8080`

---

## 📁 项目结构

```
prolab-mp-analyzer/
├── src/
│   ├── core/          # 核心逻辑
│   ├── analysis/      # 数学模型分析
│   ├── collector/     # 数据采集模块
│   └── web/           # Web 仪表盘
├── tests/
├── requirements.txt
└── README.md
```

---

## 🤝 贡献

欢迎提交 Issue 和 PR！

---

## 📄 许可

MIT License
