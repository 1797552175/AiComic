"""
剧本解析服务
使用 LLM (GPT-4 / GLM-4) 将文本剧本解析为结构化数据
"""
import re
import json
import uuid
from typing import List, Dict, Any, Optional

from config.config import settings


class ScriptParser:
    """剧本解析器"""

    # 镜头类型候选
    SHOT_TYPES = ["wide", "full", "medium", "close_up", "two_shot", "over_shoulder", "pov"]

    # 情绪候选
    EMOTIONS = ["happy", "sad", "angry", "surprised", "neutral"]

    def __init__(self, llm_api_key: Optional[str] = None):
        self.llm_api_key = llm_api_key or settings.openai_api_key
        self.llm_base_url = settings.openai_base_url
        self.llm_model = settings.llm_model

    async def parse(self, script_text: str, style: str = "anime") -> Dict[str, Any]:
        """
        解析剧本文本为结构化数据

        Args:
            script_text: 原始剧本文本
            style: 漫画风格

        Returns:
            包含 scenes, characters, warnings 的字典
        """
        # 1. 预处理：提取场景分段
        scene_blocks = self._split_scenes(script_text)

        # 2. 解析每个场景
        scenes = []
        characters = {}
        warnings = []

        for block in scene_blocks:
            try:
                scene_data = self._parse_scene(block, style)
                if scene_data:
                    scenes.append(scene_data)
                    # 收集角色
                    for char in scene_data.get("characters", []):
                        if char["name"] not in characters:
                            characters[char["name"]] = char
            except Exception as e:
                warnings.append(f"解析场景失败: {str(e)}")

        return {
            "scenes": scenes,
            "characters": list(characters.values()),
            "warnings": warnings
        }

    def _split_scenes(self, text: str) -> List[str]:
        """按【场景】分段"""
        # 匹配 【场景N：xxx】 或 【场景xxx】
        pattern = r"【([^】]+)】"
        parts = re.split(pattern, text)

        scenes = []
        for i in range(1, len(parts), 2):
            location = parts[i].strip()
            content = parts[i + 1] if i + 1 < len(parts) else ""
            scenes.append({"location": location, "content": content.strip()})

        # 如果没有场景标记，整个文本作为一个场景
        if not scenes:
            scenes = [{"location": "默认场景", "content": text.strip()}]

        return scenes

    def _parse_scene(self, scene_block: Dict[str, str], style: str) -> Optional[Dict[str, Any]]:
        """解析单个场景"""
        location = scene_block["location"]
        content = scene_block["content"]

        if not content:
            return None

        # 提取对话行
        dialogue_lines = self._extract_dialogues(content)

        # 生成镜头
        shots = self._generate_shots(dialogue_lines, style)

        # 提取该场景的角色
        scene_chars = self._extract_characters(dialogue_lines)

        return {
            "id": str(uuid.uuid4()),
            "location": location,
            "shots": shots,
            "characters": scene_chars
        }

    def _extract_dialogues(self, text: str) -> List[Dict[str, str]]:
        """提取对话行"""
        lines = text.split("\n")
        dialogues = []

        # 对话格式: 角色（情绪）：台词  或  旁白：台词
        pattern = r"^(.+?)[（(]([^）)]+)[）)]：(.+)$|^(?:旁白)[：:](.+)$|^(.+?)[：:](.+)$"

        for line in lines:
            line = line.strip()
            if not line:
                continue

            match = re.match(pattern, line)
            if match:
                # 格式1: 角色（情绪）：台词
                if match.group(1) and match.group(2) and match.group(3):
                    character = match.group(1).strip()
                    emotion = self._normalize_emotion(match.group(2).strip())
                    text_content = match.group(3).strip()
                    dialogues.append({
                        "character": character,
                        "emotion": emotion,
                        "text": text_content
                    })
                # 格式2: 旁白：台词
                elif match.group(4):
                    dialogues.append({
                        "character": "旁白",
                        "emotion": "neutral",
                        "text": match.group(4).strip()
                    })
                # 格式3: 角色：台词（无情绪）
                elif match.group(5) and match.group(6):
                    character = match.group(5).strip()
                    if character not in ["旁白", " narration"]:
                        dialogues.append({
                            "character": character,
                            "emotion": "neutral",
                            "text": match.group(6).strip()
                        })

        return dialogues

    def _extract_characters(self, dialogues: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """提取角色列表"""
        char_map = {}
        for d in dialogues:
            name = d["character"]
            if name not in char_map:
                char_map[name] = {
                    "name": name,
                    "description": "",
                    "emotion_default": d["emotion"]
                }
        return list(char_map.values())

    def _generate_shots(self, dialogues: List[Dict[str, str]], style: str) -> List[Dict[str, Any]]:
        """为对话生成分镜"""
        shots = []
        current_shot = None
        shot_id = 0

        for dialogue in dialogues:
            if dialogue["character"] == "旁白":
                # 旁白作为一个独立镜头
                shot_id += 1
                shots.append({
                    "id": str(uuid.uuid4()),
                    "type": "wide",  # 旁白通常用远景
                    "duration": self._estimate_duration(dialogue["text"]),
                    "keywords": self._generate_keywords(dialogue["text"], style),
                    "description": f"旁白：{dialogue['text'][:50]}...",
                    "dialogue": [dialogue]
                })
            else:
                # 普通对话，可能合并到当前镜头
                if current_shot is None or len(current_shot.get("dialogue", [])) >= 2:
                    # 新镜头
                    shot_id += 1
                    current_shot = {
                        "id": str(uuid.uuid4()),
                        "type": "medium",  # 默认中景
                        "duration": 0,
                        "keywords": "",
                        "description": "",
                        "dialogue": []
                    }
                    shots.append(current_shot)

                current_shot["dialogue"].append(dialogue)
                current_shot["duration"] += self._estimate_duration(dialogue["text"])

        # 限制镜头时长范围
        for shot in shots:
            shot["duration"] = max(1.5, min(8.0, shot["duration"]))
            shot["keywords"] = self._generate_keywords(
                " ".join([d["text"] for d in shot["dialogue"]]),
                style
            )

        return shots

    def _estimate_duration(self, text: str) -> float:
        """估算对话时长（秒）"""
        # 粗略估算：中文约 4-5字/秒
        char_count = len(text)
        base_duration = char_count / 4.5
        return round(base_duration, 1)

    def _normalize_emotion(self, emotion_str: str) -> str:
        """标准化情绪词"""
        emotion_str = emotion_str.lower()

        happy_keywords = ["高兴", "开心", "快乐", "喜悦", "欢快", "兴奋", "happy", "joy"]
        sad_keywords = ["悲伤", "难过", "伤心", "沮丧", "sad", "grief"]
        angry_keywords = ["生气", "愤怒", "恼火", "angry", "rage"]
        surprised_keywords = ["惊讶", "吃惊", "意外", "surprised", "shock"]

        for kw in happy_keywords:
            if kw in emotion_str:
                return "happy"
        for kw in sad_keywords:
            if kw in emotion_str:
                return "sad"
        for kw in angry_keywords:
            if kw in emotion_str:
                return "angry"
        for kw in surprised_keywords:
            if kw in emotion_str:
                return "surprised"

        return "neutral"

    def _generate_keywords(self, text: str, style: str) -> str:
        """生成画面关键词"""
        style_prefix = {
            "anime": "anime style, manga illustration,",
            "realistic": "realistic painting, cinematic,",
            "cyberpunk": "cyberpunk, neon lights, futuristic,",
            "ink": "chinese ink painting, traditional art,",
            "bw": "black and white manga, manga panel,"
        }.get(style, "manga style,")

        # 简单提取关键名词（实际应用中可调用LLM提取）
        keywords = text.replace("。", " ").replace(",", " ")
        if len(keywords) > 50:
            keywords = keywords[:50]

        return f"{style_prefix} {keywords}"


# 全局实例
script_parser = ScriptParser()
