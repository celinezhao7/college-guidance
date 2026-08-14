# College Guidance Backend

This folder contains the FastAPI backend. It is deliberately separate from the
existing command-line application under `src/`.

The first backend version is read-only and provides:

- `GET /api/health` — service health check;
- `GET /api/profiles` — selectable student profiles without exposing local paths;
- `GET /api/modes` — available recommendation modes;
- `GET /docs` — FastAPI's interactive API documentation.

It does not modify files under `data/`, rebuild Chroma, or call Qwen.

## Windows setup

From the repository root:

```powershell
py -3.12 -m venv backend\.venv
backend\.venv\Scripts\python.exe -m pip install --upgrade pip
backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

Run the development server:

```powershell
backend\.venv\Scripts\python.exe -m fastapi dev backend\app\main.py
```

Then open:

- API documentation: <http://127.0.0.1:8000/docs>
- Health check: <http://127.0.0.1:8000/api/health>

Stop the server with `Ctrl+C`.

## Separation from the CLI

```text
backend/     FastAPI code and its own dependency file
src/         Existing command-line application
data/        Existing source documents
chroma/      Existing generated indexes
```

The backend reads profile filenames from `data/student_profiles/` but does not
write to that directory. A custom profile directory can be selected with the
existing `STUDENT_PROFILE_DIR` environment variable.
