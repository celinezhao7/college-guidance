# Limited Render Demo Deployment

This configuration deploys the React frontend and FastAPI backend as one Docker
web service. It is intended for a limited demo, not a production launch.

## Privacy boundary

The Docker image includes the read-only UC and Common App guidance indexes plus
three synthetic, de-identified demo student profiles and their student index.
Never replace these demo files with real student records in a public deployment.

Do not commit `.env`. Configure secrets in Render instead.

## Before pushing

1. Rebuild the read-only guidance indexes after changing their source documents:

   ```powershell
   python src\build_index.py
   ```

2. Confirm `chroma/uc`, `chroma/common_app`, `chroma/student`, the three
   synthetic files in `data/student_profiles`, and
   `data/scorecard_school_catalog.json` are included in the deployment commit.
3. Run local checks:

   ```powershell
   cd frontend
   npm ci
   npm run build
   npm run lint
   ```

## Render setup

1. Push the deployment commit to a private GitHub repository.
2. In Render, choose **New → Blueprint** and connect the repository.
3. Render reads `render.yaml` and creates `college-guidance-demo`.
4. Enter these secret values when prompted:
   - `DASHSCOPE_API_KEY`
   - `COLLEGE_SCORECARD_API_KEY`
5. Deploy and verify:
   - `/api/health` returns `{"status":"ok", ...}`;
   - `/` loads the React interface;
   - each of the three college/field scenarios completes;
   - UC and Common App recommendations stream correctly.

## Expected free-tier limitations

- The service sleeps after inactivity, so the first request can be slow.
- In-memory conversations reset after restarts and deployments.
- Runtime caches reset after restarts.
- The bundled UC and Common App Chroma indexes are read-only deployment data.
- The bundled student profiles are synthetic demo data, not real records.

Do not enable student uploads in this demo architecture.
