# College Guidance

An evidence-based college application guidance assistant built with LangChain,
Chroma, Qwen, and the U.S. Department of Education College Scorecard API.

The project uses retrieval-augmented generation (RAG) to ground recommendations
in documented student experiences and official guidance. It supports essay prompt
selection as well as college and major exploration.

## Features

### 1. UC PIQ recommendation

Recommends four UC Personal Insight Questions using:

- official UC guidance stored in `data/uc_official/`
- documented student experiences stored in `data/student/`
- evidence strength, prompt fit, personal insight, and portfolio diversity

### 2. Common App prompt recommendation

Recommends three Common App essay prompts and identifies the strongest overall
choice using official Common App guidance and retrieved student evidence.

### 3. College and major matching

Provides three starting paths:

1. Target colleges → recommend relevant fields of study at those colleges
2. Target major → recommend colleges that report related bachelor's fields
3. Unsure about both → recommend major directions from student evidence

College information comes from the College Scorecard API. School-specific fields
of study use four-digit Classification of Instructional Programs (CIP) records
with bachelor's credential level `3`.

The program supports:

- multiple preferred states, such as `CA, MI, MA`
- school-name and abbreviation matching
- fuzzy matching against the official school catalog
- user confirmation when a name is ambiguous
- location, cost, size, and institutional-selectivity preferences
- verified College Scorecard facts such as overall admission rate, student size,
  cost, completion rate, and reported fields of study
- an English or Simplified Chinese interface and recommendation output, selected
  when the application starts

## Important limitations

This tool does not predict admission outcomes.

- Overall admission rate is not an individual admission probability.
- A target school preference does not mean the school is an academic match.
- College Scorecard CIP fields are federal reporting categories and may not match
  the exact current major or concentration name in a university catalog.
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
│   ├── college_major.py       # College Scorecard and major-matching logic
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
In the Chinese interface, enter college and major names in English (for example,
`University of Michigan` and `Computer Science`) for the most reliable matching
against the English-language College Scorecard catalog.

Main menu:

```text
1. UC PIQ Recommendation
2. Common App Essay Prompt Recommendation
3. College & Major Matching
```

College and Major Matching menu:

```text
1. I have target colleges - help me choose majors
2. I have a target major - help me choose colleges
3. I am unsure about both - recommend major directions
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

Interactive answers such as location, budget, school size, intended major, and
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
