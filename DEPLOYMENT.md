# F&C Packaging Load Map Deployment

## Streamlit Community Cloud

1. Push this folder to a GitHub repository.
2. In Streamlit Community Cloud, create a new app from that repository.
3. Set the main file path to `app.py`.
4. Add secrets/environment variables in Streamlit's app settings.

Required for login:

```toml
APP_USERNAME = "your_username"
APP_PASSWORD = "your_password"
SETTINGS_PASSWORD = "your_settings_password"
```

Optional integrations:

```toml
MAPBOX_ACCESS_TOKEN = "your_mapbox_token"
MOMENTUM_API_BASE_URL = "https://api.momentumiot.com"
MOMENTUM_EMAIL = "your_momentum_email"
MOMENTUM_PASSWORD = "your_momentum_password"
SUPABASE_URL = "https://your-project-ref.supabase.co"
SUPABASE_SERVICE_ROLE_KEY = "your_service_role_key"
SUPABASE_STORAGE_BUCKET = "fcoperations"
WHATSAPP_EMBED_URL = "optional_working_iframe_source_url"
```

## Notes

- Do not commit `.streamlit/secrets.toml`.
- Uploaded files are session-based until Supabase is configured. With Supabase secrets set, pay sheets and knowledge files are saved to Supabase Storage.
- The app does not require an AI API key. It only needs one later if AI summarization or document reasoning is added.
