package main

// ServiceInfo — описание заблокированного сервиса
type ServiceInfo struct {
	ID           string `json:"id"`
	Name         string `json:"name"`
	TestDomain   string `json:"test_domain"`
	BlockType    string `json:"blocking_type"`  // full, throttle, partial
	BypassMethod string `json:"bypass_method"`  // dpi, ip, mixed
}

// DefaultServices — встроенный список заблокированных сервисов
// bypass_method: "dpi" = zapret2 поможет, "ip" = нужен VPN, "mixed" = частично
var DefaultServices = []ServiceInfo{
	// ── DPI — zapret2 помогает ──
	{ID: "youtube", Name: "YouTube", TestDomain: "youtube.com", BlockType: "throttle", BypassMethod: "dpi"},
	{ID: "discord", Name: "Discord", TestDomain: "discord.com", BlockType: "full", BypassMethod: "dpi"},
	{ID: "chatgpt", Name: "ChatGPT", TestDomain: "chat.openai.com", BlockType: "throttle", BypassMethod: "dpi"},
	{ID: "roblox", Name: "Roblox", TestDomain: "roblox.com", BlockType: "full", BypassMethod: "dpi"},
	{ID: "twitch", Name: "Twitch", TestDomain: "twitch.tv", BlockType: "partial", BypassMethod: "dpi"},
	{ID: "soundcloud", Name: "SoundCloud", TestDomain: "soundcloud.com", BlockType: "partial", BypassMethod: "dpi"},
	{ID: "twitter", Name: "X (Twitter)", TestDomain: "x.com", BlockType: "full", BypassMethod: "mixed"},
	// ── IP-блокировка — zapret2 не поможет, нужен VPN ──
	{ID: "telegram", Name: "Telegram", TestDomain: "telegram.org", BlockType: "full", BypassMethod: "ip"},
	{ID: "whatsapp", Name: "WhatsApp", TestDomain: "web.whatsapp.com", BlockType: "full", BypassMethod: "ip"},
	{ID: "facebook", Name: "Facebook", TestDomain: "facebook.com", BlockType: "full", BypassMethod: "ip"},
	{ID: "instagram", Name: "Instagram", TestDomain: "instagram.com", BlockType: "full", BypassMethod: "ip"},
	{ID: "signal", Name: "Signal", TestDomain: "signal.org", BlockType: "full", BypassMethod: "ip"},
	{ID: "viber", Name: "Viber", TestDomain: "viber.com", BlockType: "full", BypassMethod: "ip"},
	{ID: "linkedin", Name: "LinkedIn", TestDomain: "linkedin.com", BlockType: "full", BypassMethod: "ip"},
	{ID: "snapchat", Name: "Snapchat", TestDomain: "snapchat.com", BlockType: "full", BypassMethod: "ip"},
}
