#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
暗区文字 (Dark Zone: Text)
一款基于三角洲行动-烽火地带核心玩法的文字撤离射击游戏
"""

import json
import random
import time
import os
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from copy import deepcopy

# ============== 游戏常量 ==============
class Rarity(Enum):
    """物品稀有度"""
    COMMON = ("灰色", "common", 1.0)
    UNCOMMON = ("绿色", "uncommon", 1.5)
    RARE = ("蓝色", "rare", 2.0)
    EPIC = ("紫色", "epic", 3.0)
    LEGENDARY = ("金色", "legendary", 5.0)

    def __init__(self, cn_name, color, value_mult):
        self.cn_name = cn_name
        self.color = color
        self.value_mult = value_mult

class DamageZone(Enum):
    """身体部位"""
    HEAD = ("头部", 2.5, "致命伤害！")
    THORAX = ("胸部", 1.0, "")
    STOMACH = ("腹部", 0.9, "你感到剧烈腹痛。")
    LEFT_ARM = ("左臂", 0.7, "左臂受伤，精准度下降。")
    RIGHT_ARM = ("右臂", 0.7, "右臂受伤，换弹速度下降。")
    LEFT_LEG = ("左腿", 0.7, "左腿受伤，移动速度下降。")
    RIGHT_LEG = ("右腿", 0.7, "右腿受伤，移动速度下降。")

    def __init__(self, cn_name, multiplier, effect_msg):
        self.cn_name = cn_name
        self.multiplier = multiplier
        self.effect_msg = effect_msg

# ============== 游戏数据 ==============
WEAPONS = {
    "pistol_p226": {
        "name": "P226手枪",
        "type": "手枪",
        "damage": 35,
        "accuracy": 0.85,
        "fire_rate": 2,
        "penetration": 1,
        "ammo_type": "9mm",
        "mag_size": 15,
        "weight": 1.0,
        "value": 500,
        "rarity": Rarity.COMMON
    },
    "smg_mp5": {
        "name": "MP5冲锋枪",
        "type": "冲锋枪",
        "damage": 28,
        "accuracy": 0.65,
        "fire_rate": 5,
        "penetration": 2,
        "ammo_type": "9mm",
        "mag_size": 30,
        "weight": 2.5,
        "value": 2000,
        "rarity": Rarity.UNCOMMON
    },
    "ar_ak74n": {
        "name": "AK-74N突击步枪",
        "type": "突击步枪",
        "damage": 45,
        "accuracy": 0.70,
        "fire_rate": 3,
        "penetration": 3,
        "ammo_type": "5.45x39mm",
        "mag_size": 30,
        "weight": 3.4,
        "value": 5000,
        "rarity": Rarity.RARE
    },
    "ar_m4a1": {
        "name": "M4A1卡宾枪",
        "type": "突击步枪",
        "damage": 42,
        "accuracy": 0.80,
        "fire_rate": 4,
        "penetration": 3,
        "ammo_type": "5.56x45mm",
        "mag_size": 30,
        "weight": 2.9,
        "value": 6000,
        "rarity": Rarity.RARE
    },
    "sniper_mosin": {
        "name": "莫辛纳甘步枪",
        "type": "狙击步枪",
        "damage": 85,
        "accuracy": 0.98,
        "fire_rate": 1,
        "penetration": 4,
        "ammo_type": "7.62x54mmR",
        "mag_size": 5,
        "weight": 4.0,
        "value": 3000,
        "rarity": Rarity.UNCOMMON
    },
    "shotgun_m870": {
        "name": "M870霰弹枪",
        "type": "霰弹枪",
        "damage": 120,
        "accuracy": 0.40,
        "fire_rate": 1,
        "penetration": 1,
        "ammo_type": "12ga",
        "mag_size": 7,
        "weight": 3.5,
        "value": 1500,
        "rarity": Rarity.COMMON
    }
}

ARMORS = {
    "armor_1_paca": {
        "name": "PACA软甲",
        "class": 1,
        "durability": 30,
        "max_durability": 30,
        "weight": 1.5,
        "value": 1000,
        "rarity": Rarity.COMMON
    },
    "armor_2_police": {
        "name": "警用背心",
        "class": 2,
        "durability": 40,
        "max_durability": 40,
        "weight": 2.0,
        "value": 2000,
        "rarity": Rarity.UNCOMMON
    },
    "armor_3_umka": {
        "name": "UMKA突击背心",
        "class": 3,
        "durability": 50,
        "max_durability": 50,
        "weight": 4.0,
        "value": 4000,
        "rarity": Rarity.RARE
    },
    "armor_4_korund": {
        "name": "Korund-VM防弹衣",
        "class": 4,
        "durability": 65,
        "max_durability": 65,
        "weight": 5.5,
        "value": 8000,
        "rarity": Rarity.EPIC
    },
    "armor_5_killa": {
        "name": "Killa防弹衣",
        "class": 5,
        "durability": 80,
        "max_durability": 80,
        "weight": 8.0,
        "value": 15000,
        "rarity": Rarity.EPIC
    },
    "armor_6_slick": {
        "name": "Slick重型防弹衣",
        "class": 6,
        "durability": 90,
        "max_durability": 90,
        "weight": 12.0,
        "value": 30000,
        "rarity": Rarity.LEGENDARY
    }
}

HELMETS = {
    "helmet_none": {
        "name": "无头盔",
        "class": 0,
        "durability": 0,
        "max_durability": 0,
        "weight": 0,
        "value": 0,
        "rarity": Rarity.COMMON
    },
    "helmet_1_ssh68": {
        "name": "SSH-68头盔",
        "class": 2,
        "durability": 25,
        "max_durability": 25,
        "weight": 1.3,
        "value": 800,
        "rarity": Rarity.UNCOMMON
    },
    "helmet_3_untar": {
        "name": "UNTAR头盔",
        "class": 3,
        "durability": 35,
        "max_durability": 35,
        "weight": 1.5,
        "value": 2000,
        "rarity": Rarity.RARE
    },
    "helmet_4_fast": {
        "name": "FAST头盔",
        "class": 4,
        "durability": 45,
        "max_durability": 45,
        "weight": 1.8,
        "value": 5000,
        "rarity": Rarity.EPIC
    }
}

CONSUMABLES = {
    "med_bandage": {
        "name": "绷带",
        "type": "医疗",
        "effect": {"heal": 15},
        "use_time": 2,
        "weight": 0.1,
        "value": 100,
        "rarity": Rarity.COMMON,
        "description": "快速止血，恢复少量生命值"
    },
    "med_ai2": {
        "name": "AI-2急救包",
        "type": "医疗",
        "effect": {"heal": 50},
        "use_time": 4,
        "weight": 0.3,
        "value": 300,
        "rarity": Rarity.UNCOMMON,
        "description": "恢复中等生命值"
    },
    "med_ifak": {
        "name": "IFAK医疗包",
        "type": "医疗",
        "effect": {"heal": 100},
        "use_time": 6,
        "weight": 0.5,
        "value": 800,
        "rarity": Rarity.RARE,
        "description": "恢复大量生命值"
    },
    "med_surgery": {
        "name": "手术包",
        "type": "医疗",
        "effect": {"heal": 0, "fix_bodypart": True},
        "use_time": 15,
        "weight": 1.0,
        "value": 2000,
        "rarity": Rarity.EPIC,
        "description": "修复受伤的身体部位"
    },
    "med_painkiller": {
        "name": "止痛药",
        "type": "药物",
        "effect": {"pain_relief": 180},
        "use_time": 2,
        "weight": 0.1,
        "value": 200,
        "rarity": Rarity.COMMON,
        "description": "消除疼痛状态180秒"
    },
    "drink_energy": {
        "name": "能量饮料",
        "type": "消耗品",
        "effect": {"energy": 20, "stamina": 10},
        "use_time": 2,
        "weight": 0.3,
        "value": 150,
        "rarity": Rarity.COMMON,
        "description": "恢复能量和耐力"
    }
}

LOOT_ITEMS = {
    # 普通物资
    "loot_bolts": {
        "name": "螺丝零件",
        "type": "物资",
        "weight": 0.2,
        "value": 50,
        "rarity": Rarity.COMMON,
        "description": "普通的机械零件"
    },
    "loot_tape": {
        "name": "工业胶带",
        "type": "物资",
        "weight": 0.3,
        "value": 80,
        "rarity": Rarity.COMMON,
        "description": "用途广泛的胶带"
    },
    "loot_electronics": {
        "name": "电子元件",
        "type": "物资",
        "weight": 0.4,
        "value": 500,
        "rarity": Rarity.UNCOMMON,
        "description": "拆解得来的电子零件"
    },
    "loot_cpu": {
        "name": "CPU处理器",
        "type": "物资",
        "weight": 0.2,
        "value": 1500,
        "rarity": Rarity.RARE,
        "description": "高端处理器，有市无价"
    },
    "loot_gpu": {
        "name": "显卡GPU",
        "type": "物资",
        "weight": 1.0,
        "value": 28000,
        "rarity": Rarity.EPIC,
        "description": "稀缺的高端显卡"
    },
    "loot_bitcoin": {
        "name": "比特币矿机",
        "type": "物资",
        "weight": 8.0,
        "value": 50000,
        "rarity": Rarity.LEGENDARY,
        "description": "可运行的比特币矿机"
    },
    "loot_rolex": {
        "name": "劳力士手表",
        "type": "贵重品",
        "weight": 0.2,
        "value": 50000,
        "rarity": Rarity.EPIC,
        "description": "高档奢侈手表"
    },
    "loot_usb_secret": {
        "name": "加密U盘",
        "type": "贵重品",
        "weight": 0.1,
        "value": 80000,
        "rarity": Rarity.LEGENDARY,
        "description": "包含机密数据的加密U盘"
    },
    "loot_goldbar": {
        "name": "金条",
        "type": "贵重品",
        "weight": 1.0,
        "value": 100000,
        "rarity": Rarity.LEGENDARY,
        "description": "纯金条"
    },
    "loot_document": {
        "name": "机密文件",
        "type": "贵重品",
        "weight": 0.1,
        "value": 45000,
        "rarity": Rarity.EPIC,
        "description": "含有敏感信息的文件"
    }
}

# ============== 地图数据 ==============
MAP_INDUSTRIAL = {
    "name": "工业区",
    "description": "一座废弃的工业园区，传闻有大量高价值物资...",
    "zones": {
        "spawn_west": {
            "name": "西侧入口",
            "description": "工业区的西侧入口，杂草丛生。",
            "danger_level": 1,
            "loot_tier": 1,
            "connections": ["parking", "warehouse"],
            "is_spawn": True,
            "is_extract": False
        },
        "spawn_south": {
            "name": "南侧小径",
            "description": "一条隐蔽的小径，可以绕过主路。",
            "danger_level": 1,
            "loot_tier": 1,
            "connections": ["gas_station", "forest"],
            "is_spawn": True,
            "is_extract": False
        },
        "parking": {
            "name": "停车场",
            "description": "废弃的停车场，有几辆锈迹斑斑的卡车。",
            "danger_level": 2,
            "loot_tier": 2,
            "connections": ["spawn_west", "warehouse", "admin"],
            "is_spawn": False,
            "is_extract": False
        },
        "gas_station": {
            "name": "加油站",
            "description": "老旧的加油站，便利店或许还有存货。",
            "danger_level": 2,
            "loot_tier": 2,
            "connections": ["spawn_south", "warehouse", "forest"],
            "is_spawn": False,
            "is_extract": False
        },
        "warehouse": {
            "name": "物资仓库",
            "description": "大型仓库，堆满了各种物资箱。",
            "danger_level": 3,
            "loot_tier": 3,
            "connections": ["spawn_west", "parking", "admin", "gas_station"],
            "is_spawn": False,
            "is_extract": False,
            "requires_key": None
        },
        "admin": {
            "name": "行政大楼",
            "description": "园区行政大楼，据传有高价值物品。",
            "danger_level": 4,
            "loot_tier": 4,
            "connections": ["parking", "warehouse"],
            "is_spawn": False,
            "is_extract": False,
            "requires_key": None
        },
        "forest": {
            "name": "森林边缘",
            "description": "茂密的树林，适合潜伏。",
            "danger_level": 2,
            "loot_tier": 1,
            "connections": ["spawn_south", "gas_station", "extract_forest"],
            "is_spawn": False,
            "is_extract": False
        },
        "extract_west": {
            "name": "西侧撤离点",
            "description": "一个开放的撤离点。",
            "danger_level": 1,
            "loot_tier": 0,
            "connections": ["parking"],
            "is_spawn": False,
            "is_extract": True,
            "extract_condition": {"type": "open", "open_time": 0}
        },
        "extract_forest": {
            "name": "森林撤离点",
            "description": "隐蔽的森林小道撤离点，需要等待。",
            "danger_level": 1,
            "loot_tier": 0,
            "connections": ["forest"],
            "is_spawn": False,
            "is_extract": True,
            "extract_condition": {"type": "wait", "wait_time": 30}
        },
        "extract_bunker": {
            "name": "地下掩体",
            "description": "紧急撤离通道，需要丢弃背包。",
            "danger_level": 1,
            "loot_tier": 0,
            "connections": ["admin"],
            "is_spawn": False,
            "is_extract": True,
            "extract_condition": {"type": "drop_backpack", "drop_backpack": True}
        }
    }
}

# ============== 敌人数据 ==============
ENEMY_TYPES = {
    "scav_weak": {
        "name": "游荡者新兵",
        "hp": 100,
        "armor_class": 1,
        "accuracy": 0.3,
        "weapon": "pistol_p226",
        "aggro_range": 2,
        "loot_table": "scav_basic",
        "xp": 50
    },
    "scav_normal": {
        "name": "游荡者",
        "hp": 150,
        "armor_class": 2,
        "accuracy": 0.45,
        "weapon": "smg_mp5",
        "aggro_range": 3,
        "loot_table": "scav_normal",
        "xp": 100
    },
    "scav_veteran": {
        "name": "老练游荡者",
        "hp": 200,
        "armor_class": 3,
        "accuracy": 0.55,
        "weapon": "ar_ak74n",
        "aggro_range": 4,
        "loot_table": "scav_veteran",
        "xp": 200
    },
    "pmc_grunt": {
        "name": "佣兵士兵",
        "hp": 200,
        "armor_class": 4,
        "accuracy": 0.65,
        "weapon": "ar_m4a1",
        "aggro_range": 4,
        "loot_table": "pmc_normal",
        "xp": 300
    },
    "pmc_elite": {
        "name": "佣兵精英",
        "hp": 300,
        "armor_class": 5,
        "accuracy": 0.75,
        "weapon": "ar_m4a1",
        "aggro_range": 5,
        "loot_table": "pmc_elite",
        "xp": 500
    },
    "boss_killa": {
        "name": "杀手Killa",
        "hp": 800,
        "armor_class": 6,
        "accuracy": 0.85,
        "weapon": "ar_ak74n",
        "aggro_range": 6,
        "loot_table": "boss_killa",
        "xp": 2000,
        "is_boss": True
    }
}

LOOT_TABLES = {
    "scav_basic": [
        ("loot_bolts", 0.5),
        ("loot_tape", 0.3),
        ("med_bandage", 0.2)
    ],
    "scav_normal": [
        ("loot_electronics", 0.3),
        ("med_ai2", 0.2),
        ("loot_tape", 0.3),
        ("ammo_9mm", 0.2)
    ],
    "scav_veteran": [
        ("loot_cpu", 0.2),
        ("med_ifak", 0.2),
        ("loot_electronics", 0.3),
        ("armor_2_police", 0.1)
    ],
    "pmc_normal": [
        ("loot_cpu", 0.3),
        ("loot_document", 0.1),
        ("med_ifak", 0.2),
        ("ammo_556", 0.2),
        ("armor_3_umka", 0.1)
    ],
    "pmc_elite": [
        ("loot_gpu", 0.15),
        ("loot_document", 0.2),
        ("med_surgery", 0.1),
        ("armor_4_korund", 0.15),
        ("loot_rolex", 0.05)
    ],
    "boss_killa": [
        ("loot_gpu", 0.3),
        ("loot_rolex", 0.3),
        ("loot_bitcoin", 0.1),
        ("loot_usb_secret", 0.1),
        ("armor_5_killa", 0.4),
        ("loot_goldbar", 0.05)
    ]
}

# ============== 数据类定义 ==============
@dataclass
class Item:
    """物品基类"""
    id: str
    name: str
    weight: float
    value: int
    rarity: Rarity
    stackable: bool = False
    stack_size: int = 1
    description: str = ""

@dataclass
class Weapon(Item):
    """武器类"""
    damage: int = 0
    accuracy: float = 0.0
    fire_rate: int = 1
    penetration: int = 1
    ammo_type: str = ""
    mag_size: int = 30
    current_ammo: int = 30

    def get_item_type(self):
        return "weapon"

@dataclass
class Armor(Item):
    """护甲类"""
    armor_class: int = 0
    durability: int = 0
    max_durability: int = 0

    def get_item_type(self):
        return "armor"

@dataclass
class Consumable(Item):
    """消耗品类"""
    effect: dict = field(default_factory=dict)
    use_time: int = 2

    def get_item_type(self):
        return "consumable"

@dataclass
class LootItem(Item):
    """战利品类"""
    item_type: str = "物资"

    def get_item_type(self):
        return "loot"

@dataclass
class BodyPartStatus:
    """身体部位状态"""
    hp: int = 100
    max_hp: int = 100
    is_broken: bool = False

    def take_damage(self, damage: int) -> int:
        actual_damage = min(damage, self.hp)
        self.hp -= actual_damage
        if self.hp <= 0:
            self.is_broken = True
        return actual_damage

    def heal(self, amount: int) -> int:
        if self.is_broken:
            return 0
        healed = min(amount, self.max_hp - self.hp)
        self.hp += healed
        return healed

    def repair(self):
        self.is_broken = False
        self.hp = max(1, self.hp)

@dataclass
class PlayerStats:
    """玩家状态"""
    # 身体部位
    head: BodyPartStatus = field(default_factory=BodyPartStatus)
    thorax: BodyPartStatus = field(default_factory=BodyPartStatus)
    stomach: BodyPartStatus = field(default_factory=BodyPartStatus)
    left_arm: BodyPartStatus = field(default_factory=BodyPartStatus)
    right_arm: BodyPartStatus = field(default_factory=BodyPartStatus)
    left_leg: BodyPartStatus = field(default_factory=BodyPartStatus)
    right_leg: BodyPartStatus = field(default_factory=BodyPartStatus)

    # 其他状态
    energy: int = 100
    hydration: int = 100
    stamina: int = 100
    pain_relief_timer: int = 0

    # 货币
    money: int = 10000  # 初始资金

    # 经验
    xp: int = 0
    level: int = 1

    def is_alive(self) -> bool:
        return self.head.hp > 0 and self.thorax.hp > 0

    def get_total_hp(self) -> int:
        parts = [self.head, self.thorax, self.stomach,
                 self.left_arm, self.right_arm, self.left_leg, self.right_leg]
        return sum(p.hp for p in parts)

    def get_max_hp(self) -> int:
        return 700  # 7个部位，每个100

    def get_body_part(self, zone: DamageZone) -> BodyPartStatus:
        part_map = {
            DamageZone.HEAD: self.head,
            DamageZone.THORAX: self.thorax,
            DamageZone.STOMACH: self.stomach,
            DamageZone.LEFT_ARM: self.left_arm,
            DamageZone.RIGHT_ARM: self.right_arm,
            DamageZone.LEFT_LEG: self.left_leg,
            DamageZone.RIGHT_LEG: self.right_leg
        }
        return part_map[zone]

    def apply_pain_relief(self, duration: int):
        self.pain_relief_timer = duration

    def tick(self):
        """每回合更新状态"""
        if self.pain_relief_timer > 0:
            self.pain_relief_timer -= 1
        # 饥渴消耗
        self.energy = max(0, self.energy - 1)
        self.hydration = max(0, self.hydration - 1)

@dataclass
class Enemy:
    """敌人类"""
    id: str
    name: str
    hp: int
    max_hp: int
    armor_class: int
    accuracy: float
    weapon_id: str
    aggro_range: int
    loot_table: str
    xp: int
    is_boss: bool = False
    current_zone: str = ""
    state: str = "patrol"  # patrol, alert, combat

    def take_damage(self, damage: int, penetration: int) -> int:
        """计算实际伤害"""
        # 护甲减伤
        if self.armor_class > 0:
            armor_reduction = max(0, (self.armor_class - penetration) * 0.2 + 0.1)
            armor_reduction = min(0.85, armor_reduction)
            actual_damage = int(damage * (1 - armor_reduction))
        else:
            actual_damage = damage

        self.hp -= actual_damage
        return actual_damage

    def is_alive(self) -> bool:
        return self.hp > 0

# ============== 背包系统 ==============
class Backpack:
    """背包系统 - 模拟格子存储"""
    def __init__(self, rows: int = 5, cols: int = 4):
        self.rows = rows
        self.cols = cols
        self.grid = [[None for _ in range(cols)] for _ in range(rows)]
        self.items: Dict[str, Item] = {}

    def can_fit(self, item: Item) -> bool:
        """检查是否能放入物品"""
        for row in range(self.rows):
            for col in range(self.cols):
                if self.grid[row][col] is None:
                    return True
        return False

    def add_item(self, item: Item) -> bool:
        """添加物品到背包"""
        for row in range(self.rows):
            for col in range(self.cols):
                if self.grid[row][col] is None:
                    self.grid[row][col] = item.id
                    self.items[item.id] = item
                    return True
        return False

    def remove_item(self, item_id: str) -> Optional[Item]:
        """从背包移除物品"""
        if item_id in self.items:
            item = self.items.pop(item_id)
            for row in range(self.rows):
                for col in range(self.cols):
                    if self.grid[row][col] == item_id:
                        self.grid[row][col] = None
            return item
        return None

    def get_item(self, item_id: str) -> Optional[Item]:
        return self.items.get(item_id)

    def get_all_items(self) -> List[Item]:
        return list(self.items.values())

    def get_total_weight(self) -> float:
        return sum(item.weight for item in self.items.values())

    def get_total_value(self) -> int:
        return sum(item.value for item in self.items.values())

    def clear(self):
        """清空背包"""
        self.grid = [[None for _ in range(self.cols)] for _ in range(self.rows)]
        self.items.clear()

class SecureContainer:
    """保险箱 - 死亡后保留物品"""
    def __init__(self, rows: int = 2, cols: int = 2):
        self.rows = rows
        self.cols = cols
        self.grid = [[None for _ in range(cols)] for _ in range(rows)]
        self.items: Dict[str, Item] = {}

    def add_item(self, item: Item) -> bool:
        for row in range(self.rows):
            for col in range(self.cols):
                if self.grid[row][col] is None:
                    self.grid[row][col] = item.id
                    self.items[item.id] = item
                    return True
        return False

    def remove_item(self, item_id: str) -> Optional[Item]:
        if item_id in self.items:
            item = self.items.pop(item_id)
            for row in range(self.rows):
                for col in range(self.cols):
                    if self.grid[row][col] == item_id:
                        self.grid[row][col] = None
            return item
        return None

    def get_all_items(self) -> List[Item]:
        return list(self.items.values())

# ============== 装备槽位 ==============
class EquipmentSlots:
    """装备槽位"""
    def __init__(self):
        self.primary_weapon: Optional[Weapon] = None
        self.secondary_weapon: Optional[Weapon] = None
        self.helmet: Optional[Armor] = None
        self.armor: Optional[Armor] = None
        self.backpack: Backpack = Backpack()
        self.secure_container: SecureContainer = SecureContainer()
        self.pocket_items: List[Item] = []  # 口袋物品（安全带出）

    def equip_weapon(self, weapon: Weapon, slot: str = "primary"):
        if slot == "primary":
            self.primary_weapon = weapon
        else:
            self.secondary_weapon = weapon

    def equip_armor(self, armor: Armor):
        self.armor = armor

    def equip_helmet(self, helmet: Armor):
        self.helmet = helmet

    def get_total_weight(self) -> float:
        weight = 0
        if self.primary_weapon:
            weight += self.primary_weapon.weight
        if self.secondary_weapon:
            weight += self.secondary_weapon.weight
        if self.helmet:
            weight += self.helmet.weight
        if self.armor:
            weight += self.armor.weight
        weight += self.backpack.get_total_weight()
        return weight

# ============== 玩家类 ==============
class Player:
    """玩家类"""
    def __init__(self, name: str = "玩家"):
        self.name = name
        self.stats = PlayerStats()
        self.equipment = EquipmentSlots()
        self.inventory: List[Item] = []  # 仓库
        self.current_zone: str = ""
        self.action_points: int = 100
        self.max_action_points: int = 100
        self.kills: int = 0
        self.total_loot_value: int = 0

    def heal(self, amount: int, body_part: DamageZone = None):
        """治疗"""
        if body_part:
            part = self.stats.get_body_part(body_part)
            return part.heal(amount)
        else:
            # 治疗所有部位
            healed = 0
            for zone in DamageZone:
                part = self.stats.get_body_part(zone)
                healed += part.heal(amount)
            return healed

    def take_damage(self, damage: int, zone: DamageZone, penetration: int = 0) -> Tuple[int, str]:
        """受到伤害"""
        part = self.stats.get_body_part(zone)

        # 计算护甲减伤
        armor_reduction = 0
        armor_msg = ""

        if zone in [DamageZone.HEAD, DamageZone.THORAX] and self.equipment.armor:
            armor = self.equipment.armor
            if armor.durability > 0:
                armor_reduction = max(0, (armor.armor_class - penetration) * 0.2 + 0.1)
                armor_reduction = min(0.85, armor_reduction)
                armor.durability -= int(damage * 0.1)
                if armor_reduction > 0:
                    armor_msg = f"护甲抵挡了{int(armor_reduction*100)}%伤害！"
        elif zone == DamageZone.HEAD and self.equipment.helmet:
            helmet = self.equipment.helmet
            if helmet.durability > 0 and helmet.armor_class > 0:
                armor_reduction = max(0, (helmet.armor_class - penetration) * 0.2 + 0.1)
                armor_reduction = min(0.85, armor_reduction)
                helmet.durability -= int(damage * 0.1)
                if armor_reduction > 0:
                    armor_msg = f"头盔抵挡了{int(armor_reduction*100)}%伤害！"

        actual_damage = int(damage * (1 - armor_reduction) * zone.multiplier)
        part.take_damage(actual_damage)

        msg = f"你的{zone.cn_name}受到{actual_damage}点伤害！"
        if armor_msg:
            msg += f" {armor_msg}"
        if zone.effect_msg:
            msg += f" {zone.effect_msg}"

        return actual_damage, msg

    def attack(self, target: Enemy, aim: str = "body") -> Tuple[int, str]:
        """攻击敌人"""
        weapon = self.equipment.primary_weapon
        if not weapon:
            return 0, "你没有装备武器！"

        if weapon.current_ammo <= 0:
            return 0, "弹药耗尽！需要换弹！"

        # 消耗弹药
        shots = min(weapon.fire_rate, weapon.current_ammo)
        weapon.current_ammo -= shots

        # 计算命中
        base_accuracy = weapon.accuracy

        # 身体部位影响
        if self.stats.right_arm.is_broken:
            base_accuracy *= 0.5
        if self.stats.left_arm.is_broken:
            base_accuracy *= 0.8

        # 瞄准修正
        aim_modifier = {"head": 0.5, "body": 1.0, "legs": 0.9}.get(aim, 1.0)

        total_damage = 0
        hits = 0
        messages = []

        for _ in range(shots):
            if random.random() < base_accuracy * aim_modifier:
                hits += 1
                damage = target.take_damage(weapon.damage, weapon.penetration)
                total_damage += damage

        if hits > 0:
            msg = f"你使用{weapon.name}射击，命中{hits}发，造成{total_damage}点伤害！"
            if not target.is_alive():
                msg += f"\n{target.name}被击杀！"
        else:
            msg = f"你使用{weapon.name}射击，但全部打偏了！"

        return total_damage, msg

    def reload(self):
        """换弹"""
        weapon = self.equipment.primary_weapon
        if weapon:
            weapon.current_ammo = weapon.mag_size
            return True, f"{weapon.name}已装填弹药！"
        return False, "没有装备武器！"

    def use_item(self, item_id: str) -> Tuple[bool, str]:
        """使用物品"""
        # 从背包或口袋中寻找物品
        item = self.equipment.backpack.get_item(item_id)
        if not item and item_id in [i.id for i in self.equipment.pocket_items]:
            item = next((i for i in self.equipment.pocket_items if i.id == item_id), None)

        if not item:
            return False, "找不到该物品！"

        if not isinstance(item, Consumable):
            return False, "该物品无法使用！"

        # 应用效果
        msg = f"你使用了{item.name}。"
        effect = item.effect

        if "heal" in effect and effect["heal"] > 0:
            healed = self.heal(effect["heal"])
            msg += f"恢复了{healed}点生命值。"

        if "fix_bodypart" in effect and effect["fix_bodypart"]:
            for zone in DamageZone:
                part = self.stats.get_body_part(zone)
                if part.is_broken:
                    part.repair()
            msg += "修复了所有受伤部位。"

        if "pain_relief" in effect:
            self.stats.apply_pain_relief(effect["pain_relief"])
            msg += f"止痛效果持续{effect['pain_relief']}秒。"

        if "energy" in effect:
            self.stats.energy = min(100, self.stats.energy + effect["energy"])
            msg += f"恢复了{effect['energy']}点能量。"

        # 移除物品
        self.equipment.backpack.remove_item(item_id)
        if item in self.equipment.pocket_items:
            self.equipment.pocket_items.remove(item)

        return True, msg

    def add_xp(self, amount: int):
        """增加经验值"""
        self.stats.xp += amount
        # 升级检查
        xp_needed = self.stats.level * 1000
        while self.stats.xp >= xp_needed:
            self.stats.xp -= xp_needed
            self.stats.level += 1
            xp_needed = self.stats.level * 1000

# ============== 游戏状态 ==============
class GameState(Enum):
    """游戏状态"""
    MAIN_MENU = "main_menu"
    BASE = "base"  # 基地/仓库
    RAID = "raid"  # 行动中
    COMBAT = "combat"  # 战斗中
    DEAD = "dead"  # 死亡
    EXTRACTED = "extracted"  # 成功撤离

# ============== 突击行动管理 ==============
class Raid:
    """突击行动"""
    def __init__(self, map_data: dict):
        self.map_data = map_data
        self.zones = deepcopy(map_data["zones"])
        self.enemies: List[Enemy] = []
        self.time_elapsed: int = 0
        self.max_time: int = 60  # 最大行动时间（回合）
        self.loot_generated: bool = False

    def spawn_enemies(self, player_level: int):
        """根据玩家等级生成敌人"""
        enemy_count = 5 + player_level * 2

        for i in range(enemy_count):
            # 根据等级选择敌人类型
            if player_level <= 3:
                enemy_type = random.choice(["scav_weak", "scav_normal"])
            elif player_level <= 6:
                enemy_type = random.choice(["scav_normal", "scav_veteran", "pmc_grunt"])
            else:
                enemy_type = random.choice(["pmc_grunt", "pmc_elite"])

            # 小概率刷Boss
            if random.random() < 0.05 and not any(e.is_boss for e in self.enemies):
                enemy_type = "boss_killa"

            enemy_data = ENEMY_TYPES[enemy_type]
            enemy = Enemy(
                id=f"enemy_{i}",
                name=enemy_data["name"],
                hp=enemy_data["hp"],
                max_hp=enemy_data["hp"],
                armor_class=enemy_data["armor_class"],
                accuracy=enemy_data["accuracy"],
                weapon_id=enemy_data["weapon"],
                aggro_range=enemy_data["aggro_range"],
                loot_table=enemy_data["loot_table"],
                xp=enemy_data["xp"],
                is_boss=enemy_data.get("is_boss", False)
            )

            # 随机分配到非出生点/撤离点的区域
            zone_ids = [zid for zid, z in self.zones.items()
                       if not z.get("is_spawn") and not z.get("is_extract")]
            enemy.current_zone = random.choice(zone_ids)
            self.enemies.append(enemy)

    def generate_loot(self):
        """为每个区域生成战利品"""
        if self.loot_generated:
            return

        for zone_id, zone in self.zones.items():
            if zone.get("is_spawn") or zone.get("is_extract"):
                continue

            loot_tier = zone.get("loot_tier", 1)
            loot_count = random.randint(1, loot_tier * 2)
            zone["loot"] = []

            for _ in range(loot_count):
                # 根据稀有度权重选择物品
                if loot_tier >= 4:
                    weights = [0.3, 0.3, 0.2, 0.15, 0.05]
                elif loot_tier >= 3:
                    weights = [0.4, 0.3, 0.2, 0.08, 0.02]
                else:
                    weights = [0.5, 0.3, 0.15, 0.04, 0.01]

                rarity = random.choices(list(Rarity), weights=weights)[0]

                # 选择对应稀有度的物品
                items_of_rarity = [(k, v) for k, v in LOOT_ITEMS.items()
                                   if v["rarity"] == rarity]
                if items_of_rarity:
                    item_id, item_data = random.choice(items_of_rarity)
                    zone["loot"].append({
                        "id": f"loot_{random.randint(1000, 9999)}",
                        "item_id": item_id,
                        "data": item_data
                    })

        self.loot_generated = True

    def get_zone(self, zone_id: str) -> Optional[dict]:
        return self.zones.get(zone_id)

    def get_enemies_in_zone(self, zone_id: str) -> List[Enemy]:
        return [e for e in self.enemies if e.current_zone == zone_id and e.is_alive()]

    def tick(self):
        """时间流逝"""
        self.time_elapsed += 1

        # 敌人AI行动
        for enemy in self.enemies:
            if not enemy.is_alive():
                continue

            # 简单的巡逻逻辑
            if enemy.state == "patrol":
                zone = self.zones[enemy.current_zone]
                if random.random() < 0.3:  # 30%概率移动
                    connections = zone.get("connections", [])
                    if connections:
                        new_zone = random.choice(connections)
                        enemy.current_zone = new_zone

# ============== 主游戏类 ==============
class Game:
    """主游戏类"""
    def __init__(self):
        self.state = GameState.MAIN_MENU
        self.player = Player()
        self.current_raid: Optional[Raid] = None
        self.current_enemy: Optional[Enemy] = None
        self.messages: List[str] = []
        self.game_log: List[str] = []

        # 初始装备
        self._give_starting_gear()

    def _give_starting_gear(self):
        """给玩家初始装备"""
        # 初始武器
        pistol_data = WEAPONS["pistol_p226"]
        pistol = Weapon(
            id="start_pistol",
            name=pistol_data["name"],
            weight=pistol_data["weight"],
            value=pistol_data["value"],
            rarity=pistol_data["rarity"],
            damage=pistol_data["damage"],
            accuracy=pistol_data["accuracy"],
            fire_rate=pistol_data["fire_rate"],
            penetration=pistol_data["penetration"],
            ammo_type=pistol_data["ammo_type"],
            mag_size=pistol_data["mag_size"],
            current_ammo=pistol_data["mag_size"]
        )
        self.player.equipment.equip_weapon(pistol, "primary")

        # 初始护甲
        armor_data = ARMORS["armor_1_paca"]
        armor = Armor(
            id="start_armor",
            name=armor_data["name"],
            weight=armor_data["weight"],
            value=armor_data["value"],
            rarity=armor_data["rarity"],
            armor_class=armor_data["class"],
            durability=armor_data["durability"],
            max_durability=armor_data["max_durability"]
        )
        self.player.equipment.equip_armor(armor)

        # 初始消耗品
        for _ in range(2):
            bandage_data = CONSUMABLES["med_bandage"]
            bandage = Consumable(
                id=f"start_bandage_{_}",
                name=bandage_data["name"],
                weight=bandage_data["weight"],
                value=bandage_data["value"],
                rarity=bandage_data["rarity"],
                effect=bandage_data["effect"],
                use_time=bandage_data["use_time"],
                description=bandage_data["description"]
            )
            self.player.equipment.backpack.add_item(bandage)

    def add_message(self, msg: str):
        """添加消息"""
        self.messages.append(msg)
        self.game_log.append(msg)

    def clear_messages(self):
        """清空消息"""
        self.messages.clear()

    def start_raid(self, map_data: dict):
        """开始突击行动"""
        self.current_raid = Raid(map_data)
        self.current_raid.spawn_enemies(self.player.stats.level)
        self.current_raid.generate_loot()

        # 随机选择出生点
        spawn_zones = [zid for zid, z in self.current_raid.zones.items() if z.get("is_spawn")]
        self.player.current_zone = random.choice(spawn_zones)

        self.state = GameState.RAID
        self.add_message(f"=== 行动开始 ===")
        self.add_message(f"你已部署到 {map_data['name']}")
        self.add_message(f"当前位置: {self.current_raid.zones[self.player.current_zone]['name']}")
        self.add_message(f"时间限制: {self.current_raid.max_time} 回合")

    def move_to_zone(self, zone_id: str) -> Tuple[bool, str]:
        """移动到区域"""
        if self.state != GameState.RAID:
            return False, "当前不在行动中！"

        current_zone = self.current_raid.get_zone(self.player.current_zone)
        if zone_id not in current_zone.get("connections", []):
            return False, "无法到达该区域！"

        target_zone = self.current_raid.get_zone(zone_id)
        if not target_zone:
            return False, "该区域不存在！"

        # 消耗行动点
        ap_cost = 10 + int(target_zone.get("danger_level", 1) * 2)
        if self.player.action_points < ap_cost:
            return False, f"行动点不足！需要 {ap_cost} 点"

        self.player.action_points -= ap_cost
        self.player.current_zone = zone_id

        msg = f"你移动到了 {target_zone['name']}。"
        self.add_message(msg)

        # 检查是否有敌人
        enemies = self.current_raid.get_enemies_in_zone(zone_id)
        if enemies:
            self.current_enemy = enemies[0]
            self.state = GameState.COMBAT
            self.add_message(f"！遭遇敌人: {self.current_enemy.name}")
            self.add_message(f"敌人状态: HP {self.current_enemy.hp}/{self.current_enemy.max_hp}")

        # 时间流逝
        self.current_raid.tick()
        self.player.stats.tick()

        return True, msg

    def search_zone(self) -> Tuple[bool, str]:
        """搜索当前区域"""
        if self.state != GameState.RAID:
            return False, "当前不在行动中！"

        zone = self.current_raid.get_zone(self.player.current_zone)
        if not zone:
            return False, "区域错误！"

        ap_cost = 15
        if self.player.action_points < ap_cost:
            return False, f"行动点不足！需要 {ap_cost} 点"

        self.player.action_points -= ap_cost

        loot = zone.get("loot", [])
        if not loot:
            msg = "你仔细搜索了这个区域，但没有发现任何有价值的东西。"
            self.add_message(msg)
            return True, msg

        # 发现物品
        found_items = []
        for loot_entry in loot[:]:  # 使用副本迭代
            item_data = loot_entry["data"]

            if self.player.equipment.backpack.can_fit(None):
                item = LootItem(
                    id=loot_entry["id"],
                    name=item_data["name"],
                    weight=item_data["weight"],
                    value=item_data["value"],
                    rarity=item_data["rarity"],
                    item_type=item_data.get("type", "物资"),
                    description=item_data.get("description", "")
                )
                self.player.equipment.backpack.add_item(item)
                found_items.append(item)
                zone["loot"].remove(loot_entry)

        if found_items:
            msg = f"你发现了 {len(found_items)} 件物品：\n"
            for item in found_items:
                msg += f"  - [{item.rarity.cn_name}]{item.name} (价值: {item.value})\n"
        else:
            msg = "你的背包已满，无法携带更多物品。"

        self.add_message(msg)

        # 时间流逝
        self.current_raid.tick()
        self.player.stats.tick()

        return True, msg

    def combat_action(self, action: str, target: str = None) -> Tuple[bool, str]:
        """战斗行动"""
        if self.state != GameState.COMBAT:
            return False, "当前不在战斗中！"

        if not self.current_enemy or not self.current_enemy.is_alive():
            self.state = GameState.RAID
            return True, "战斗结束。"

        msg = ""
        success = True

        if action == "attack":
            damage, attack_msg = self.player.attack(self.current_enemy, target or "body")
            msg = attack_msg

            if not self.current_enemy.is_alive():
                # 敌人死亡
                self.player.add_xp(self.current_enemy.xp)
                self.player.kills += 1
                msg += f"\n获得 {self.current_enemy.xp} 经验值！"

                # 掉落物品
                loot_table = LOOT_TABLES.get(self.current_enemy.loot_table, [])
                for item_id, chance in loot_table:
                    if random.random() < chance:
                        if item_id in LOOT_ITEMS:
                            item_data = LOOT_ITEMS[item_id]
                            item = LootItem(
                                id=f"loot_{random.randint(1000, 9999)}",
                                name=item_data["name"],
                                weight=item_data["weight"],
                                value=item_data["value"],
                                rarity=item_data["rarity"]
                            )
                            if self.player.equipment.backpack.add_item(item):
                                msg += f"\n获得: {item.name}"

                self.current_enemy = None
                self.state = GameState.RAID

        elif action == "reload":
            success, reload_msg = self.player.reload()
            msg = reload_msg

        elif action == "heal":
            # 尝试使用医疗物品
            for item in self.player.equipment.backpack.get_all_items():
                if isinstance(item, Consumable) and "heal" in item.effect:
                    success, heal_msg = self.player.use_item(item.id)
                    msg = heal_msg
                    break
            else:
                msg = "没有可用的医疗物品！"
                success = False

        elif action == "flee":
            # 撤退
            if random.random() < 0.5:
                msg = "你成功脱离了战斗！"
                self.current_enemy = None
                self.state = GameState.RAID
            else:
                msg = "撤退失败！"
                success = False

        # 敌人回合
        if self.current_enemy and self.current_enemy.is_alive():
            enemy_weapon_data = WEAPONS.get(self.current_enemy.weapon_id, {})
            enemy_damage = enemy_weapon_data.get("damage", 20)
            enemy_accuracy = self.current_enemy.accuracy
            enemy_pen = enemy_weapon_data.get("penetration", 1)

            if random.random() < enemy_accuracy:
                # 随机选择命中部位
                zone = random.choice(list(DamageZone))
                damage, damage_msg = self.player.take_damage(enemy_damage, zone, enemy_pen)
                msg += f"\n\n{self.current_enemy.name}反击！{damage_msg}"

                if not self.player.stats.is_alive():
                    self.state = GameState.DEAD
                    msg += "\n\n你倒下了..."
            else:
                msg += f"\n\n{self.current_enemy.name}的攻击打偏了！"

        self.add_message(msg)
        return success, msg

    def try_extract(self) -> Tuple[bool, str]:
        """尝试撤离"""
        if self.state != GameState.RAID:
            return False, "当前不在行动中！"

        zone = self.current_raid.get_zone(self.player.current_zone)
        if not zone.get("is_extract"):
            return False, "当前区域没有撤离点！"

        condition = zone.get("extract_condition", {})
        extract_type = condition.get("type", "open")

        if extract_type == "wait":
            wait_time = condition.get("wait_time", 30)
            msg = f"撤离点需要等待 {wait_time} 秒..."
            self.add_message(msg)
            # 简化：直接成功
        elif extract_type == "drop_backpack":
            if self.player.equipment.backpack.get_all_items():
                self.player.equipment.backpack.clear()
                self.add_message("你丢弃了背包中的所有物品。")

        # 成功撤离
        self.state = GameState.EXTRACTED
        loot_value = self.player.equipment.backpack.get_total_value()
        self.player.total_loot_value += loot_value
        self.player.stats.money += loot_value

        msg = f"=== 撤离成功 ===\n"
        msg += f"获得物资价值: {loot_value}\n"
        msg += f"当前余额: {self.player.stats.money}"
        self.add_message(msg)

        return True, msg

    def handle_death(self):
        """处理死亡"""
        self.state = GameState.DEAD
        msg = "=== 行动失败 ===\n"
        msg += "你在行动中阵亡，丢失了背包中的所有物品...\n"

        # 保险箱物品保留
        secure_items = self.player.equipment.secure_container.get_all_items()
        if secure_items:
            msg += f"保险箱保留了 {len(secure_items)} 件物品。"

        # 丢失背包物品
        self.player.equipment.backpack.clear()

        # 重置装备（除了保险箱）
        self.player.equipment.primary_weapon = None
        self.player.equipment.armor = None
        self.player.equipment.helmet = None

        self.add_message(msg)

    def return_to_base(self):
        """返回基地"""
        self.state = GameState.BASE
        self.current_raid = None
        self.current_enemy = None

        # 重置玩家状态
        self.player.action_points = self.player.max_action_points
        self.player.stats = PlayerStats(
            money=self.player.stats.money,
            xp=self.player.stats.xp,
            level=self.player.stats.level
        )

# ============== 游戏界面 ==============
class GameUI:
    """游戏界面"""
    def __init__(self, game: Game):
        self.game = game

    def clear_screen(self):
        """清屏"""
        os.system('cls' if os.name == 'nt' else 'clear')

    def display_main_menu(self):
        """显示主菜单"""
        print("=" * 50)
        print("       暗区文字 (Dark Zone: Text)")
        print("     一款撤离射击文字游戏")
        print("=" * 50)
        print()
        print("1. 开始游戏")
        print("2. 查看仓库")
        print("3. 查看玩家状态")
        print("4. 游戏帮助")
        print("0. 退出游戏")
        print()

    def display_base(self):
        """显示基地界面"""
        print("=" * 50)
        print("       【基地】")
        print("=" * 50)
        print(f"玩家: {self.game.player.name} | 等级: {self.game.player.stats.level}")
        print(f"余额: {self.game.player.stats.money} 哈夫币")
        print(f"经验: {self.game.player.stats.xp}/{self.game.player.stats.level * 1000}")
        print("-" * 50)
        print("1. 开始行动 (工业区)")
        print("2. 整理装备")
        print("3. 查看仓库")
        print("4. 休息恢复")
        print("0. 返回主菜单")
        print()

    def display_raid(self):
        """显示行动界面"""
        raid = self.game.current_raid
        zone = raid.get_zone(self.game.player.current_zone)

        print("=" * 50)
        print(f"       【行动中 - {raid.map_data['name']}】")
        print("=" * 50)
        print(f"回合: {raid.time_elapsed}/{raid.max_time}")
        print(f"行动点: {self.game.player.action_points}/{self.game.player.max_action_points}")
        print("-" * 50)
        print(f"当前位置: {zone['name']}")
        print(f"危险等级: {'★' * zone.get('danger_level', 1)}")
        print(f"描述: {zone['description']}")
        print("-" * 50)

        # 显示连接的区域
        print("可前往区域:")
        for i, conn_id in enumerate(zone.get("connections", []), 1):
            conn_zone = raid.get_zone(conn_id)
            zone_type = ""
            if conn_zone.get("is_extract"):
                zone_type = " [撤离点]"
            print(f"  {i}. {conn_zone['name']}{zone_type}")

        print("-" * 50)
        print("行动选项:")
        print("  m [编号] - 移动到指定区域")
        print("  s - 搜索当前区域")
        print("  e - 尝试撤离 (如果在撤离点)")
        print("  i - 查看背包")
        print("  p - 查看状态")
        print("  q - 紧急撤离 (丢失所有背包物品)")
        print()

    def display_combat(self):
        """显示战斗界面"""
        enemy = self.game.current_enemy
        player = self.game.player

        print("=" * 50)
        print("       【战斗中】")
        print("=" * 50)

        # 敌人信息
        hp_bar = "█" * (enemy.hp * 20 // enemy.max_hp) + "░" * (20 - enemy.hp * 20 // enemy.max_hp)
        print(f"敌人: {enemy.name}")
        print(f"HP: [{hp_bar}] {enemy.hp}/{enemy.max_hp}")
        if enemy.is_boss:
            print("  ★ BOSS ★")
        print()

        # 玩家信息
        total_hp = player.stats.get_total_hp()
        max_hp = player.stats.get_max_hp()
        hp_bar = "█" * (total_hp * 20 // max_hp) + "░" * (20 - total_hp * 20 // max_hp)
        print(f"你的HP: [{hp_bar}] {total_hp}/{max_hp}")

        weapon = player.equipment.primary_weapon
        if weapon:
            print(f"武器: {weapon.name} | 弹药: {weapon.current_ammo}/{weapon.mag_size}")
        print("-" * 50)

        print("战斗指令:")
        print("  a [head/body/legs] - 攻击 (瞄准部位)")
        print("  r - 换弹")
        print("  h - 使用医疗物品")
        print("  f - 撤退")
        print()

    def display_player_status(self):
        """显示玩家状态"""
        stats = self.game.player.stats
        eq = self.game.player.equipment

        print("=" * 50)
        print("       【玩家状态】")
        print("=" * 50)
        print(f"等级: {stats.level} | 经验: {stats.xp}/{stats.level * 1000}")
        print(f"余额: {stats.money} 哈夫币")
        print(f"击杀数: {self.game.player.kills}")
        print(f"累计物资价值: {self.game.player.total_loot_value}")
        print("-" * 50)

        print("身体状态:")
        for zone in DamageZone:
            part = stats.get_body_part(zone)
            status = "正常"
            if part.is_broken:
                status = "已损坏"
            elif part.hp < part.max_hp * 0.3:
                status = "严重受伤"
            elif part.hp < part.max_hp:
                status = "轻伤"
            print(f"  {zone.cn_name}: {part.hp}/{part.max_hp} [{status}]")

        print("-" * 50)
        print("装备:")
        if eq.primary_weapon:
            print(f"  主武器: {eq.primary_weapon.name}")
        if eq.armor:
            print(f"  护甲: {eq.armor.name} (耐久: {eq.armor.durability}/{eq.armor.max_durability})")
        if eq.helmet:
            print(f"  头盔: {eq.helmet.name}")

        print(f"  背包负重: {eq.backpack.get_total_weight():.1f}kg")
        print()

    def display_backpack(self):
        """显示背包"""
        backpack = self.game.player.equipment.backpack
        secure = self.game.player.equipment.secure_container

        print("=" * 50)
        print("       【背包】")
        print("=" * 50)

        items = backpack.get_all_items()
        if items:
            total_value = 0
            for i, item in enumerate(items, 1):
                rarity_color = item.rarity.cn_name
                print(f"  {i}. [{rarity_color}]{item.name}")
                print(f"     重量: {item.weight}kg | 价值: {item.value}")
                total_value += item.value
            print("-" * 50)
            print(f"总价值: {total_value} 哈夫币")
            print(f"总重量: {backpack.get_total_weight():.1f}kg")
        else:
            print("  (空)")

        print("-" * 50)
        print("【保险箱】")
        secure_items = secure.get_all_items()
        if secure_items:
            for item in secure_items:
                print(f"  [{item.rarity.cn_name}]{item.name}")
        else:
            print("  (空)")
        print()

    def display_help(self):
        """显示帮助"""
        print("=" * 50)
        print("       【游戏帮助】")
        print("=" * 50)
        print("""
【游戏目标】
进入战区搜集高价值物资，然后成功撤离。

【核心机制】
- 撤离射击: 进入地图 → 搜刮物资 → 撤离
- 死亡惩罚: 死亡会丢失背包中所有物品
- 保险箱: 保险箱中的物品死亡后保留

【战斗系统】
- 身体部位: 头部(2.5x伤害)、胸部(1x)、四肢(0.7x)
- 护甲减伤: 根据护甲等级减少伤害
- 瞄准系统: 可选择瞄准不同部位

【物品稀有度】
灰色(普通) < 绿色 < 蓝色 < 紫色 < 金色(传说)

【行动点】
移动和搜索会消耗行动点，行动点耗尽会进入疲劳状态。
        """)

    def display_messages(self):
        """显示消息"""
        if self.game.messages:
            print("-" * 50)
            for msg in self.game.messages:
                print(msg)
            print("-" * 50)
            self.game.clear_messages()

    def run(self):
        """运行游戏主循环"""
        while True:
            self.clear_screen()

            if self.game.state == GameState.MAIN_MENU:
                self.display_main_menu()
                self.display_messages()
                choice = input("请选择: ").strip()

                if choice == "1":
                    self.game.state = GameState.BASE
                elif choice == "2":
                    self.display_backpack()
                    input("按回车继续...")
                elif choice == "3":
                    self.display_player_status()
                    input("按回车继续...")
                elif choice == "4":
                    self.display_help()
                    input("按回车继续...")
                elif choice == "0":
                    print("感谢游玩！")
                    break

            elif self.game.state == GameState.BASE:
                self.display_base()
                self.display_messages()
                choice = input("请选择: ").strip()

                if choice == "1":
                    self.game.start_raid(MAP_INDUSTRIAL)
                elif choice == "2":
                    self.display_backpack()
                    input("按回车继续...")
                elif choice == "3":
                    print("仓库功能开发中...")
                    input("按回车继续...")
                elif choice == "4":
                    self.game.player.stats = PlayerStats(
                        money=self.game.player.stats.money,
                        xp=self.game.player.stats.xp,
                        level=self.game.player.stats.level
                    )
                    self.game.add_message("你休息了一段时间，状态已恢复。")
                elif choice == "0":
                    self.game.state = GameState.MAIN_MENU

            elif self.game.state == GameState.RAID:
                self.display_raid()
                self.display_messages()
                cmd = input("输入指令: ").strip().lower()

                if cmd.startswith("m "):
                    try:
                        zone_idx = int(cmd[2:]) - 1
                        zone = self.game.current_raid.get_zone(self.game.player.current_zone)
                        connections = zone.get("connections", [])
                        if 0 <= zone_idx < len(connections):
                            self.game.move_to_zone(connections[zone_idx])
                    except ValueError:
                        self.game.add_message("无效的指令！")

                elif cmd == "s":
                    self.game.search_zone()

                elif cmd == "e":
                    self.game.try_extract()

                elif cmd == "i":
                    self.display_backpack()
                    input("按回车继续...")

                elif cmd == "p":
                    self.display_player_status()
                    input("按回车继续...")

                elif cmd == "q":
                    self.game.player.equipment.backpack.clear()
                    self.game.state = GameState.BASE
                    self.game.add_message("你进行了紧急撤离，丢失了所有背包物品。")

                # 检查死亡
                if not self.game.player.stats.is_alive():
                    self.game.handle_death()

                # 检查撤离成功
                if self.game.state == GameState.EXTRACTED:
                    input("按回车返回基地...")
                    self.game.return_to_base()

            elif self.game.state == GameState.COMBAT:
                self.display_combat()
                self.display_messages()
                cmd = input("输入指令: ").strip().lower()

                if cmd.startswith("a "):
                    target = cmd[2:] if len(cmd) > 2 else "body"
                    self.game.combat_action("attack", target)
                elif cmd == "a":
                    self.game.combat_action("attack", "body")
                elif cmd == "r":
                    self.game.combat_action("reload")
                elif cmd == "h":
                    self.game.combat_action("heal")
                elif cmd == "f":
                    self.game.combat_action("flee")

                # 检查战斗结束
                if self.game.state == GameState.RAID:
                    pass  # 继续行动
                elif self.game.state == GameState.DEAD:
                    self.game.handle_death()
                    input("按回车返回基地...")
                    self.game.return_to_base()

            elif self.game.state == GameState.DEAD:
                self.display_messages()
                input("按回车返回基地...")
                self.game.return_to_base()


# ============== 主程序入口 ==============
def main():
    """主程序入口"""
    game = Game()
    ui = GameUI(game)
    ui.run()


if __name__ == "__main__":
    main()