"""
Реестр заблокированных сервисов в России.
Каждый сервис содержит домены для проверки, порты и тип ожидаемой блокировки.
"""

BLOCKED_SERVICES = [
    # === Полная блокировка ===
    {
        "id": "discord",
        "name": "Discord",
        "icon": "💬",
        "domains": [
            "discord.com", "discordapp.com", "discord.gg", "discord.media",
            "cdn.discordapp.com", "gateway.discord.gg", "media.discordapp.net",
            "dl.discordapp.net", "images-ext-1.discordapp.net",
            "images-ext-2.discordapp.net", "static.cloudflareinsights.com",
            "status.discord.com", "router.discordapp.net",
            "latency.discord.media", "update.discord.com",
        ],
        "test_domain": "discord.com",
        "ports": {"tcp": [443, 80], "udp": [443]},
        "blocking_type": "full",
        "category": "messenger",
    },
    {
        "id": "youtube",
        "name": "YouTube",
        "icon": "▶",
        "domains": [
            "youtube.com", "www.youtube.com", "m.youtube.com",
            "googlevideo.com", "ytimg.com", "yt3.ggpht.com",
            "youtu.be", "yt.be",
        ],
        "test_domain": "youtube.com",
        "ports": {"tcp": [443, 80], "udp": [443]},
        "blocking_type": "throttle",
        "category": "video",
    },
    {
        "id": "facebook",
        "name": "Facebook",
        "icon": "👤",
        "domains": ["facebook.com", "www.facebook.com", "fbcdn.net", "fb.com"],
        "test_domain": "facebook.com",
        "ports": {"tcp": [443, 80]},
        "blocking_type": "full",
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
        "category": "social",
    },
    {
        "id": "telegram_calls",
        "name": "Telegram (звонки)",
        "icon": "📞",
        "domains": ["telegram.org", "t.me", "core.telegram.org"],
        "test_domain": "telegram.org",
        "ports": {"tcp": [443, 80], "udp": [443]},
        "blocking_type": "partial",
        "category": "messenger",
    },
    {
        "id": "signal",
        "name": "Signal",
        "icon": "🔒",
        "domains": ["signal.org", "chat.signal.org", "updates.signal.org"],
        "test_domain": "signal.org",
        "ports": {"tcp": [443]},
        "blocking_type": "full",
        "category": "messenger",
    },
    {
        "id": "viber",
        "name": "Viber",
        "icon": "📱",
        "domains": ["viber.com", "www.viber.com"],
        "test_domain": "viber.com",
        "ports": {"tcp": [443, 80]},
        "blocking_type": "full",
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
        "category": "social",
    },
    {
        "id": "whatsapp_calls",
        "name": "WhatsApp (звонки)",
        "icon": "📲",
        "domains": ["whatsapp.com", "web.whatsapp.com", "www.whatsapp.com"],
        "test_domain": "web.whatsapp.com",
        "ports": {"tcp": [443], "udp": [443]},
        "blocking_type": "partial",
        "category": "messenger",
    },
    {
        "id": "chatgpt",
        "name": "ChatGPT",
        "icon": "🤖",
        "domains": ["chat.openai.com", "openai.com", "api.openai.com"],
        "test_domain": "chat.openai.com",
        "ports": {"tcp": [443]},
        "blocking_type": "throttle",
        "category": "ai",
    },
    {
        "id": "roblox",
        "name": "Roblox",
        "icon": "🎮",
        "domains": ["roblox.com", "www.roblox.com", "rbxcdn.com"],
        "test_domain": "roblox.com",
        "ports": {"tcp": [443, 80]},
        "blocking_type": "full",
        "category": "gaming",
    },
    {
        "id": "twitch",
        "name": "Twitch",
        "icon": "🎥",
        "domains": ["twitch.tv", "www.twitch.tv", "static.twitchcdn.net"],
        "test_domain": "twitch.tv",
        "ports": {"tcp": [443, 80]},
        "blocking_type": "partial",
        "category": "video",
    },
    {
        "id": "soundcloud",
        "name": "SoundCloud",
        "icon": "🎵",
        "domains": ["soundcloud.com", "api-v2.soundcloud.com"],
        "test_domain": "soundcloud.com",
        "ports": {"tcp": [443]},
        "blocking_type": "partial",
        "category": "media",
    },
]


def get_all_services():
    """Вернуть все сервисы."""
    return BLOCKED_SERVICES


def get_all_domains():
    """Собрать все домены из всех сервисов в один плоский список."""
    domains = []
    for svc in BLOCKED_SERVICES:
        domains.extend(svc["domains"])
    return sorted(set(domains))


def get_service_by_id(service_id: str):
    """Найти сервис по ID."""
    for svc in BLOCKED_SERVICES:
        if svc["id"] == service_id:
            return svc
    return None
