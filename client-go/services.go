package main

// ServiceInfo — описание заблокированного сервиса
type ServiceInfo struct {
	ID          string `json:"id"`
	Name        string `json:"name"`
	TestDomain  string `json:"test_domain"`
	BlockType   string `json:"blocking_type"` // full, throttle, partial
}

// DefaultServices — встроенный список заблокированных сервисов
var DefaultServices = []ServiceInfo{
	{ID: "youtube", Name: "YouTube", TestDomain: "youtube.com", BlockType: "throttle"},
	{ID: "discord", Name: "Discord", TestDomain: "discord.com", BlockType: "full"},
	{ID: "facebook", Name: "Facebook", TestDomain: "facebook.com", BlockType: "full"},
	{ID: "instagram", Name: "Instagram", TestDomain: "instagram.com", BlockType: "full"},
	{ID: "twitter", Name: "X (Twitter)", TestDomain: "x.com", BlockType: "full"},
	{ID: "telegram_calls", Name: "Telegram (звонки)", TestDomain: "telegram.org", BlockType: "partial"},
	{ID: "signal", Name: "Signal", TestDomain: "signal.org", BlockType: "full"},
	{ID: "viber", Name: "Viber", TestDomain: "viber.com", BlockType: "full"},
	{ID: "linkedin", Name: "LinkedIn", TestDomain: "linkedin.com", BlockType: "full"},
	{ID: "snapchat", Name: "Snapchat", TestDomain: "snapchat.com", BlockType: "full"},
	{ID: "whatsapp_calls", Name: "WhatsApp (звонки)", TestDomain: "web.whatsapp.com", BlockType: "partial"},
	{ID: "chatgpt", Name: "ChatGPT", TestDomain: "chat.openai.com", BlockType: "throttle"},
	{ID: "roblox", Name: "Roblox", TestDomain: "roblox.com", BlockType: "full"},
	{ID: "twitch", Name: "Twitch", TestDomain: "twitch.tv", BlockType: "partial"},
	{ID: "soundcloud", Name: "SoundCloud", TestDomain: "soundcloud.com", BlockType: "partial"},
}
