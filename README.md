# astrbot_plugin_random_voice

按概率把 AstrBot 发送的文本内容**随机**转换为语音（TTS）。命中时，消息会以一段语音（语音段）形式发出，可同时保留原文文字。

## 工作原理

利用 AstrBot 的 `on_decorating_result` 消息发送前钩子：

1. 每次 AstrBot 准备发送消息时，按 `probability` 概率掷骰；
2. 命中后，取出消息链中的纯文本，调用当前会话使用的 TTS Provider（`context.get_using_tts_provider_async`）合成音频；
3. 用 `Record` 语音段替换文本段（也可选择同时保留原文）。

依赖机器人已配置可用的 TTS Provider（如 Edge-TTS、鱼音、MiniMax、Azure TTS 等）。

## 安装

把本目录放入 AstrBot 的 `data/plugins`，然后在 WebUI 中启用插件并配置 TTS Provider 即可。

## 配置（WebUI 管理面板或 `_conf_schema.json`）

| 配置项 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `enabled` | bool | true | 是否启用随机语音 |
| `probability` | float | 0.3 | 消息被转为语音的概率（0~1） |
| `keep_text` | bool | true | 转语音时是否同时保留原文文字 |
| `min_chars` | int | 1 | 少于该字符数不转语音 |
| `max_chars` | int | 500 | 超过该长度先截断再合成 |
| `skip_platforms` | list | [] | 跳过不转换的平台名（如 `webchat`、`telegram`） |

## 会话指令

```
/random_voice                      查看本会话状态与用法
/random_voice 开                   开启本会话随机语音
/random_voice 关                   关闭本会话随机语音
/random_voice 概率 0.5             设置本会话概率为 50%
```

会话级设置优先于全局配置，重启后恢复为全局配置。

## 说明

- 如果消息链里已经包含语音段（如 AstrBot 自带的语音回复），插件会跳过，避免重复转换。
- 仅纯文本/图片混合消息可转换；命中后保留图片等其他消息段。
- 合成失败不会影响原消息发送，插件会静默跳过。"# astrbot_plugin_random_voice" 
