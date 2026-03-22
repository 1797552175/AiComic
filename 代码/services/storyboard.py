"""
分镜生成服务
基于剧本结构生成详细的分镜列表
"""
import uuid
from typing import List, Dict, Any, Optional


class StoryboardGenerator:
    """分镜生成器"""

    # 镜头类型描述
    SHOT_TYPE_DESCRIPTIONS = {
        "wide": "建立场景，展示全貌",
        "full": "展示角色全身",
        "medium": "对话常用，膝盖以上",
        "close_up": "特写，强调表情或物品",
        "two_shot": "双人中景，两人同框",
        "over_shoulder": "过肩镜头，代入感强",
        "pov": "主观镜头，观众视角"
    }

    # 运动类型
    MOTION_TYPES = {
        "static": {"name": "静止", "type": "none", "params": {}},
        "pan_left": {"name": "左平推", "type": "translate", "params": {"x": -0.1, "y": 0}},
        "pan_right": {"name": "右平推", "type": "translate", "params": {"x": 0.1, "y": 0}},
        "tilt_up": {"name": "上摇", "type": "translate", "params": {"x": 0, "y": -0.1}},
        "tilt_down": {"name": "下摇", "type": "translate", "params": {"x": 0, "y": 0.1}},
        "zoom_in": {"name": "推进", "type": "scale", "params": {"from": 1.0, "to": 1.2}},
        "zoom_out": {"name": "拉远", "type": "scale", "params": {"from": 1.0, "to": 0.85}},
        "rotate": {"name": "旋转", "type": "rotate", "params": {"angle": 5}},
        "shake": {"name": "抖动", "type": "shake", "params": {"intensity": 0.02}}
    }

    async def generate_storyboard(
        self,
        scenes: List[Dict[str, Any]],
        characters: List[Dict[str, Any]],
        style: str = "anime"
    ) -> List[Dict[str, Any]]:
        """
        基于剧本结构生成分镜列表

        Args:
            scenes: 场景列表
            characters: 角色列表
            style: 漫画风格

        Returns:
            完整的分镜列表（含详细信息）
        """
        storyboard = []
        global_shot_index = 0

        for scene_idx, scene in enumerate(scenes):
            scene_shots = []

            for shot in scene.get("shots", []):
                # 补充镜头详细信息
                shot_type = shot.get("type", "medium")
                duration = shot.get("duration", 3.0)

                # 生成详细画面描述
                image_description = self._generate_shot_description(
                    shot=shot,
                    scene=scene,
                    characters=characters,
                    style=style
                )

                # 生成推荐运动类型
                recommended_motion = self._recommend_motion(
                    shot_type=shot_type,
                    has_dialogue=bool(shot.get("dialogue")),
                    is_action=any(
                        kw in str(shot.get("keywords", ""))
                        for kw in ["跑", "跳", "打", "飞", "冲", "run", "jump", "fight"]
                    )
                )

                # 角色列表（该镜头中出现的角色）
                shot_characters = self._extract_shot_characters(shot, characters)

                scene_shots.append({
                    "id": shot.get("id", str(uuid.uuid4())),
                    "scene_id": scene.get("id", ""),
                    "scene_index": scene_idx,
                    "order_index": global_shot_index,
                    "type": shot_type,
                    "type_description": self.SHOT_TYPE_DESCRIPTIONS.get(shot_type, ""),
                    "duration": duration,
                    "keywords": shot.get("keywords", ""),
                    "description": shot.get("description", ""),
                    "image_description": image_description,
                    "dialogue": shot.get("dialogue", []),
                    "characters": shot_characters,
                    "motion": recommended_motion,
                    "status": "pending",
                    "image_url": None
                })

                global_shot_index += 1

            storyboard.extend(scene_shots)

        return storyboard

    def _generate_shot_description(
        self,
        shot: Dict[str, Any],
        scene: Dict[str, Any],
        characters: List[Dict[str, Any]],
        style: str
    ) -> str:
        """生成详细的画面描述"""
        shot_type = shot.get("type", "medium")
        dialogues = shot.get("dialogue", [])
        location = scene.get("location", "")

        # 构建基础描述
        desc_parts = []

        # 场景
        desc_parts.append(f"场景：{location}")

        # 镜头类型对应的画面
        if shot_type == "wide":
            desc_parts.append("广角镜头，建立场景氛围")
        elif shot_type == "close_up":
            desc_parts.append("特写镜头，强调角色表情")
        elif shot_type == "medium":
            desc_parts.append("中景镜头，标准对话距离")
        elif shot_type == "two_shot":
            desc_parts.append("双人镜头，两人互动")
        elif shot_type == "pov":
            desc_parts.append("主观视角，观众代入感")

        # 角色动作/表情
        for d in dialogues:
            char_name = d.get("character", "")
            emotion = d.get("emotion", "neutral")
            text = d.get("text", "")

            if char_name != "旁白":
                emotion_text = {
                    "happy": "高兴地",
                    "sad": "伤心地",
                    "angry": "生气地",
                    "surprised": "惊讶地",
                    "neutral": "平静地"
                }.get(emotion, "")
                desc_parts.append(f"{char_name}【{emotion_text}】说：\"{text[:20]}...\"")

        # 风格补充
        style_desc = {
            "anime": "日系动漫风格，线条清晰，色彩明快",
            "realistic": "写实风格，光影自然，质感真实",
            "cyberpunk": "赛博朋克风格，霓虹灯光，未来科技感",
            "ink": "水墨风格，国风美学，笔触飘逸",
            "bw": "黑白漫画风格，对比强烈，网点纹理"
        }.get(style, "")

        desc_parts.append(style_desc)

        return " | ".join(desc_parts)

    def _recommend_motion(
        self,
        shot_type: str,
        has_dialogue: bool,
        is_action: bool
    ) -> Dict[str, Any]:
        """推荐运动类型"""
        # 有对话的镜头建议静止或轻微动效
        if has_dialogue:
            if shot_type == "close_up":
                return {"type": "static", "name": "静止", "params": {}}
            elif shot_type == "wide":
                return {"type": "pan_left", "name": "缓慢左移", "params": {"x": -0.03, "y": 0}}
            else:
                return {"type": "static", "name": "静止", "params": {}}

        # 动作场景
        if is_action:
            if shot_type == "wide":
                return {"type": "pan_left", "name": "快速左移", "params": {"x": -0.15, "y": 0}}
            else:
                return {"type": "shake", "name": "抖动", "params": {"intensity": 0.05}}

        # 默认静止
        return {"type": "static", "name": "静止", "params": {}}

    def _extract_shot_characters(
        self,
        shot: Dict[str, Any],
        all_characters: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """提取该镜头中出现的角色"""
        dialogue_characters = set()
        for d in shot.get("dialogue", []):
            if d.get("character") != "旁白":
                dialogue_characters.add(d.get("character"))

        # 匹配角色详情
        result = []
        for char in all_characters:
            if char.get("name") in dialogue_characters:
                result.append({
                    "name": char.get("name"),
                    "description": char.get("description", ""),
                    "emotion_default": char.get("emotion_default", "neutral")
                })

        return result

    def get_motion_options(self) -> List[Dict[str, Any]]:
        """获取可选的运动类型列表"""
        return [
            {"value": k, "label": v["name"], "type": v["type"], "params": v["params"]}
            for k, v in self.MOTION_TYPES.items()
        ]

    def get_shot_type_options(self) -> List[Dict[str, str]]:
        """获取可选的镜头类型列表"""
        return [
            {"value": k, "label": f"{v} - {desc}"}
            for k, v, desc in [
                ("wide", "远景", self.SHOT_TYPE_DESCRIPTIONS["wide"]),
                ("full", "全景", self.SHOT_TYPE_DESCRIPTIONS["full"]),
                ("medium", "中景", self.SHOT_TYPE_DESCRIPTIONS["medium"]),
                ("close_up", "特写", self.SHOT_TYPE_DESCRIPTIONS["close_up"]),
                ("two_shot", "双人中景", self.SHOT_TYPE_DESCRIPTIONS["two_shot"]),
                ("over_shoulder", "过肩镜头", self.SHOT_TYPE_DESCRIPTIONS["over_shoulder"]),
                ("pov", "主观镜头", self.SHOT_TYPE_DESCRIPTIONS["pov"]),
            ]
        ]


# 全局实例
storyboard_generator = StoryboardGenerator()
