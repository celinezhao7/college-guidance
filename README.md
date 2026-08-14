# College Guidance

[English](#english) | [简体中文](#简体中文)

## English

An evidence-based college application guidance assistant built with LangChain,
Chroma, Qwen, and the U.S. Department of Education College Scorecard API.

The project uses retrieval-augmented generation (RAG) to ground recommendations
in documented student experiences and official guidance. It supports essay prompt
selection as well as college and field-of-study exploration.

## Features

### 1. UC PIQ recommendation

Recommends four UC Personal Insight Questions using:

- official UC guidance stored in `data/uc_official/`
- documented student experiences stored in `data/student/`
- evidence strength, prompt fit, personal insight, and portfolio diversity

### 2. Common App prompt recommendation

Recommends three Common App essay prompts and identifies the strongest overall
choice using official Common App guidance and retrieved student evidence.

### 3. College and field-of-study matching

Provides three starting paths:

1. Target colleges → recommend relevant reported fields at those colleges
2. Target field → recommend colleges that report related bachelor's fields
3. Unsure about both → recommend fields to explore from student evidence

This feature recommends broad fields of study, not exact university catalog
majors. Students use the results as a starting point and then explore specific
majors, concentrations, and degree names on each university's official website.

College information comes from the College Scorecard API. School-specific fields
of study use four-digit Classification of Instructional Programs (CIP) records
with bachelor's credential level `3`.

The program supports:

- multiple preferred states, such as `CA, MI, MA`
- school-name and abbreviation matching
- fuzzy matching against the official school catalog
- user confirmation when a name is ambiguous
- location, cost, size, and institutional-selectivity preferences
- public, private nonprofit, private for-profit, or unrestricted school-type filtering
- liberal arts college, university, or either format filtering, using College
  Scorecard's Carnegie classification as an approximate category
- verified College Scorecard facts such as overall admission rate, student size,
  cost, completion rate, and reported fields of study
- an English or Simplified Chinese interface and recommendation output, selected
  when the application starts
- a user-selected college recommendation count; if too few supported matches are
  available, the program asks whether to continue with fewer or adjust the filters

## Important limitations

This tool does not predict admission outcomes.

- Overall admission rate is not an individual admission probability.
- A target school preference does not mean the school is an academic match.
- College Scorecard CIP fields are federal reporting categories, not exact
  university catalog majors or concentrations.
- Cost of attendance and average net price are not a student's personal price.
- Program availability, application requirements, deadlines, and current costs
  should always be verified on official university websites.
- External college rankings are not used.

## Project structure

```text
college-guidance/
├── data/
│   ├── common_app_official/   # Common App guidance documents
│   ├── student/               # Student evidence documents
│   └── uc_official/           # UC guidance documents
├── src/
│   ├── build_index.py         # Builds the Chroma vector indexes
│   ├── college_major.py       # College Scorecard and field-matching logic
│   ├── i18n.py                # CLI localization strings and helpers
│   └── recommend.py           # Main command-line application
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

Generated Chroma indexes and the local College Scorecard school catalog cache are
excluded from Git.

## Requirements

- Python 3.10 or newer
- A DashScope-compatible API key for embeddings and chat generation
- A free `api.data.gov` key for College Scorecard queries

## Installation

Open PowerShell in the repository:

```powershell
Set-Location C:\Users\celin\college-guidance
```

Create and activate a virtual environment:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, allow it for the current process only:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Configuration

Copy the example environment file:

```powershell
Copy-Item .env.example .env
```

Add your keys to `.env`:

```env
DASHSCOPE_API_KEY=your_dashscope_api_key
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
QWEN_MODEL=qwen3.5-plus
COLLEGE_SCORECARD_API_KEY=your_data_gov_api_key
COLLEGE_GUIDANCE_DEBUG=false
```

Get a College Scorecard API key from
[api.data.gov](https://api.data.gov/signup/).

Never commit `.env`. It is excluded by `.gitignore`.

## Prepare student evidence

Place `.docx` source files in the appropriate data directories. Documents are
split on the separator:

```text
@@@
```

Student experiences should have stable labels such as:

```text
Experience 2: Computer Science Journey
```

The model is instructed to cite these exact labels and use only documented facts.

## Build the indexes

Run:

```powershell
python src\build_index.py
```

This creates local Chroma collections under `chroma/` for:

- UC official guidance
- Common App official guidance
- student evidence

Index rebuilding is idempotent: each collection is reset and rebuilt using stable
document IDs. Repeated runs do not accumulate duplicate experiences.

Rebuild the indexes whenever source documents change.

## Run the application

```powershell
python src\recommend.py
```

Choose `1` for English or `2` for Simplified Chinese at startup. The selected
language applies to the command-line interface and AI-generated recommendations.
Official school names, source evidence labels, PIQ/prompt numbers, and CIP codes
remain unchanged so that citations can still be checked against their sources.
In the Chinese interface, college names should still be entered in English. Fields
of study may be entered in Chinese or English. Common Chinese fields use built-in
translations; other Chinese entries are translated to an English search term and
shown to the user for confirmation before College Scorecard matching.

Main menu:

```text
1. UC PIQ Recommendation
2. Common App Essay Prompt Recommendation
3. College & Field-of-Study Matching
```

College and Field-of-Study Matching menu:

```text
1. I have target colleges - help me explore related fields
2. I have a target field - help me choose colleges
3. I am unsure about both - recommend fields to explore
```

The first College Scorecard school-name search may download an official school
catalog cache. The cache contains public school identifiers, names, cities, and
states—not user responses.

## Data and privacy

Locally stored data includes:

- source Word documents under `data/`
- generated vector indexes under `chroma/`
- API credentials in `.env`
- an optional generated College Scorecard school catalog cache

Interactive answers such as location, budget, school size, intended field, and
target schools are held in memory during the current run and are not written to a
user-profile file. They are included in prompts sent to the configured Qwen API
when generating recommendations.

The `.env`, virtual environments, Chroma indexes, and generated school catalog
cache are excluded from Git.

## Data sources

- [College Scorecard](https://collegescorecard.ed.gov/data/), U.S. Department of Education
- Official UC guidance documents included in `data/uc_official/`
- Official Common App guidance documents included in `data/common_app_official/`
- User-provided student evidence included in `data/student/`

## Development status

This is a command-line prototype. Recommendations should be treated as structured
research support, not as professional admissions advice or an admission forecast.

---

## 简体中文

这是一个基于证据的大学申请指导助手，使用 LangChain、Chroma、Qwen 和美国教育部 College Scorecard API 构建。

本项目使用检索增强生成（RAG），根据有记录的学生经历和官方指导生成有依据的建议，支持文书题目选择、大学探索和专业探索。

### 功能

#### 1. UC PIQ 推荐

根据以下内容推荐四道 UC Personal Insight Questions（个人洞察问题）：

- `data/uc_official/` 中的 UC 官方指导；
- `data/student/` 中有记录的学生经历；
- 证据强度、题目契合度、个人洞察和整体内容多样性。

#### 2. Common App 主文书题目推荐

根据 Common App 官方指导和检索到的学生经历，推荐三道 Common App 主文书题目，并选出最适合的总体选择。

#### 3. 大学与专业领域匹配

提供三种起点：

1. 已有目标大学 → 推荐这些大学报告的相关本科领域；
2. 已有目标专业领域 → 推荐报告了相关本科领域的大学；
3. 两者都不确定 → 根据学生经历推荐值得探索的领域。

此功能推荐的是宽泛的专业领域，而不是大学课程目录中的确切专业。学生可以把结果作为探索起点，再前往各大学官网了解具体专业、方向和学位名称。

大学信息来自 College Scorecard API。学校特定的专业领域使用四位 Classification of Instructional Programs（CIP）记录，本科学位层级为 `3`。

程序支持：

- 多个偏好州，例如 `CA, MI, MA`；
- 学校名称和英文缩写匹配；
- 根据官方学校目录进行模糊匹配；
- 名称有歧义时要求用户确认；
- 地理位置、费用、学校规模和院校选择性偏好；
- 公立、私立非营利、私立营利或不限的学校性质筛选；
- 文理学院、综合性大学或两者均可的学校类型筛选；该筛选使用 College Scorecard
  中的 Carnegie 分类作为近似类别，并非实时或法定的院校类型认证；
- College Scorecard 中经过验证的整体录取率、学生人数、费用、毕业率和专业领域等信息；
- 启动时选择英文或简体中文界面，并使用所选语言生成推荐结果。
- 由用户决定大学推荐数量；如果有充分数据支持的学校不足，程序会询问是接受较少结果还是调整筛选条件。

### 重要限制

本工具不预测录取结果。

- 学校整体录取率不等于个人录取概率。
- 将某所学校设为目标学校，不表示该校一定与学生的学术背景匹配。
- College Scorecard CIP 字段是联邦统计分类，可能与学校当前目录中的具体专业或方向名称不同。
- 就读成本和平均净价不是某位学生的个人实际费用。
- 专业是否开设、申请要求、截止日期和当前费用必须前往大学官方网站核实。
- 本项目不使用外部大学排名。

### 项目结构

```text
college-guidance/
├── data/
│   ├── common_app_official/   # Common App 官方指导文档
│   ├── student/               # 学生经历文档
│   └── uc_official/           # UC 官方指导文档
├── src/
│   ├── build_index.py         # 构建 Chroma 向量索引
│   ├── college_major.py       # College Scorecard 与专业领域匹配逻辑
│   ├── i18n.py                # 命令行界面本地化文本
│   └── recommend.py           # 主命令行程序
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

生成的 Chroma 索引和本地 College Scorecard 学校目录缓存不会提交到 Git。

### 环境要求

- Python 3.10 或更高版本；
- 用于嵌入和聊天生成的 DashScope 兼容 API 密钥；
- 用于 College Scorecard 查询的免费 `api.data.gov` 密钥。

### 安装

在仓库目录中打开 PowerShell：

```powershell
Set-Location C:\Users\celin\college-guidance
```

创建并激活虚拟环境：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

如果 PowerShell 阻止激活，可仅对当前进程临时放行：

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

安装依赖：

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 配置

复制环境变量示例文件：

```powershell
Copy-Item .env.example .env
```

在 `.env` 中填写密钥：

```env
DASHSCOPE_API_KEY=your_dashscope_api_key
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
QWEN_MODEL=qwen3.5-plus
COLLEGE_SCORECARD_API_KEY=your_data_gov_api_key
COLLEGE_GUIDANCE_DEBUG=false
```

可在 [api.data.gov](https://api.data.gov/signup/) 申请 College Scorecard API 密钥。

请勿提交 `.env`。该文件已被 `.gitignore` 排除。

### 准备学生经历

将 `.docx` 源文件放入相应的数据目录。文档使用以下分隔符切分：

```text
@@@
```

学生经历应使用稳定的标签，例如：

```text
Experience 2: Computer Science Journey
```

模型会按照指令引用这些原始标签，并且只能使用文档中记录的事实。

### 构建索引

运行：

```powershell
python src\build_index.py
```

该命令会在 `chroma/` 下创建以下本地 Chroma 集合：

- UC 官方指导；
- Common App 官方指导；
- 学生经历。

索引重建具有幂等性：每个集合会被重置，并使用稳定的文档 ID 重新构建。重复执行不会累积重复经历。源文档发生变化后应重新构建索引。

### 运行程序

```powershell
python src\recommend.py
```

启动时选择 `1` 使用英文，或选择 `2` 使用简体中文。所选语言会应用到命令行界面和 AI 生成的推荐结果。

中文界面中的大学名称仍应使用英文输入。专业领域可以输入中文或英文；常见中文领域会使用内置对照表转换，其他中文输入会先翻译成英文搜索词并请用户确认，再与 College Scorecard 数据匹配。学校官方名称、证据标签、PIQ/题目编号和 CIP 编码会保留原文，以便核查来源。

主菜单：

```text
1. UC 个人洞察问题（PIQ）推荐
2. Common App 主文书题目推荐
3. 大学与专业领域匹配
```

大学与专业领域匹配菜单：

```text
1. 我有目标大学——帮我探索相关专业领域
2. 我有目标专业领域——帮我选择大学
3. 大学和专业领域都不确定——推荐探索方向
```

第一次搜索学校名称时，程序可能会下载 College Scorecard 官方学校目录缓存。缓存只包含公开的学校 ID、名称、城市和州，不包含用户回答。

### 数据与隐私

本地存储的数据包括：

- `data/` 下的 Word 源文档；
- `chroma/` 下生成的向量索引；
- `.env` 中的 API 凭证；
- 可选生成的 College Scorecard 学校目录缓存。

用户在交互过程中输入的地点、预算、学校规模、意向专业和目标学校等信息，只在当前运行期间保存在内存中，不会写入用户档案文件。生成推荐时，这些信息会包含在发送给所配置 Qwen API 的提示中。

`.env`、虚拟环境、Chroma 索引和生成的学校目录缓存均被排除在 Git 之外。

### 数据来源

- 美国教育部 [College Scorecard](https://collegescorecard.ed.gov/data/)；
- `data/uc_official/` 中的 UC 官方指导文档；
- `data/common_app_official/` 中的 Common App 官方指导文档；
- `data/student/` 中由用户提供的学生经历。

### 开发状态

本项目目前是命令行原型。推荐结果应被视为结构化的研究辅助信息，而不是专业升学建议或录取预测。
