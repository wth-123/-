# External Deployment

This deployment uses Netlify for the browser UI and Render for the FastAPI API.

## 1. Deploy the API to Render

1. Put this project in a private Git repository and create a Render Blueprint from `render.yaml`.
2. In the Render service environment, set `APP_ACCESS_PASSWORD` to a new shared password.
3. Leave `ALLOWED_ORIGINS` empty until the Netlify production URL exists.
4. Deploy the service and copy its HTTPS URL, for example `https://archive-workbench-api.onrender.com`.

The current app stores uploaded documents and review data on local service storage. Render may clear that storage when the service restarts. Do not use this deployment for records that require durable retention until object storage and a database are added.

## 2. Configure the Netlify UI

Run this locally with the Render API URL:

```powershell
.\.venv\Scripts\python.exe scripts\configure_netlify_api.py https://archive-workbench-api.onrender.com
```

Deploy `app/templates` as the Netlify publish directory. The generated `config.js` is public and contains only the Render URL.

## 3. Restrict the API Origin

After Netlify returns a site URL, set Render `ALLOWED_ORIGINS` to that exact URL, for example:

```text
https://your-site.netlify.app
```

Redeploy the Render service after changing the environment variable.

## 4. Verify

1. Open the Netlify URL.
2. Enter the shared password; it is stored in that browser for seven days.
3. Upload a non-sensitive test CSV, process it, confirm it, and export it.
4. Confirm a request without `X-Access-Password` returns HTTP 401.
