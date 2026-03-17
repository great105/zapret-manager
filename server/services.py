"""
Реестр заблокированных сервисов в России.

bypass_method:
  "dpi"  — блокировка через DPI, zapret2 может обойти
  "ip"   — блокировка по IP, zapret2 НЕ поможет (нужен VPN/прокси)
  "mixed"— DPI + частично IP, zapret2 может помочь частично
"""

BLOCKED_SERVICES = [
    # ── DPI-блокировка / замедление (zapret2 помогает) ────────────────
    {
        "id": "youtube",
        "name": "YouTube",
        "icon": "▶",
        "domains": [
            "youtube.com", "www.youtube.com", "m.youtube.com",
            "youtu.be", "yt.be", "googlevideo.com",
            "ytimg.com", "yt3.ggpht.com", "yt3.googleusercontent.com",
            "youtube-nocookie.com", "youtube-ui.l.google.com",
        ],
        "test_domain": "youtube.com",
        "ports": {"tcp": [443, 80], "udp": [443]},
        "blocking_type": "throttle",
        "bypass_method": "dpi",
        "category": "video",
    },
    {
        "id": "discord",
        "name": "Discord",
        "icon": "💬",
        "domains": [
            "discord.com", "discordapp.com", "discord.gg",
            "discord.media", "discordapp.net", "discord.dev",
            "cdn.discordapp.com", "gateway.discord.gg",
            "media.discordapp.net", "dl.discordapp.net",
            "images-ext-1.discordapp.net", "images-ext-2.discordapp.net",
            "router.discordapp.net", "status.discord.com",
            "update.discord.com", "latency.discord.media",
            "dis.gd", "discord.new", "discord.gift",
        ],
        "test_domain": "discord.com",
        "ports": {"tcp": [443, 80], "udp": [443]},
        "blocking_type": "full",
        "bypass_method": "dpi",
        "category": "messenger",
    },

    # ── IP-блокировка (zapret2 может не помочь) ───────────────────────
    {
        "id": "telegram",
        "name": "Telegram",
        "icon": "📨",
        "domains": [
            "telegram.org", "t.me", "core.telegram.org",
            "web.telegram.org", "desktop.telegram.org",
            "updates.telegram.org", "telegram.me",
        ],
        "test_domain": "telegram.org",
        "ports": {"tcp": [443, 80]},
        "blocking_type": "full",
        "bypass_method": "ip",
        "category": "messenger",
    },
    {
        "id": "facebook",
        "name": "Facebook",
        "icon": "👤",
        "domains": ["facebook.com", "www.facebook.com", "fbcdn.net", "fb.com", "fb.me"],
        "test_domain": "facebook.com",
        "ports": {"tcp": [443, 80]},
        "blocking_type": "full",
        "bypass_method": "ip",
        "category": "social",
    },
    {
        "id": "instagram",
        "name": "Instagram",
        "icon": "📷",
        "domains": ["instagram.com", "www.instagram.com", "cdninstagram.com", "ig.me"],
        "test_domain": "instagram.com",
        "ports": {"tcp": [443, 80]},
        "blocking_type": "full",
        "bypass_method": "ip",
        "category": "social",
    },
    {
        "id": "twitter",
        "name": "X (Twitter)",
        "icon": "𝕏",
        "domains": ["twitter.com", "x.com", "t.co", "twimg.com", "abs.twimg.com"],
        "test_domain": "x.com",
        "ports": {"tcp": [443, 80]},
        "blocking_type": "full",
        "bypass_method": "mixed",
        "category": "social",
    },
    {
        "id": "signal",
        "name": "Signal",
        "icon": "🔒",
        "domains": ["signal.org", "chat.signal.org", "updates.signal.org"],
        "test_domain": "signal.org",
        "ports": {"tcp": [443]},
        "blocking_type": "full",
        "bypass_method": "ip",
        "category": "messenger",
    },
    {
        "id": "viber",
        "name": "Viber",
        "icon": "📱",
        "domains": ["viber.com", "www.viber.com", "dl.viber.com"],
        "test_domain": "viber.com",
        "ports": {"tcp": [443, 80]},
        "blocking_type": "full",
        "bypass_method": "ip",
        "category": "messenger",
    },
    {
        "id": "whatsapp",
        "name": "WhatsApp",
        "icon": "📲",
        "domains": ["whatsapp.com", "web.whatsapp.com", "www.whatsapp.com", "whatsapp.net"],
        "test_domain": "web.whatsapp.com",
        "ports": {"tcp": [443], "udp": [443]},
        "blocking_type": "full",
        "bypass_method": "ip",
        "category": "messenger",
    },
    {
        "id": "linkedin",
        "name": "LinkedIn",
        "icon": "💼",
        "domains": ["linkedin.com", "www.linkedin.com"],
        "test_domain": "linkedin.com",
        "ports": {"tcp": [443, 80]},
        "blocking_type": "full",
        "bypass_method": "ip",
        "category": "social",
    },
    {
        "id": "snapchat",
        "name": "Snapchat",
        "icon": "👻",
        "domains": ["snapchat.com", "www.snapchat.com", "app.snapchat.com"],
        "test_domain": "snapchat.com",
        "ports": {"tcp": [443]},
        "blocking_type": "full",
        "bypass_method": "ip",
        "category": "social",
    },
    {
        "id": "chatgpt",
        "name": "ChatGPT",
        "icon": "🤖",
        "domains": ["chat.openai.com", "openai.com", "api.openai.com", "cdn.oaistatic.com"],
        "test_domain": "chat.openai.com",
        "ports": {"tcp": [443]},
        "blocking_type": "throttle",
        "bypass_method": "dpi",
        "category": "ai",
    },
    {
        "id": "roblox",
        "name": "Roblox",
        "icon": "🎮",
        "domains": ["roblox.com", "www.roblox.com", "rbxcdn.com", "roblox.qq.com"],
        "test_domain": "roblox.com",
        "ports": {"tcp": [443, 80]},
        "blocking_type": "full",
        "bypass_method": "dpi",
        "category": "gaming",
    },
    {
        "id": "twitch",
        "name": "Twitch",
        "icon": "🎥",
        "domains": ["twitch.tv", "www.twitch.tv", "static.twitchcdn.net", "usher.ttvnw.net"],
        "test_domain": "twitch.tv",
        "ports": {"tcp": [443, 80]},
        "blocking_type": "partial",
        "bypass_method": "dpi",
        "category": "video",
    },
    {
        "id": "soundcloud",
        "name": "SoundCloud",
        "icon": "🎵",
        "domains": ["soundcloud.com", "api-v2.soundcloud.com", "sndcdn.com"],
        "test_domain": "soundcloud.com",
        "ports": {"tcp": [443]},
        "blocking_type": "partial",
        "bypass_method": "dpi",
        "category": "media",
    },
]


def get_all_services():
    return BLOCKED_SERVICES

def get_all_domains():
    domains = []
    for svc in BLOCKED_SERVICES:
        domains.extend(svc["domains"])
    return sorted(set(domains))

def get_service_by_id(service_id: str):
    for svc in BLOCKED_SERVICES:
        if svc["id"] == service_id:
            return svc
    return None

def get_dpi_bypassable_services():
    """Сервисы, которые можно обойти через DPI desync."""
    return [s for s in BLOCKED_SERVICES if s["bypass_method"] in ("dpi", "mixed")]
