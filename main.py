import random

import astrbot.api.message_components as Comp
from astrbot.api import AstrBotConfig, logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star


class RandomVoice(Star):
    """把 AstrBot 发送的文本内容按概率随机转换为语音（TTS）。

    依赖：机器人头部配置了可用的 TTS Provider（如 Edge-TTS、鱼音、MiniMax 等）。
    """

    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self.session_overrides: dict[str, dict[str, object]] = {}

    def _session_state(self, umo: str) -> dict[str, object]:
        return self.session_overrides.setdefault(umo, {})

    def _config_float(self, key: str, default: float) -> float:
        try:
            return max(0.0, min(1.0, float(self.config.get(key, default))))
        except (TypeError, ValueError):
            return default

    def _should_convert(self, event: AstrMessageEvent) -> float | None:
        if not bool(self.config.get("enabled", True)):
            return None
        skip = self.config.get("skip_platforms", []) or []
        if event.get_platform_name() in skip:
            return None
        st = self._session_state(event.unified_msg_origin)
        if "enabled" in st and not st["enabled"]:
            return None
        if "probability" in st:
            return max(0.0, min(1.0, float(st["probability"])))
        return self._config_float("probability", 0.3)

    def _plain_text(self, chain) -> str:
        texts = []
        for comp in chain:
            if isinstance(comp, Comp.Plain):
                texts.append(getattr(comp, "text", None) or "")
        return " ".join(t for t in texts if t).strip()

    async def _synthesize(self, event: AstrMessageEvent, text: str) -> str | None:
        try:
            provider = await self.context.get_using_tts_provider_async(
                umo=event.unified_msg_origin
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"[random_voice] 获取 TTS Provider 失败: {exc}")
            return None
        if provider is None:
            logger.debug("[random_voice] 未配置 TTS Provider，跳过本次转换")
            return None
        try:
            path = await provider.get_audio(text)
            return path if path else None
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"[random_voice] TTS 合成失败: {exc}")
            return None

    @filter.on_decorating_result()
    async def on_decorating_result(self, event: AstrMessageEvent):
        """消息发送前钩子：按概率把纯文本内容替换为一条语音。"""
        probability = self._should_convert(event)
        if probability is None:
            return
        result = event.get_result()
        if result is None or not result.chain:
            return
        if any(isinstance(comp, Comp.Record) for comp in result.chain):
            return

        text = self._plain_text(result.chain)
        if not text:
            return
        min_chars = int(self.config.get("min_chars", 1) or 1)
        if len(text) < min_chars:
            return
        max_chars = int(self.config.get("max_chars", 500) or 500)
        if max_chars > 0 and len(text) > max_chars:
            text = text[:max_chars]

        if random.random() > probability:
            return

        path = await self._synthesize(event, text)
        if not path:
            return

        try:
            voice = Comp.Record.fromFileSystem(path)
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"[random_voice] 构造语音消息失败: {exc}")
            return

        new_chain = []
        if bool(self.config.get("keep_text", True)):
            new_chain.append(Comp.Plain(text=text, convert=False))
        new_chain.append(voice)
        for comp in result.chain:
            if isinstance(comp, (Comp.Plain, Comp.Record)):
                continue
            new_chain.append(comp)
        result.chain = new_chain
        logger.info(f"[random_voice] 已把一条消息转为语音（概率 {probability:.0%}）")

    @filter.command("random_voice")
    async def random_voice_command(self, event: AstrMessageEvent, *args):
        """会话级控制：/random_voice 开|关|概率 <0~1>"""
        umo = event.unified_msg_origin
        st = self._session_state(umo)
        tokens = " ".join(str(a) for a in args).split()
        if not tokens:
            enabled = st.get("enabled", True)
            prob = st.get(
                "probability", self._config_float("probability", 0.3)
            )
            yield event.plain_result(
                "随机语音状态："
                + ("开启" if enabled else "关闭")
                + f"\n本会话概率：{prob}\n全局默认概率：{self._config_float('probability', 0.3)}"
                + "\n用法：/random_voice 开 ｜ 关 ｜ 概率 <0~1>"
            )
            return
        head = tokens[0].lower()
        if head in ("开", "on", "1", "true", "yes"):
            st["enabled"] = True
            yield event.plain_result("已开启本会话的随机语音。")
        elif head in ("关", "off", "0", "false", "no"):
            st["enabled"] = False
            yield event.plain_result("已关闭本会话的随机语音。")
        elif head in ("概率", "prob", "p"):
            try:
                value = float(tokens[1])
            except (IndexError, TypeError, ValueError):
                yield event.plain_result("用法：/random_voice 概率 <0~1>")
                return
            st["probability"] = max(0.0, min(1.0, value))
            yield event.plain_result(
                f"本会话随机语音概率已设为 {st['probability']:.0%}。"
            )
        else:
            yield event.plain_result("用法：/random_voice 开 ｜ 关 ｜ 概率 <0~1>")