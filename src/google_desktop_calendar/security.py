from urllib.parse import urlsplit

AUTH_ENDPOINTS = frozenset(
    {
        "https://accounts.google.com/o/oauth2/auth",
        "https://accounts.google.com/o/oauth2/v2/auth",
    }
)
TOKEN_ENDPOINTS = frozenset(
    {
        "https://oauth2.googleapis.com/token",
        "https://accounts.google.com/o/oauth2/token",
    }
)


def trusted_desktop_config(config: dict) -> bool:
    installed = config.get("installed")
    return (
        isinstance(installed, dict)
        and "web" not in config
        and installed.get("auth_uri") in AUTH_ENDPOINTS
        and installed.get("token_uri") in TOKEN_ENDPOINTS
    )


def allowed_url(url: str, *, auth: bool = False) -> bool:
    if any(ord(character) < 32 or ord(character) == 127 for character in url):
        return False
    try:
        parsed = urlsplit(url)
        if (
            parsed.scheme != "https"
            or parsed.username is not None
            or parsed.password is not None
            or parsed.port not in (None, 443)
        ):
            return False
        if auth:
            return f"https://{parsed.netloc}{parsed.path}" in AUTH_ENDPOINTS
        return parsed.hostname in {
            "calendar.google.com",
            "www.google.com",
        } and parsed.path == "/calendar/event"
    except ValueError:
        return False
