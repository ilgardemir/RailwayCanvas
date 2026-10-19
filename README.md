# Canvas Dashboard — Railway Edition

This is a password-protected Flask dashboard for **your own** Canvas LMS assignments.

## Railway setup

1. Revoke the Canvas token you previously shared and generate a fresh token (if Canvas permits it).
2. Create a **private** GitHub repository containing `app.py`, `requirements.txt`, `Procfile`, and `templates/index.html`.
3. In Railway select **New Project → Deploy from GitHub repo** and choose the repository.
4. In the Railway service's **Variables** tab, set these four values:

   - `CANVAS_BASE_URL`: e.g. `https://school.instructure.com` (use your actual Canvas address)
   - `CANVAS_TOKEN`: your **new** Canvas API token
   - `DASHBOARD_USERNAME`: a login name you choose
   - `DASHBOARD_PASSWORD`: a long, unique password you choose

5. Deploy. Railway reads `Procfile` and starts Gunicorn listening on `$PORT`.
6. Under service **Settings → Networking**, generate a public domain. Use **HTTPS** only. The browser will prompt for the dashboard username and password.

Do not commit any token or password to your repository. The root page and `/api/dashboard` are protected with HTTP Basic authentication. Avoid sharing your dashboard password; its API response includes private school information. Tokens may expire and need renewal. Treat Railway service logs and environment variable access as sensitive.

## Important scheduled-task limitation

Hosting on Railway **does not automatically grant a ChatGPT Scheduled task access** to the private `/api/dashboard` endpoint. ChatGPT tasks may not support arbitrary authenticated websites or custom headers. For automated briefings, consider a separate Railway scheduled job that retrieves Canvas data and sends a digest through an authorized delivery channel, or use a supported connected app. Do not make the endpoint public just to allow a bot to fetch it.

## Local development

Install with `python -m pip install -r requirements.txt` and set the above four environment variables, then run `python app.py`. Browse to http://127.0.0.1:5000.
