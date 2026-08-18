# College Guidance

[English](#english) | [简体中文](#简体中文)

## English

College Guidance is a bilingual command-line assistant for exploring college
applications. It combines official guidance, documented student experiences,
Qwen, and U.S. Department of Education data.

It can help with three tasks:

1. choose four UC Personal Insight Questions (PIQs);
2. choose three Common App essay prompts;
3. explore colleges and broad undergraduate fields of study.

This project is a research aid. It does not predict admission decisions or replace
official university information.

### What the college tool does

You can start with a target college, a target field, or neither. When recommending
colleges, the program can filter by:

- state;
- maximum annual cost before aid;
- undergraduate size;
- public, private nonprofit, or private for-profit ownership;
- liberal arts college or university format;
- institutional competition, measured by overall admission rate;
- target college or university system;
- requested number of recommendations.

Most filters support multiple selections. Press Enter when the prompt says a
preference is optional or unrestricted.

Fields of study may be entered in English or Chinese. A Chinese entry is converted
to an English search term and shown for confirmation before matching.

Target colleges may also be entered in English or Chinese. The web conversation
flow translates Chinese school names to a likely official English name, then uses
fuzzy matching against the College Scorecard catalog. Common Chinese names use
deterministic aliases first. A match is accepted only when its score and lead over
other candidates are strong enough; otherwise the user is asked to add a campus
identifier or try another form of the name.

### What the results mean

College facts come from the U.S. Department of Education's College Scorecard.
Reported fields are broad federal subject categories, not exact major names from a
university catalog.

For example, a result such as `Computer Science` means the institution reported a
related bachelor's field. It does not confirm a particular concentration,
curriculum, laboratory, or currently available program. Use the result as a
starting point, then check the university's official undergraduate catalog.

Overall admission rate describes the institution. It is not the student's personal
admission probability. Cost data is also an estimate, not an individual financial
aid offer.

### Before you begin

You need:

- Python 3.10 or newer (Python 3.12 is recommended);
- a DashScope API key for Qwen chat and embeddings;
- a free College Scorecard API key from
  [api.data.gov](https://api.data.gov/signup/).

### Quick start on Windows

Open PowerShell in the folder where you want the project, then run:

```powershell
git clone https://github.com/celinezhao7/college-guidance.git
cd college-guidance
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If PowerShell blocks virtual-environment activation, allow it for the current
PowerShell session only:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Create the local configuration file:

```powershell
Copy-Item .env.example .env
```

Open `.env` and add your own keys:

```env
DASHSCOPE_API_KEY=your_dashscope_api_key
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
QWEN_MODEL=qwen3.5-plus
COLLEGE_SCORECARD_API_KEY=your_data_gov_api_key
COLLEGE_GUIDANCE_DEBUG=false
```

Never commit `.env` or share its contents.

Build the local search indexes:

```powershell
python src\build_index.py
```

Then start the application:

```powershell
python src\recommend.py
```

Choose English or Simplified Chinese when the program starts.

### Using your own student evidence

The included Word documents are stored under `data/`:

```text
data/
├── common_app_official/   Common App guidance
├── student_profiles/      Selectable student profiles
└── uc_official/           UC guidance
```

Put each student's evidence in a separate `.docx` file under
`data/student_profiles/`. Run `python src\build_index.py` to index all profiles.
When you run `python src\recommend.py`, select one student by number. Only that
student's evidence is retrieved for the selected recommendation feature.
Separate entries inside each profile with:

```text
@@@
```

Give each experience a stable first-line label, for example:

```text
Experience 2: Computer Science Journey
```

Run `python src\build_index.py` again whenever the source documents change.

### Common questions

#### Why did the program return fewer colleges than requested?

It only keeps colleges supported by the selected filters and a sufficiently close
reported field. If too few remain, the program asks whether to accept fewer results
or revise the conditions.

#### Why was a target college excluded?

A target can conflict with ownership, format, size, cost, location, competition,
or field requirements. The program reports known conflicts instead of silently
calling the target a match.

#### What is the difference between private nonprofit and private for-profit?

Both are privately controlled. A nonprofit institution reinvests its surplus in
the institution; a for-profit institution may distribute profit to owners or
investors. Ownership alone does not determine academic quality. Students should
also examine accreditation, total cost, graduation outcomes, credit transfer, and
professional licensing requirements.

#### Can college names be entered in Chinese?

Yes. The web conversation flow translates Chinese college names before fuzzy
matching them against College Scorecard's official English catalog. English names
and common abbreviations such as `UC` and `UMich` are also supported. If several
campuses have similar names or the match is weak, the program asks for more detail
instead of silently choosing one.

### Data and privacy

- API credentials are stored locally in `.env`.
- Source documents are stored under `data/`.
- Generated Chroma indexes are stored under `chroma/`.
- Interactive answers remain in memory for the current run and are not saved to a
  user-profile file.
- Student context and preferences are sent to the configured Qwen API when a
  recommendation is generated. Chinese college names not covered by a local alias
  may also be sent to Qwen for English-name translation before Scorecard matching.
- `.env`, `.venv`, generated indexes, and the downloaded school catalog cache are
  excluded from Git.

### Project layout

```text
college-guidance/
├── data/                  Source Word documents
├── src/
│   ├── build_index.py     Build local Chroma indexes for all profiles
│   ├── college_major.py   College filtering and field matching
│   ├── i18n.py            English and Chinese interface text
│   └── recommend.py       Application entry point
├── .env.example           Configuration template
├── requirements.txt       Python dependencies
└── README.md
```

### Data sources and limitations

- [College Scorecard](https://collegescorecard.ed.gov/data/), U.S. Department of
  Education;
- official UC guidance under `data/uc_official/`;
- official Common App guidance under `data/common_app_official/`;
- the selected student profile under `data/student_profiles/`.

Always verify current majors, requirements, deadlines, costs, accreditation, and
financial aid on official university websites. External college rankings are not
used.

---

## 简体中文

College Guidance 是一个双语命令行大学申请辅助工具。它结合官方申请指导、已记录的学生经历、Qwen 和美国教育部公开数据，为学生提供有依据的探索建议。

它可以完成三类任务：

1. 推荐四道 UC Personal Insight Questions（PIQ）；
2. 推荐三道 Common App 主文书题目；
3. 探索大学和宽泛的本科专业领域。

本项目是研究辅助工具，不预测录取结果，也不能代替大学官方网站。

### 大学推荐功能可以做什么

用户可以从目标大学、目标专业领域或“两者都不确定”开始。推荐大学时，可以按照以下条件筛选：

- 州；
- 助学金前的最高年度费用；
- 本科生规模；
- 公立、私立非营利或私立营利；
- 文理学院或综合性大学；
- 根据学校整体录取率划分的竞争程度；
- 目标大学或大学系统；
- 希望获得的推荐数量。

多数条件可以多选。提示中注明“不限”或“可选”时，直接按 Enter 即可跳过。

专业领域可以输入中文或英文。中文输入会先转换为英文搜索词，并在匹配前请用户确认。

目标大学同样可以输入中文或英文。Web 对话会先把中文校名转换成可能的英文官方名称，再与 College Scorecard 院校目录进行模糊匹配。常见中文校名优先使用本地确定性映射；只有匹配分数足够高，并且明显优于其他候选学校时，系统才会接受结果。遇到同名、相似分校或低置信度结果时，系统会请用户补充分校信息或换一种写法，而不会直接猜测。

### 如何理解推荐结果

大学数据来自美国教育部 College Scorecard。结果中的专业领域是联邦统计使用的宽泛学科分类，不是大学课程目录中的准确专业名称。

例如，结果显示 `Computer Science`，代表学校报告了相关本科领域，但不保证某个具体专业、细分方向、课程、实验室或项目目前仍在开设。学生应把它作为探索起点，再前往大学官网查看最新本科专业目录。

学校整体录取率只描述学校的选择性，不代表某位学生的个人录取概率。费用数据也是参考值，不是学生最终收到的助学金方案或实际支付价格。

### 开始前需要准备

- Python 3.10 或更高版本，推荐 Python 3.12；
- 用于 Qwen 对话和嵌入模型的 DashScope API 密钥；
- 在 [api.data.gov](https://api.data.gov/signup/) 免费申请的 College Scorecard API 密钥。

### Windows 快速安装

在准备存放项目的文件夹中打开 PowerShell，然后运行：

```powershell
git clone https://github.com/celinezhao7/college-guidance.git
cd college-guidance
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

如果 PowerShell 阻止虚拟环境激活，可以只为当前窗口临时放行：

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

复制配置文件：

```powershell
Copy-Item .env.example .env
```

打开 `.env`，填入自己的密钥：

```env
DASHSCOPE_API_KEY=your_dashscope_api_key
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
QWEN_MODEL=qwen3.5-plus
COLLEGE_SCORECARD_API_KEY=your_data_gov_api_key
COLLEGE_GUIDANCE_DEBUG=false
```

不要提交 `.env`，也不要向他人分享其中内容。

构建本地检索索引：

```powershell
python src\build_index.py
```

运行程序：

```powershell
python src\recommend.py
```

程序启动后可以选择英文或简体中文。

### 使用自己的学生经历

项目中的 Word 文档位于：

```text
data/
├── common_app_official/   Common App 官方指导
├── student_profiles/      可选择的学生档案
└── uc_official/           UC 官方指导
```

请将每名学生的资料分别保存为独立的 `.docx` 文件，并统一放入 `data/student_profiles/`。
运行 `python src\build_index.py` 会为所有档案建立索引；运行 `python src\recommend.py`
时再通过数字选择学生，后续功能只会检索该学生的资料。
每份档案中的不同经历使用以下符号分隔：

```text
@@@
```

每段经历的第一行应使用稳定标签，例如：

```text
Experience 2: Computer Science Journey
```

修改源文档后，需要重新运行 `python src\build_index.py`。

### 常见问题

#### 为什么推荐数量少于我要求的数量？

程序只保留同时满足筛选条件、并具有可靠专业领域匹配的学校。如果数量不足，程序会询问是接受较少结果，还是重新调整条件。

#### 为什么目标大学没有进入结果？

目标大学可能与学校性质、学校类型、规模、费用、位置、竞争程度或专业领域条件冲突。程序会说明已知冲突，而不会直接把目标学校称为合适的匹配。

#### 私立非营利和私立营利有什么区别？

两者都属于私立学校。非营利学校会将盈余继续用于学校运营；营利学校可以向所有者或投资者分配利润。学校性质本身不能直接代表教学质量，学生还应比较认证、总费用、毕业情况、学分转移和职业执照要求。

#### 大学校名可以输入中文吗？

可以。Web 对话会先翻译中文校名，再与 College Scorecard 的英文官方院校目录进行模糊匹配；英文校名以及 `UC`、`UMich` 等常见缩写也仍然支持。如果多个分校名称相似或匹配不够可靠，程序会要求补充信息，而不是直接选择其中一所。

### 数据与隐私

- API 密钥保存在本地 `.env` 文件中；
- 源文档保存在 `data/`；
- 生成的 Chroma 索引保存在 `chroma/`；
- 交互回答只在本次运行期间保存在内存中，不会写入用户档案；
- 生成推荐时，学生背景和偏好会发送给所配置的 Qwen API；未被本地常用名称映射覆盖的中文校名，也可能发送给 Qwen 进行英文名称转换，再用于 Scorecard 匹配；
- `.env`、`.venv`、生成的索引和下载的学校目录缓存不会提交到 Git。

### 项目结构

```text
college-guidance/
├── data/                  Word 源文档
├── src/
│   ├── build_index.py     为全部档案构建本地 Chroma 索引
│   ├── college_major.py   大学筛选与专业领域匹配
│   ├── i18n.py            中英文界面文本
│   └── recommend.py       程序入口
├── .env.example           配置模板
├── requirements.txt       Python 依赖
└── README.md
```

### 数据来源与限制

- 美国教育部 [College Scorecard](https://collegescorecard.ed.gov/data/)；
- `data/uc_official/` 中的 UC 官方指导；
- `data/common_app_official/` 中的 Common App 官方指导；
- `data/student_profiles/` 中当前选定的学生档案。

请始终在大学官方网站核实最新专业、申请要求、截止日期、费用、认证和助学金信息。本项目不使用外部大学排名。
