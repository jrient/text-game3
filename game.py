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
import math

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
    """身体部位 - 简化为头/胸/腿"""
    HEAD = ("头部", 2.0, "致命伤害！", 0.15)      # 高伤害倍率，低命中率
    CHEST = ("胸部", 1.0, "", 0.55)                # 标准伤害，高命中率
    LEGS = ("腿部", 0.7, "移动速度下降。", 0.30)   # 低伤害，低命中率，无护甲

    def __init__(self, cn_name, multiplier, effect_msg, base_hit_chance):
        self.cn_name = cn_name
        self.multiplier = multiplier
        self.effect_msg = effect_msg
        self.base_hit_chance = base_hit_chance  # 基础命中率

# ============== 干员系统（三角洲行动核心）==============
class OperatorClass(Enum):
    """干员兵种 - 三角洲行动四兵种"""
    ASSAULT = ("突击", "assault", "高机动突击，擅长近距离作战")
    SUPPORT = ("支援", "support", "提供火力支援和团队补给")
    RECON = ("侦查", "recon", "情报收集，远程精确打击")
    ENGINEER = ("工程", "engineer", "载具操作，爆破与维修")

    def __init__(self, cn_name, code, desc):
        self.cn_name = cn_name
        self.code = code
        self.desc = desc

# 干员技能定义
OPERATOR_SKILLS = {
    "assault": {
        "tactical_sprint": {
            "name": "战术冲刺",
            "description": "短时间内大幅提升移动速度",
            "cooldown": 3,
            "duration": 2,
            "effect": {"speed_bonus": 2, "dodge_bonus": 0.3}
        },
        "frag_grenade": {
            "name": "破片手雷",
            "description": "投掷破片手雷造成范围伤害",
            "cooldown": 4,
            "damage": 150,
            "radius": 3
        },
        "breach_charge": {
            "name": "爆破炸药",
            "description": "在墙壁或门上放置炸药进行爆破",
            "cooldown": 5,
            "damage": 200
        }
    },
    "support": {
        "ammo_bag": {
            "name": "弹药补给包",
            "description": "为队友补充弹药",
            "cooldown": 5,
            "effect": {"ammo_refill": True, "uses": 3}
        },
        "med_bag": {
            "name": "医疗包",
            "description": "为队友恢复生命值",
            "cooldown": 4,
            "effect": {"heal_amount": 50, "uses": 3}
        },
        "shield_deploy": {
            "name": "部署护盾",
            "description": "部署一个可移动的掩体护盾",
            "cooldown": 6,
            "effect": {"shield_hp": 200}
        }
    },
    "recon": {
        "sensor_dart": {
            "name": "侦察飞镖",
            "description": "发射侦察飞镖标记敌人位置",
            "cooldown": 3,
            "duration": 5,
            "effect": {"reveal_enemies": True, "range": 4}
        },
        "motion_sensor": {
            "name": "动作感应器",
            "description": "部署感应器侦测移动的敌人",
            "cooldown": 4,
            "duration": 6,
            "effect": {"detect_motion": True, "range": 5}
        },
        "uav_scan": {
            "name": "无人机扫描",
            "description": "释放无人机扫描附近区域",
            "cooldown": 8,
            "duration": 4,
            "effect": {"scan_area": True, "range": 6}
        }
    },
    "engineer": {
        "repair_tool": {
            "name": "维修工具",
            "description": "修复载具和装备",
            "cooldown": 3,
            "effect": {"repair_amount": 50}
        },
        "at_mine": {
            "name": "反坦克地雷",
            "description": "部署反载具地雷",
            "cooldown": 5,
            "damage": 500,
            "effect": {"vehicle_damage_mult": 2.0}
        },
        "tow_missile": {
            "name": "线导导弹",
            "description": "发射线导反坦克导弹",
            "cooldown": 6,
            "damage": 400,
            "effect": {"guided": True, "vehicle_damage_mult": 1.5}
        }
    }
}

# 干员定义
OPERATORS = {
    "operator_wyatt": {
        "name": "怀亚特",
        "class": OperatorClass.ASSAULT,
        "description": "前特种部队成员，擅长快速突击作战",
        "primary_skill": "tactical_sprint",
        "secondary_skill": "frag_grenade",
        "bonus": {"damage": 0.1, "speed": 0.15}
    },
    "operator_luna": {
        "name": "露娜",
        "class": OperatorClass.RECON,
        "description": "资深狙击手，能精准定位敌人",
        "primary_skill": "sensor_dart",
        "secondary_skill": "motion_sensor",
        "bonus": {"accuracy": 0.15, "headshot_damage": 0.2}
    },
    "operator_hack": {
        "name": "哈克",
        "class": OperatorClass.ENGINEER,
        "description": "技术专家，精通载具和爆破",
        "primary_skill": "repair_tool",
        "secondary_skill": "at_mine",
        "bonus": {"vehicle_damage": 0.2, "repair_speed": 0.3}
    },
    "operator_doc": {
        "name": "医生",
        "class": OperatorClass.SUPPORT,
        "description": "战地医疗兵，提供关键支援",
        "primary_skill": "med_bag",
        "secondary_skill": "ammo_bag",
        "bonus": {"heal_bonus": 0.3, "revive_speed": 0.5}
    },
    "operator_smoke": {
        "name": "烟鬼",
        "class": OperatorClass.ASSAULT,
        "description": "突击专家，擅长爆破突入",
        "primary_skill": "breach_charge",
        "secondary_skill": "tactical_sprint",
        "bonus": {"explosive_damage": 0.25, "speed": 0.1}
    },
    "operator_stinger": {
        "name": "毒刺",
        "class": OperatorClass.RECON,
        "description": "情报官，无人侦察专家",
        "primary_skill": "uav_scan",
        "secondary_skill": "sensor_dart",
        "bonus": {"detection_range": 0.3, "intel_bonus": True}
    },
    "operator_tower": {
        "name": "塔楼",
        "class": OperatorClass.SUPPORT,
        "description": "重装支援，擅长阵地防御",
        "primary_skill": "shield_deploy",
        "secondary_skill": "med_bag",
        "bonus": {"armor_bonus": 0.2, "suppression": 0.3}
    },
    "operator_saw": {
        "name": "电锯",
        "class": OperatorClass.ENGINEER,
        "description": "反载具专家，精通反坦克武器",
        "primary_skill": "tow_missile",
        "secondary_skill": "repair_tool",
        "bonus": {"vehicle_damage": 0.35, "explosive_damage": 0.15}
    }
}

# ============== 载具系统（三角洲行动核心）==============
class VehicleType(Enum):
    """载具类型"""
    HELICOPTER = ("直升机", "helicopter", "空中载具，快速机动")
    TANK = ("坦克", "tank", "重型装甲，火力强大")
    APC = ("装甲车", "apc", "步兵战车，平衡机动与防护")

    def __init__(self, cn_name, code, desc):
        self.cn_name = cn_name
        self.code = code
        self.desc = desc

# 载具数据
VEHICLES = {
    "heli_little_bird": {
        "name": "小鸟直升机",
        "type": VehicleType.HELICOPTER,
        "hp": 800,
        "max_hp": 800,
        "armor": 2,
        "seats": 4,  # 1驾驶员 + 3乘客
        "speed": 10,
        "weapons": ["minigun"],
        "description": "轻型侦察直升机，快速机动",
        "value": 50000
    },
    "heli_black_hawk": {
        "name": "黑鹰直升机",
        "type": VehicleType.HELICOPTER,
        "hp": 1500,
        "max_hp": 1500,
        "armor": 3,
        "seats": 8,  # 1驾驶员 + 2炮手 + 5乘客
        "speed": 8,
        "weapons": ["minigun", "rocket_pod"],
        "description": "中型运输直升机，可装载小队",
        "value": 100000
    },
    "tank_m1a2": {
        "name": "M1A2主战坦克",
        "type": VehicleType.TANK,
        "hp": 3000,
        "max_hp": 3000,
        "armor": 6,
        "seats": 3,  # 驾驶员+炮手+车长
        "speed": 4,
        "weapons": ["main_cannon", "coaxial_mg"],
        "description": "重型主战坦克，火力与防护顶级",
        "value": 500000
    },
    "tank_t90": {
        "name": "T-90主战坦克",
        "type": VehicleType.TANK,
        "hp": 2800,
        "max_hp": 2800,
        "armor": 5,
        "seats": 3,
        "speed": 5,
        "weapons": ["main_cannon", "coaxial_mg", "atgm"],
        "description": "俄制主战坦克，配备反坦克导弹",
        "value": 450000
    },
    "apc_m2_bradley": {
        "name": "M2步兵战车",
        "type": VehicleType.APC,
        "hp": 1200,
        "max_hp": 1200,
        "armor": 4,
        "seats": 6,  # 3车组 + 3步兵
        "speed": 6,
        "weapons": ["autocannon", "tow_launcher"],
        "description": "步兵战车，可运载小队",
        "value": 200000
    },
    "apc_bmp3": {
        "name": "BMP-3步兵战车",
        "type": VehicleType.APC,
        "hp": 1000,
        "max_hp": 1000,
        "armor": 3,
        "seats": 7,  # 3车组 + 4步兵
        "speed": 7,
        "weapons": ["autocannon", "coaxial_mg", "atgm"],
        "description": "俄制步兵战车，火力配置丰富",
        "value": 180000
    },
    "apc_stryker": {
        "name": "斯崔克装甲车",
        "type": VehicleType.APC,
        "hp": 800,
        "max_hp": 800,
        "armor": 3,
        "seats": 9,  # 2车组 + 7步兵
        "speed": 8,
        "weapons": ["remote_mg", "grenade_launcher"],
        "description": "轮式装甲车，高机动性",
        "value": 150000
    }
}

# 载具武器数据
VEHICLE_WEAPONS = {
    "minigun": {
        "name": "米尼岗机枪",
        "damage": 50,
        "fire_rate": 10,
        "accuracy": 0.6,
        "range": 5,
        "ammo": 1000,
        "reload_time": 5
    },
    "rocket_pod": {
        "name": "火箭弹巢",
        "damage": 200,
        "fire_rate": 1,
        "accuracy": 0.7,
        "range": 8,
        "ammo": 14,
        "reload_time": 30,
        "splash": True,
        "splash_radius": 2
    },
    "main_cannon": {
        "name": "主炮",
        "damage": 800,
        "fire_rate": 1,
        "accuracy": 0.85,
        "range": 10,
        "ammo": 40,
        "reload_time": 6,
        "penetration": 6
    },
    "coaxial_mg": {
        "name": "同轴机枪",
        "damage": 40,
        "fire_rate": 5,
        "accuracy": 0.7,
        "range": 6,
        "ammo": 2000,
        "reload_time": 10
    },
    "autocannon": {
        "name": "机关炮",
        "damage": 150,
        "fire_rate": 3,
        "accuracy": 0.75,
        "range": 7,
        "ammo": 300,
        "reload_time": 8,
        "penetration": 4
    },
    "tow_launcher": {
        "name": "TOW导弹发射器",
        "damage": 500,
        "fire_rate": 1,
        "accuracy": 0.9,
        "range": 12,
        "ammo": 4,
        "reload_time": 15,
        "guided": True
    },
    "atgm": {
        "name": "反坦克导弹",
        "damage": 450,
        "fire_rate": 1,
        "accuracy": 0.85,
        "range": 10,
        "ammo": 4,
        "reload_time": 12,
        "guided": True
    },
    "remote_mg": {
        "name": "遥控武器站",
        "damage": 35,
        "fire_rate": 6,
        "accuracy": 0.65,
        "range": 5,
        "ammo": 500,
        "reload_time": 8
    },
    "grenade_launcher": {
        "name": "榴弹发射器",
        "damage": 100,
        "fire_rate": 2,
        "accuracy": 0.6,
        "range": 4,
        "ammo": 100,
        "reload_time": 10,
        "splash": True,
        "splash_radius": 1
    }
}

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
    },
    # ===== 新增武器 =====
    "pistol_glock17": {
        "name": "Glock17手枪",
        "type": "手枪",
        "damage": 30,
        "accuracy": 0.88,
        "fire_rate": 3,
        "penetration": 1,
        "ammo_type": "9mm",
        "mag_size": 17,
        "weight": 0.9,
        "value": 400,
        "rarity": Rarity.COMMON
    },
    "pistol_deagle": {
        "name": "沙漠之鹰",
        "type": "手枪",
        "damage": 65,
        "accuracy": 0.70,
        "fire_rate": 1,
        "penetration": 3,
        "ammo_type": ".50AE",
        "mag_size": 7,
        "weight": 2.0,
        "value": 3000,
        "rarity": Rarity.RARE
    },
    "smg_vector": {
        "name": "KRISS Vector冲锋枪",
        "type": "冲锋枪",
        "damage": 25,
        "accuracy": 0.72,
        "fire_rate": 6,
        "penetration": 1,
        "ammo_type": "9mm",
        "mag_size": 33,
        "weight": 2.7,
        "value": 3500,
        "rarity": Rarity.UNCOMMON
    },
    "smg_pp19": {
        "name": "PP-19野牛冲锋枪",
        "type": "冲锋枪",
        "damage": 26,
        "accuracy": 0.60,
        "fire_rate": 5,
        "penetration": 2,
        "ammo_type": "9mm",
        "mag_size": 64,
        "weight": 3.0,
        "value": 2500,
        "rarity": Rarity.UNCOMMON
    },
    "ar_hk416": {
        "name": "HK416突击步枪",
        "type": "突击步枪",
        "damage": 44,
        "accuracy": 0.82,
        "fire_rate": 4,
        "penetration": 3,
        "ammo_type": "5.56x45mm",
        "mag_size": 30,
        "weight": 3.2,
        "value": 7000,
        "rarity": Rarity.RARE
    },
    "ar_scarh": {
        "name": "SCAR-H战斗步枪",
        "type": "突击步枪",
        "damage": 55,
        "accuracy": 0.78,
        "fire_rate": 3,
        "penetration": 4,
        "ammo_type": "7.62x51mm",
        "mag_size": 20,
        "weight": 3.8,
        "value": 9000,
        "rarity": Rarity.EPIC
    },
    "dmr_svd": {
        "name": "SVD射手步枪",
        "type": "射手步枪",
        "damage": 70,
        "accuracy": 0.90,
        "fire_rate": 2,
        "penetration": 4,
        "ammo_type": "7.62x54mmR",
        "mag_size": 10,
        "weight": 4.3,
        "value": 6000,
        "rarity": Rarity.RARE
    },
    "dmr_mk14": {
        "name": "Mk14 EBR射手步枪",
        "type": "射手步枪",
        "damage": 65,
        "accuracy": 0.88,
        "fire_rate": 2,
        "penetration": 4,
        "ammo_type": "7.62x51mm",
        "mag_size": 20,
        "weight": 5.1,
        "value": 12000,
        "rarity": Rarity.EPIC
    },
    "sniper_awm": {
        "name": "AWM狙击步枪",
        "type": "狙击步枪",
        "damage": 110,
        "accuracy": 0.99,
        "fire_rate": 1,
        "penetration": 5,
        "ammo_type": ".338 Lapua",
        "mag_size": 5,
        "weight": 6.5,
        "value": 25000,
        "rarity": Rarity.LEGENDARY
    },
    "lmg_pkm": {
        "name": "PKM轻机枪",
        "type": "轻机枪",
        "damage": 50,
        "accuracy": 0.55,
        "fire_rate": 6,
        "penetration": 3,
        "ammo_type": "7.62x54mmR",
        "mag_size": 100,
        "weight": 7.5,
        "value": 8000,
        "rarity": Rarity.RARE
    },
    "lmg_m249": {
        "name": "M249轻机枪",
        "type": "轻机枪",
        "damage": 45,
        "accuracy": 0.50,
        "fire_rate": 7,
        "penetration": 3,
        "ammo_type": "5.56x45mm",
        "mag_size": 200,
        "weight": 10.0,
        "value": 15000,
        "rarity": Rarity.EPIC
    },
    "shotgun_saiga12": {
        "name": "Saiga-12霰弹枪",
        "type": "霰弹枪",
        "damage": 100,
        "accuracy": 0.45,
        "fire_rate": 3,
        "penetration": 1,
        "ammo_type": "12ga",
        "mag_size": 10,
        "weight": 3.8,
        "value": 4000,
        "rarity": Rarity.UNCOMMON
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

# 背包类型 - 不同大小和价格
BACKPACKS = {
    "bag_small": {
        "name": "小型背包",
        "rows": 4,
        "cols": 3,
        "weight": 0.5,
        "value": 500,
        "rarity": Rarity.COMMON,
        "description": "12格背包，基础存储空间"
    },
    "bag_medium": {
        "name": "中型背包",
        "rows": 5,
        "cols": 4,
        "weight": 1.0,
        "value": 2000,
        "rarity": Rarity.UNCOMMON,
        "description": "20格背包，标准存储空间"
    },
    "bag_large": {
        "name": "大型背包",
        "rows": 6,
        "cols": 5,
        "weight": 1.5,
        "value": 5000,
        "rarity": Rarity.RARE,
        "description": "30格背包，扩展存储空间"
    },
    "bag_tactical": {
        "name": "战术背包",
        "rows": 7,
        "cols": 5,
        "weight": 2.0,
        "value": 10000,
        "rarity": Rarity.EPIC,
        "description": "35格背包，专业战术存储"
    },
    "bag_military": {
        "name": "军用背包",
        "rows": 8,
        "cols": 6,
        "weight": 2.5,
        "value": 20000,
        "rarity": Rarity.LEGENDARY,
        "description": "48格背包，最大存储容量"
    }
}

CONSUMABLES = {
    "med_bandage": {
        "name": "绷带",
        "type": "医疗",
        "effect": {"heal": 15, "stop_bleed": True},
        "use_time": 2,
        "weight": 0.1,
        "value": 100,
        "rarity": Rarity.COMMON,
        "description": "止血并恢复少量生命值"
    },
    "med_ai2": {
        "name": "AI-2急救包",
        "type": "医疗",
        "effect": {"heal": 50, "stop_bleed": True},
        "use_time": 4,
        "weight": 0.3,
        "value": 300,
        "rarity": Rarity.UNCOMMON,
        "description": "恢复中等生命值，可止血"
    },
    "med_ifak": {
        "name": "IFAK医疗包",
        "type": "医疗",
        "effect": {"heal": 100, "stop_bleed": True},
        "use_time": 6,
        "weight": 0.5,
        "value": 800,
        "rarity": Rarity.RARE,
        "description": "恢复大量生命值，可止血"
    },
    "med_surgery": {
        "name": "手术包",
        "type": "医疗",
        "effect": {"heal": 30, "fix_bodypart": True, "stop_bleed": True},
        "use_time": 15,
        "weight": 1.0,
        "value": 2000,
        "rarity": Rarity.EPIC,
        "description": "修复断裂的身体部位并止血"
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
    },
    "repair_armor_small": {
        "name": "护甲修理包(小)",
        "type": "工具",
        "effect": {"repair_armor": 15},
        "use_time": 5,
        "weight": 0.2,
        "value": 200,
        "rarity": Rarity.COMMON,
        "description": "修复护甲耐久度15点"
    },
    "repair_armor_large": {
        "name": "护甲修理包(大)",
        "type": "工具",
        "effect": {"repair_armor": 40},
        "use_time": 8,
        "weight": 0.5,
        "value": 500,
        "rarity": Rarity.UNCOMMON,
        "description": "修复护甲耐久度40点"
    },
    # ===== 新增消耗品 =====
    "med_salewa": {
        "name": "Salewa急救包",
        "type": "医疗",
        "effect": {"heal": 80, "stop_bleed": True},
        "use_time": 5,
        "weight": 0.4,
        "value": 600,
        "rarity": Rarity.UNCOMMON,
        "description": "军用急救包，恢复大量生命值"
    },
    "med_grizzly": {
        "name": "灰熊急救箱",
        "type": "医疗",
        "effect": {"heal": 200, "stop_bleed": True, "fix_bodypart": True},
        "use_time": 12,
        "weight": 1.5,
        "value": 3000,
        "rarity": Rarity.EPIC,
        "description": "大型急救箱，全面治疗"
    },
    "stim_adrenaline": {
        "name": "肾上腺素注射器",
        "type": "药物",
        "effect": {"stamina_boost": 50, "pain_relief": 120, "ap_boost": 20},
        "use_time": 1,
        "weight": 0.1,
        "value": 1500,
        "rarity": Rarity.RARE,
        "description": "快速恢复耐力，暂时提升行动力"
    },
    "stim_propital": {
        "name": "Propital再生注射器",
        "type": "药物",
        "effect": {"heal": 30, "regen": 5, "regen_duration": 5},
        "use_time": 1,
        "weight": 0.1,
        "value": 2000,
        "rarity": Rarity.RARE,
        "description": "持续恢复生命值5回合"
    },
    "grenade_frag": {
        "name": "破片手雷",
        "type": "战术",
        "effect": {"grenade_damage": 120, "grenade_type": "frag"},
        "use_time": 1,
        "weight": 0.5,
        "value": 800,
        "rarity": Rarity.UNCOMMON,
        "description": "高杀伤破片手雷"
    },
    "grenade_flash": {
        "name": "闪光弹",
        "type": "战术",
        "effect": {"grenade_type": "flash", "stun_duration": 2},
        "use_time": 1,
        "weight": 0.3,
        "value": 500,
        "rarity": Rarity.COMMON,
        "description": "致盲敌人2回合，降低命中率"
    },
    "grenade_smoke": {
        "name": "烟雾弹",
        "type": "战术",
        "effect": {"grenade_type": "smoke", "flee_bonus": 0.3},
        "use_time": 1,
        "weight": 0.3,
        "value": 400,
        "rarity": Rarity.COMMON,
        "description": "释放烟雾，大幅提高撤退成功率"
    },
    "food_mre": {
        "name": "军用口粮MRE",
        "type": "食物",
        "effect": {"energy": 40, "hydration": 15},
        "use_time": 4,
        "weight": 0.5,
        "value": 200,
        "rarity": Rarity.COMMON,
        "description": "标准军用即食口粮"
    },
    "food_tushonka": {
        "name": "图申卡牛肉罐头",
        "type": "食物",
        "effect": {"energy": 55, "hydration": 10},
        "use_time": 5,
        "weight": 0.6,
        "value": 350,
        "rarity": Rarity.UNCOMMON,
        "description": "经典俄制牛肉罐头，能量充沛"
    },
    "drink_water": {
        "name": "瓶装水",
        "type": "饮品",
        "effect": {"hydration": 50},
        "use_time": 2,
        "weight": 0.5,
        "value": 100,
        "rarity": Rarity.COMMON,
        "description": "干净的瓶装水"
    },
    "drink_juice": {
        "name": "果汁饮料",
        "type": "饮品",
        "effect": {"hydration": 35, "energy": 10},
        "use_time": 2,
        "weight": 0.4,
        "value": 180,
        "rarity": Rarity.COMMON,
        "description": "甜味果汁，补充水分和少量能量"
    },
    "ammo_box_9mm": {
        "name": "9mm弹药箱",
        "type": "弹药",
        "effect": {"reload_weapon": True, "ammo_type": "9mm"},
        "use_time": 3,
        "weight": 0.3,
        "value": 200,
        "rarity": Rarity.COMMON,
        "description": "9mm弹药补给箱"
    },
    "ammo_box_556": {
        "name": "5.56mm弹药箱",
        "type": "弹药",
        "effect": {"reload_weapon": True, "ammo_type": "5.56x45mm"},
        "use_time": 3,
        "weight": 0.4,
        "value": 350,
        "rarity": Rarity.UNCOMMON,
        "description": "5.56mm弹药补给箱"
    },
    "ammo_box_762": {
        "name": "7.62mm弹药箱",
        "type": "弹药",
        "effect": {"reload_weapon": True, "ammo_type": "7.62x51mm"},
        "use_time": 3,
        "weight": 0.5,
        "value": 500,
        "rarity": Rarity.UNCOMMON,
        "description": "7.62mm弹药补给箱"
    }
}

LOOT_ITEMS = {
    # ===== 灰色物品 - 最常见 =====
    "loot_bolts": {
        "name": "螺丝零件",
        "type": "物资",
        "grid": 1,
        "value": 50,
        "rarity": Rarity.COMMON,
        "description": "普通的机械零件，随处可见"
    },
    "loot_tape": {
        "name": "工业胶带",
        "type": "物资",
        "grid": 1,
        "value": 80,
        "rarity": Rarity.COMMON,
        "description": "用途广泛的胶带，修补利器"
    },
    "loot_wire": {
        "name": "电线束",
        "type": "物资",
        "grid": 1,
        "value": 120,
        "rarity": Rarity.COMMON,
        "description": "一捆铜芯电线，可回收利用"
    },
    "loot_battery_old": {
        "name": "废旧电池",
        "type": "物资",
        "grid": 1,
        "value": 150,
        "rarity": Rarity.COMMON,
        "description": "还能勉强使用的旧电池"
    },
    "loot_plastic": {
        "name": "塑料制品",
        "type": "物资",
        "grid": 1,
        "value": 60,
        "rarity": Rarity.COMMON,
        "description": "可回收的塑料材料"
    },
    "loot_cardboard": {
        "name": "纸箱",
        "type": "物资",
        "grid": 1,
        "value": 40,
        "rarity": Rarity.COMMON,
        "description": "废弃的包装纸箱"
    },
    "loot_rags": {
        "name": "破旧衣物",
        "type": "物资",
        "grid": 1,
        "value": 70,
        "rarity": Rarity.COMMON,
        "description": "还能当抹布使用的旧衣物"
    },
    "loot_glass": {
        "name": "玻璃碎片",
        "type": "物资",
        "grid": 1,
        "value": 30,
        "rarity": Rarity.COMMON,
        "description": "锋利的玻璃碎片，小心割伤"
    },

    # ===== 绿色物品 - 常见 =====
    "loot_circuit_board": {
        "name": "印刷电路板",
        "type": "物资",
        "grid": 1,
        "value": 800,
        "rarity": Rarity.UNCOMMON,
        "description": "可回收的电路板，含少量贵金属"
    },
    "loot_led_tube": {
        "name": "LED灯管",
        "type": "物资",
        "grid": 1,
        "value": 600,
        "rarity": Rarity.UNCOMMON,
        "description": "节能LED照明灯管"
    },
    "loot_phone_battery": {
        "name": "手机电池",
        "type": "物资",
        "grid": 1,
        "value": 500,
        "rarity": Rarity.UNCOMMON,
        "description": "通用的锂离子电池"
    },
    "loot_adapter": {
        "name": "转换插头",
        "type": "物资",
        "grid": 1,
        "value": 700,
        "rarity": Rarity.UNCOMMON,
        "description": "多功能电源转换插头"
    },
    "loot_alcohol": {
        "name": "消毒酒精",
        "type": "医疗",
        "grid": 1,
        "value": 450,
        "rarity": Rarity.UNCOMMON,
        "description": "医用消毒酒精，必备品"
    },
    "loot_thermometer": {
        "name": "额温枪",
        "type": "医疗",
        "grid": 1,
        "value": 600,
        "rarity": Rarity.UNCOMMON,
        "description": "红外线体温测量仪"
    },
    "loot_solid_fuel": {
        "name": "固体燃料",
        "type": "物资",
        "grid": 1,
        "value": 400,
        "rarity": Rarity.UNCOMMON,
        "description": "便携式固体燃料块"
    },
    "loot_multi_battery": {
        "name": "多用途电池",
        "type": "物资",
        "grid": 1,
        "value": 550,
        "rarity": Rarity.UNCOMMON,
        "description": "可用于多种设备的电池"
    },
    "loot_candles": {
        "name": "盒装蜡烛",
        "type": "物资",
        "grid": 1,
        "value": 300,
        "rarity": Rarity.UNCOMMON,
        "description": "应急照明用的蜡烛套装"
    },
    "loot_blowtorch": {
        "name": "燃气喷灯",
        "type": "工具",
        "grid": 2,
        "value": 1200,
        "rarity": Rarity.UNCOMMON,
        "description": "工业用高温喷灯"
    },
    "loot_camping_lamp": {
        "name": "军用露营灯",
        "type": "工具",
        "grid": 2,
        "value": 1500,
        "rarity": Rarity.UNCOMMON,
        "description": "耐用型野外照明灯"
    },
    "loot_electronics": {
        "name": "电子元件",
        "type": "物资",
        "grid": 1,
        "value": 500,
        "rarity": Rarity.UNCOMMON,
        "description": "拆解得来的电子零件"
    },
    "loot_9v_battery": {
        "name": "9V电池",
        "type": "物资",
        "grid": 1,
        "value": 350,
        "rarity": Rarity.UNCOMMON,
        "description": "方形9伏电池"
    },

    # ===== 蓝色物品 - 较稀有 =====
    "loot_cpu": {
        "name": "CPU处理器",
        "type": "物资",
        "grid": 1,
        "value": 3500,
        "rarity": Rarity.RARE,
        "description": "高端处理器，有市无价"
    },
    "loot_hdd": {
        "name": "硬盘驱动器",
        "type": "物资",
        "grid": 1,
        "value": 2000,
        "rarity": Rarity.RARE,
        "description": "可能存有有价值数据的硬盘"
    },
    "loot_motor": {
        "name": "电机",
        "type": "物资",
        "grid": 2,
        "value": 1800,
        "rarity": Rarity.RARE,
        "description": "完好的工业电机"
    },
    "loot_fuel_can": {
        "name": "燃料罐",
        "type": "物资",
        "grid": 2,
        "value": 1500,
        "rarity": Rarity.RARE,
        "description": "满载的燃料容器"
    },
    "loot_portable_power": {
        "name": "军用便携电源",
        "type": "物资",
        "grid": 2,
        "value": 2500,
        "rarity": Rarity.RARE,
        "description": "高容量军用级移动电源"
    },
    "loot_bp_monitor": {
        "name": "血压监测器",
        "type": "医疗",
        "grid": 1,
        "value": 2200,
        "rarity": Rarity.RARE,
        "description": "电子血压监测设备"
    },
    "loot_uv_lamp": {
        "name": "紫外线灯",
        "type": "工具",
        "grid": 1,
        "value": 1800,
        "rarity": Rarity.RARE,
        "description": "紫外线消毒灯"
    },
    "loot_coffee_machine": {
        "name": "胶囊咖啡机套组",
        "type": "物资",
        "grid": 2,
        "value": 3000,
        "rarity": Rarity.RARE,
        "description": "便携式胶囊咖啡机套装"
    },
    "loot_coffee_beans": {
        "name": "袋装咖啡豆",
        "type": "物资",
        "grid": 1,
        "value": 800,
        "rarity": Rarity.RARE,
        "description": "高级咖啡豆"
    },
    "loot_laptop": {
        "name": "笔记本电脑",
        "type": "电子产品",
        "grid": 4,
        "value": 15000,
        "rarity": Rarity.RARE,
        "description": "配置不错的笔记本电脑"
    },
    "loot_camera": {
        "name": "摄像机",
        "type": "电子产品",
        "grid": 2,
        "value": 8000,
        "rarity": Rarity.RARE,
        "description": "专业级摄像设备"
    },
    "loot_info_terminal": {
        "name": "军用信息终端",
        "type": "电子产品",
        "grid": 3,
        "value": 12000,
        "rarity": Rarity.RARE,
        "description": "军用加固型便携终端"
    },
    "loot_military_flash": {
        "name": "军用闪存盘",
        "type": "物资",
        "grid": 1,
        "value": 5000,
        "rarity": Rarity.RARE,
        "description": "军用规格的高容量闪存"
    },
    "loot_med_tools": {
        "name": "手术器械",
        "type": "医疗",
        "grid": 2,
        "value": 12000,
        "rarity": Rarity.RARE,
        "description": "成套的专业手术工具"
    },

    # ===== 紫色物品 - 稀有 =====
    "loot_gpu": {
        "name": "显卡GPU",
        "type": "物资",
        "grid": 2,
        "value": 35000,
        "rarity": Rarity.EPIC,
        "description": "稀缺的高端显卡"
    },
    "loot_military_radio": {
        "name": "军用通讯器",
        "type": "物资",
        "grid": 1,
        "value": 8000,
        "rarity": Rarity.EPIC,
        "description": "加密的军用通讯设备"
    },
    "loot_thermal_scope": {
        "name": "热成像瞄准镜",
        "type": "贵重品",
        "grid": 2,
        "value": 45000,
        "rarity": Rarity.EPIC,
        "description": "高端热成像光学设备"
    },
    "loot_nv_goggles": {
        "name": "夜视仪",
        "type": "贵重品",
        "grid": 1,
        "value": 30000,
        "rarity": Rarity.EPIC,
        "description": "军用级夜视装备"
    },
    "loot_document": {
        "name": "机密文件",
        "type": "贵重品",
        "grid": 1,
        "value": 45000,
        "rarity": Rarity.EPIC,
        "description": "含有敏感信息的文件"
    },
    "loot_intel_folder": {
        "name": "情报文件夹",
        "type": "任务物品",
        "grid": 1,
        "value": 25000,
        "rarity": Rarity.EPIC,
        "description": "装满军事情报的文件夹"
    },
    "loot_water_sample": {
        "name": "水样本",
        "type": "任务物品",
        "grid": 1,
        "value": 12000,
        "rarity": Rarity.EPIC,
        "description": "大坝水库中采集的可疑水样"
    },
    "loot_carbon_fiber": {
        "name": "强化碳纤维板",
        "type": "物资",
        "grid": 4,
        "value": 80000,
        "rarity": Rarity.EPIC,
        "description": "高强度碳纤维复合材料"
    },
    "loot_blade_server": {
        "name": "刀片服务器",
        "type": "电子产品",
        "grid": 6,
        "value": 90000,
        "rarity": Rarity.EPIC,
        "description": "企业级刀片服务器单元"
    },
    "loot_flight_recorder": {
        "name": "飞行记录仪",
        "type": "电子产品",
        "grid": 2,
        "value": 60000,
        "rarity": Rarity.EPIC,
        "description": "飞机黑匣子，数据珍贵"
    },
    "loot_cloud_storage": {
        "name": "云存储阵列",
        "type": "电子产品",
        "grid": 6,
        "value": 100000,
        "rarity": Rarity.EPIC,
        "description": "企业级存储阵列"
    },
    "loot_disk_array": {
        "name": "高速磁盘阵列",
        "type": "电子产品",
        "grid": 6,
        "value": 95000,
        "rarity": Rarity.EPIC,
        "description": "高速数据存储系统"
    },
    "loot_rolex": {
        "name": "劳力士手表",
        "type": "贵重品",
        "grid": 1,
        "value": 60000,
        "rarity": Rarity.EPIC,
        "description": "高档奢侈手表"
    },
    "loot_satellite_phone": {
        "name": "卫星电话",
        "type": "电子产品",
        "grid": 2,
        "value": 150000,
        "rarity": Rarity.EPIC,
        "description": "铱星卫星通讯电话"
    },
    "loot_defibrillator": {
        "name": "自体除颤器",
        "type": "医疗",
        "grid": 3,
        "value": 120000,
        "rarity": Rarity.EPIC,
        "description": "便携式心脏除颤设备"
    },

    # ===== 金色物品 - 极稀有 =====
    "loot_usb_secret": {
        "name": "加密U盘",
        "type": "贵重品",
        "grid": 1,
        "value": 100000,
        "rarity": Rarity.LEGENDARY,
        "description": "包含机密数据的加密U盘"
    },
    "loot_bitcoin": {
        "name": "比特币矿机",
        "type": "物资",
        "grid": 4,
        "value": 65000,
        "rarity": Rarity.LEGENDARY,
        "description": "可运行的比特币矿机"
    },
    "loot_bust": {
        "name": "半身像",
        "type": "贵重品",
        "grid": 4,
        "value": 150000,
        "rarity": Rarity.LEGENDARY,
        "description": "古董大理石半身雕像"
    },
    "loot_golden_gazelle": {
        "name": "黄金瞪羚",
        "type": "贵重品",
        "grid": 3,
        "value": 180000,
        "rarity": Rarity.LEGENDARY,
        "description": "镀金瞪羚雕塑，精美绝伦"
    },
    "loot_crown": {
        "name": "珠宝头冠",
        "type": "贵重品",
        "grid": 3,
        "value": 250000,
        "rarity": Rarity.LEGENDARY,
        "description": "镶嵌宝石的贵族头冠"
    },
    "loot_vacuum": {
        "name": "强力吸尘器",
        "type": "物资",
        "grid": 6,
        "value": 200000,
        "rarity": Rarity.LEGENDARY,
        "description": "工业级大功率吸尘设备"
    },
    "loot_mandel_unit": {
        "name": "曼德尔超算单元",
        "type": "电子产品",
        "grid": 6,
        "value": 280000,
        "rarity": Rarity.LEGENDARY,
        "description": "超级计算机核心单元"
    },
    "loot_portable_radar": {
        "name": "便携军用雷达",
        "type": "电子产品",
        "grid": 6,
        "value": 350000,
        "rarity": Rarity.LEGENDARY,
        "description": "小型战术雷达系统"
    },
    "loot_secret_server": {
        "name": "绝密服务器",
        "type": "电子产品",
        "grid": 6,
        "value": 400000,
        "rarity": Rarity.LEGENDARY,
        "description": "军用级加密服务器"
    },
    "loot_ecmo": {
        "name": "ECMO",
        "type": "医疗",
        "grid": 9,
        "value": 500000,
        "rarity": Rarity.LEGENDARY,
        "description": "体外膜肺氧合设备"
    },
    "loot_respirator": {
        "name": "复苏呼吸机",
        "type": "医疗",
        "grid": 9,
        "value": 550000,
        "rarity": Rarity.LEGENDARY,
        "description": "高级生命支持呼吸机"
    },

    # ===== 红色物品 - 传说级 =====
    "loot_goldbar": {
        "name": "金条",
        "type": "贵重品",
        "grid": 1,
        "value": 150000,
        "rarity": Rarity.LEGENDARY,
        "description": "纯金条，硬通货"
    },
    "loot_diamond": {
        "name": "未切割钻石",
        "type": "贵重品",
        "grid": 1,
        "value": 200000,
        "rarity": Rarity.LEGENDARY,
        "description": "非洲之心级别的原钻"
    },
    "loot_lion_statue": {
        "name": "黄金雄狮像",
        "type": "贵重品",
        "grid": 4,
        "value": 250000,
        "rarity": Rarity.LEGENDARY,
        "description": "纯金打造的雄狮雕像"
    },
    "loot_tank_model": {
        "name": "坦克模型",
        "type": "贵重品",
        "grid": 4,
        "value": 300000,
        "rarity": Rarity.LEGENDARY,
        "description": "精密制作的限量版坦克模型"
    },
    "loot_ifv_model": {
        "name": "步战车模型",
        "type": "贵重品",
        "grid": 4,
        "value": 220000,
        "rarity": Rarity.LEGENDARY,
        "description": "步兵战车精密模型"
    },
    "loot_artillery_shell": {
        "name": "军用炮弹",
        "type": "物资",
        "grid": 6,
        "value": 280000,
        "rarity": Rarity.LEGENDARY,
        "description": "未引爆的军用炮弹，极其危险"
    },
    "loot_robot_vacuum": {
        "name": "扫拖机器",
        "type": "物资",
        "grid": 9,
        "value": 400000,
        "rarity": Rarity.LEGENDARY,
        "description": "智能扫拖一体机器人"
    },
    "loot_reactor": {
        "name": "微型反应炉",
        "type": "物资",
        "grid": 9,
        "value": 450000,
        "rarity": Rarity.LEGENDARY,
        "description": "微型核反应堆原型"
    },
    "loot_zongheng": {
        "name": "纵横",
        "type": "贵重品",
        "grid": 9,
        "value": 500000,
        "rarity": Rarity.LEGENDARY,
        "description": "古代名剑复制品，工艺精湛"
    },
    "loot_tears_crown": {
        "name": "万金泪冠",
        "type": "贵重品",
        "grid": 9,
        "value": 480000,
        "rarity": Rarity.LEGENDARY,
        "description": "镶嵌泪滴状宝石的皇冠"
    },
    "loot_armor_battery": {
        "name": "装甲车电池",
        "type": "物资",
        "grid": 6,
        "value": 350000,
        "rarity": Rarity.LEGENDARY,
        "description": "军用装甲车辆动力电池"
    },
    "loot_african_heart": {
        "name": "非洲之心",
        "type": "贵重品",
        "grid": 1,
        "value": 800000,
        "rarity": Rarity.LEGENDARY,
        "description": "世界最大的切割钻石"
    },
    "loot_ocean_tear": {
        "name": "海洋之泪",
        "type": "贵重品",
        "grid": 1,
        "value": 1200000,
        "rarity": Rarity.LEGENDARY,
        "description": "稀世蓝钻，传说来自深海"
    },

    # ===== 钥匙和任务物品 =====
    "key_lab_keycard": {
        "name": "实验室钥匙卡",
        "type": "钥匙",
        "grid": 0,
        "value": 20000,
        "rarity": Rarity.EPIC,
        "description": "可打开研究实验室的磁卡"
    },
    "key_armory": {
        "name": "军火库钥匙",
        "type": "钥匙",
        "grid": 0,
        "value": 25000,
        "rarity": Rarity.EPIC,
        "description": "通往军火库的钥匙"
    },
    "key_server": {
        "name": "服务器机房钥匙卡",
        "type": "钥匙",
        "grid": 0,
        "value": 30000,
        "rarity": Rarity.LEGENDARY,
        "description": "数据服务器机房的高级权限卡"
    },
    "key_safe": {
        "name": "保险柜密码条",
        "type": "钥匙",
        "grid": 0,
        "value": 15000,
        "rarity": Rarity.RARE,
        "description": "某个保险柜的密码"
    },
    "key_substation": {
        "name": "变电站钥匙",
        "type": "钥匙",
        "grid": 0,
        "value": 18000,
        "rarity": Rarity.RARE,
        "description": "主变电站的通行钥匙"
    },
    "key_control_room": {
        "name": "控制室门禁卡",
        "type": "钥匙",
        "grid": 0,
        "value": 25000,
        "rarity": Rarity.EPIC,
        "description": "大坝控制室的高级门禁卡"
    },
    "key_radar_station": {
        "name": "雷达站钥匙卡",
        "type": "钥匙",
        "grid": 0,
        "value": 35000,
        "rarity": Rarity.LEGENDARY,
        "description": "哈夫克雷达站通行证"
    },
    "key_director_office": {
        "name": "总裁室钥匙卡",
        "type": "钥匙",
        "grid": 0,
        "value": 40000,
        "rarity": Rarity.LEGENDARY,
        "description": "航天基地总裁办公室权限卡"
    },
    "key_launch_area": {
        "name": "发射区通行证",
        "type": "钥匙",
        "grid": 0,
        "value": 30000,
        "rarity": Rarity.EPIC,
        "description": "航天发射区通行证件"
    },
    "key_babel": {
        "name": "巴别塔钥匙",
        "type": "钥匙",
        "grid": 0,
        "value": 50000,
        "rarity": Rarity.LEGENDARY,
        "description": "通往巴别塔顶层的古铜钥匙"
    },

    # ===== 可破译的高价值物资 =====
    "decode_encrypted_drive": {
        "name": "加密硬盘",
        "type": "可破译",
        "grid": 2,
        "value": 0,
        "decode_time": 3,
        "decode_reward": {
            "money": [50000, 100000, 200000],
            "items": ["loot_gpu", "loot_document", "loot_bitcoin"]
        },
        "rarity": Rarity.EPIC,
        "description": "加密的军用硬盘，需要3回合破译才能获取其中的价值"
    },
    "decode_secret_cache": {
        "name": "秘密缓存盒",
        "type": "可破译",
        "grid": 3,
        "value": 0,
        "decode_time": 4,
        "decode_reward": {
            "money": [30000, 80000, 150000],
            "items": ["loot_usb_secret", "loot_military_radio"]
        },
        "rarity": Rarity.EPIC,
        "description": "军用级加密存储盒，需要专业工具破译"
    },
    "decode_gold_safe": {
        "name": "黄金保险箱",
        "type": "可破译",
        "grid": 4,
        "value": 0,
        "decode_time": 5,
        "decode_reward": {
            "money": [100000, 200000, 500000],
            "items": ["loot_goldbar", "loot_diamond", "loot_rolex"]
        },
        "rarity": Rarity.LEGENDARY,
        "description": "高价值保险箱，需要长时间破译"
    },
    "decode_lab_sample": {
        "name": "实验室样本箱",
        "type": "可破译",
        "grid": 2,
        "value": 0,
        "decode_time": 2,
        "decode_reward": {
            "money": [20000, 50000, 100000],
            "items": ["loot_water_sample", "med_surgery", "stim_propital"]
        },
        "rarity": Rarity.RARE,
        "description": "生化实验室样本，需要快速处理"
    }
}

# 破译系统配置
DECODE_CONFIG = {
    "base_decode_time_multiplier": 1.0,
    "engineer_bonus": 0.5,  # 工程师破译时间减半
    "recon_bonus": 0.25,    # 侦查员减少25%时间
    "decode_interrupt_penalty": 0.5,  # 被打断时损失50%进度
    "max_concurrent_decodes": 2  # 最多同时破译2个物品
}

# ============== 地图数据 ==============
# 地图坐标系统 - 用于计算距离和可视化
_MAP_INDUSTRIAL_REMOVED = True  # 已迁移到三角洲行动地图

# ============== 零号大坝地图 ==============
MAP_DAM = {
    "name": "零号大坝",
    "description": "一座巨型水电站大坝，曾是重要的能源枢纽，现已沦为各方势力争夺的战场...",
    "width": 22,
    "height": 16,
    "zones": {
        # ============ 出生点 ============
        "dam_spawn_east": {
            "name": "东侧公路",
            "description": "通往大坝的主公路，路面龟裂。",
            "x": 20, "y": 8,
            "danger_level": 1, "loot_tier": 1,
            "connections": ["dam_admin_district", "dam_barracks"],
            "is_spawn": True, "is_extract": False
        },
        "dam_spawn_south": {
            "name": "南侧河滩",
            "description": "大坝下游的河滩地带，水流湍急。",
            "x": 10, "y": 1,
            "danger_level": 1, "loot_tier": 1,
            "connections": ["dam_hydroplant", "dam_visitor_center"],
            "is_spawn": True, "is_extract": False
        },
        "dam_spawn_northwest": {
            "name": "西北山路",
            "description": "崎岖的山间小路，可以俯瞰大坝全貌。",
            "x": 2, "y": 14,
            "danger_level": 1, "loot_tier": 1,
            "connections": ["dam_backup_station", "dam_construction"],
            "is_spawn": True, "is_extract": False
        },
        # ============ 外围区域 ============
        "dam_visitor_center": {
            "name": "游客中心",
            "description": "大坝旅游景区的游客服务中心，内有展览厅和纪念品商店。",
            "x": 8, "y": 3,
            "danger_level": 2, "loot_tier": 2,
            "connections": ["dam_spawn_south", "dam_cement_factory", "dam_small_substation"],
            "is_spawn": False, "is_extract": False
        },
        "dam_construction": {
            "name": "建筑工地",
            "description": "未完工的扩建工程，脚手架林立，可作绝佳掩体。",
            "x": 4, "y": 12,
            "danger_level": 2, "loot_tier": 2,
            "connections": ["dam_spawn_northwest", "dam_backup_station", "dam_staff_dorm"],
            "is_spawn": False, "is_extract": False
        },
        "dam_staff_dorm": {
            "name": "员工宿舍",
            "description": "大坝工作人员的生活区，废弃已久，个人物品散落一地。",
            "x": 7, "y": 10,
            "danger_level": 2, "loot_tier": 2,
            "connections": ["dam_construction", "dam_cement_factory", "dam_admin_west"],
            "is_spawn": False, "is_extract": False
        },
        "dam_cement_factory": {
            "name": "水泥厂",
            "description": "为大坝供应建材的水泥生产厂，粉尘弥漫。",
            "x": 10, "y": 6,
            "danger_level": 3, "loot_tier": 3,
            "connections": ["dam_visitor_center", "dam_staff_dorm", "dam_admin_west", "dam_small_substation"],
            "is_spawn": False, "is_extract": False
        },
        "dam_small_substation": {
            "name": "小变电站",
            "description": "负责园区日常供电的小型变电设施。",
            "x": 6, "y": 5,
            "danger_level": 2, "loot_tier": 2,
            "connections": ["dam_visitor_center", "dam_cement_factory", "dam_backup_station"],
            "is_spawn": False, "is_extract": False
        },
        "dam_backup_station": {
            "name": "备用电站",
            "description": "大坝应急备用发电设施，关键时刻可恢复供电。",
            "x": 4, "y": 8,
            "danger_level": 3, "loot_tier": 3,
            "connections": ["dam_spawn_northwest", "dam_construction", "dam_small_substation", "dam_extract_pipe"],
            "is_spawn": False, "is_extract": False
        },
        # ============ 核心区域 ============
        "dam_admin_west": {
            "name": "行政西楼",
            "description": "行政区西侧楼栋，财务和后勤部门驻扎于此。",
            "x": 12, "y": 9,
            "danger_level": 3, "loot_tier": 3,
            "connections": ["dam_staff_dorm", "dam_cement_factory", "dam_admin_district", "dam_barracks"],
            "is_spawn": False, "is_extract": False
        },
        "dam_admin_east": {
            "name": "行政东楼",
            "description": "行政区东侧楼栋，指挥和情报部门的据点。",
            "x": 16, "y": 9,
            "danger_level": 4, "loot_tier": 4,
            "connections": ["dam_admin_district", "dam_barracks", "dam_main_substation"],
            "is_spawn": False, "is_extract": False
        },
        "dam_admin_district": {
            "name": "行政辖区",
            "description": "大坝管理核心区域，各类行政设施密集分布。",
            "x": 14, "y": 7,
            "danger_level": 4, "loot_tier": 4,
            "connections": ["dam_spawn_east", "dam_admin_west", "dam_admin_east", "dam_control_room"],
            "is_spawn": False, "is_extract": False
        },
        "dam_barracks": {
            "name": "军营",
            "description": "驻守大坝的武装力量营地，武器储备充足。",
            "x": 18, "y": 11,
            "danger_level": 3, "loot_tier": 3,
            "connections": ["dam_spawn_east", "dam_admin_west", "dam_admin_east", "dam_extract_village"],
            "is_spawn": False, "is_extract": False
        },
        "dam_hydroplant": {
            "name": "水电站厂房",
            "description": "巨大的水力发电涡轮机组，轰鸣声震耳欲聋。",
            "x": 11, "y": 3,
            "danger_level": 4, "loot_tier": 4,
            "connections": ["dam_spawn_south", "dam_control_room", "dam_extract_river"],
            "is_spawn": False, "is_extract": False
        },
        # ============ 高价值区域 ============
        "dam_main_substation": {
            "name": "主变电站",
            "description": "控制整座大坝电力分配的核心变电设施，戒备森严。",
            "x": 18, "y": 7,
            "danger_level": 4, "loot_tier": 4,
            "connections": ["dam_admin_east", "dam_control_room"],
            "is_spawn": False, "is_extract": False,
            "requires_key": "substation_key"
        },
        "dam_control_room": {
            "name": "大坝控制室",
            "description": "掌控整座大坝运作的神经中枢，布满监控屏幕与精密仪器。",
            "x": 14, "y": 4,
            "danger_level": 5, "loot_tier": 5,
            "connections": ["dam_admin_district", "dam_hydroplant", "dam_main_substation", "dam_extract_elevator"],
            "is_spawn": False, "is_extract": False,
            "requires_key": "control_keycard"
        },
        # ============ 撤离点 ============
        "dam_extract_elevator": {
            "name": "工业电梯撤离",
            "description": "大坝内部的工业货运电梯，需要支付通行费。",
            "x": 16, "y": 3,
            "danger_level": 1, "loot_tier": 0,
            "connections": ["dam_control_room"],
            "is_spawn": False, "is_extract": True,
            "extract_condition": {"type": "paid", "cost": 8000}
        },
        "dam_extract_river": {
            "name": "河滩限时撤离",
            "description": "通过河滩快速撤离，需要等待接应船只。",
            "x": 13, "y": 1,
            "danger_level": 1, "loot_tier": 0,
            "connections": ["dam_hydroplant"],
            "is_spawn": False, "is_extract": True,
            "extract_condition": {"type": "wait", "wait_time": 30}
        },
        "dam_extract_pipe": {
            "name": "维修管道撤离",
            "description": "狭窄的维修管道出口，背包无法通过。",
            "x": 2, "y": 9,
            "danger_level": 1, "loot_tier": 0,
            "connections": ["dam_backup_station"],
            "is_spawn": False, "is_extract": True,
            "extract_condition": {"type": "drop_backpack", "drop_backpack": True}
        },
        "dam_extract_village": {
            "name": "村庄撤离",
            "description": "军营附近的废弃村庄，开放的撤离通道。",
            "x": 20, "y": 13,
            "danger_level": 1, "loot_tier": 0,
            "connections": ["dam_barracks"],
            "is_spawn": False, "is_extract": True,
            "extract_condition": {"type": "open", "open_time": 0}
        }
    }
}

# ============== 长弓溪谷地图 ==============
MAP_VALLEY = {
    "name": "长弓溪谷",
    "description": "一条被河流贯穿的深谷，上下两个半区地形高低错落，资源丰富但危机四伏...",
    "width": 24,
    "height": 18,
    "zones": {
        # ============ 出生点 ============
        "valley_spawn_west": {
            "name": "西侧山道",
            "description": "蜿蜒的山间小道，通往溪谷西部。",
            "x": 1, "y": 9,
            "danger_level": 1, "loot_tier": 1,
            "connections": ["valley_manor", "valley_pasture"],
            "is_spawn": True, "is_extract": False
        },
        "valley_spawn_southeast": {
            "name": "东南海岸",
            "description": "溪谷东南方向的海岸线，渔船残骸随处可见。",
            "x": 20, "y": 2,
            "danger_level": 1, "loot_tier": 1,
            "connections": ["valley_blue_harbor", "valley_small_station"],
            "is_spawn": True, "is_extract": False
        },
        "valley_spawn_north": {
            "name": "北部公路",
            "description": "贯穿溪谷北部的主干公路，路面宽阔。",
            "x": 12, "y": 16,
            "danger_level": 1, "loot_tier": 1,
            "connections": ["valley_checkpoint", "valley_storage"],
            "is_spawn": True, "is_extract": False
        },
        # ============ 左侧区域 ============
        "valley_manor": {
            "name": "小型庄园",
            "description": "依山而建的古老庄园，主楼与附属建筑保存尚好。",
            "x": 3, "y": 12,
            "danger_level": 2, "loot_tier": 2,
            "connections": ["valley_spawn_west", "valley_garbi", "valley_pasture"],
            "is_spawn": False, "is_extract": False
        },
        "valley_garbi": {
            "name": "加尔比旧址",
            "description": "曾经的村落遗址，战火已将其夷为平地，瓦砾中仍藏有物资。",
            "x": 3, "y": 15,
            "danger_level": 3, "loot_tier": 3,
            "connections": ["valley_manor", "valley_extract_tunnel"],
            "is_spawn": False, "is_extract": False
        },
        "valley_pasture": {
            "name": "沙径牧场",
            "description": "沿溪谷延伸的牧场，围栏和牲口棚提供天然掩体。",
            "x": 6, "y": 11,
            "danger_level": 2, "loot_tier": 2,
            "connections": ["valley_spawn_west", "valley_manor", "valley_crash_site", "valley_fishing_port"],
            "is_spawn": False, "is_extract": False
        },
        "valley_crash_site": {
            "name": "坠机之地",
            "description": "一架军用直升机的坠毁现场，残骸中可能有珍贵军用物资。",
            "x": 6, "y": 8,
            "danger_level": 3, "loot_tier": 3,
            "connections": ["valley_pasture", "valley_fishing_port", "valley_substation"],
            "is_spawn": False, "is_extract": False
        },
        "valley_fishing_port": {
            "name": "渔港",
            "description": "小型渔业码头，船坞和仓库内物资丰富。",
            "x": 4, "y": 5,
            "danger_level": 2, "loot_tier": 2,
            "connections": ["valley_pasture", "valley_crash_site", "valley_substation"],
            "is_spawn": False, "is_extract": False
        },
        # ============ 中央区域 ============
        "valley_radar": {
            "name": "哈夫克雷达站",
            "description": "溪谷制高点上的军用雷达设施，信号覆盖整个区域，内藏高价值情报设备。",
            "x": 11, "y": 13,
            "danger_level": 5, "loot_tier": 5,
            "connections": ["valley_substation", "valley_storage", "valley_extract_helipad"],
            "is_spawn": False, "is_extract": False,
            "requires_key": "radar_keycard"
        },
        "valley_substation": {
            "name": "变电站",
            "description": "为溪谷各设施供电的主变电站，电气设备密集。",
            "x": 8, "y": 10,
            "danger_level": 3, "loot_tier": 3,
            "connections": ["valley_crash_site", "valley_fishing_port", "valley_radar", "valley_superstar"],
            "is_spawn": False, "is_extract": False
        },
        "valley_storage": {
            "name": "储藏站",
            "description": "物资中转储藏设施，各类补给在此集散。",
            "x": 13, "y": 14,
            "danger_level": 3, "loot_tier": 3,
            "connections": ["valley_spawn_north", "valley_radar", "valley_checkpoint", "valley_hotel"],
            "is_spawn": False, "is_extract": False
        },
        "valley_superstar": {
            "name": "超星车站",
            "description": "废弃的公共交通换乘站，站台和候车室内掩体充足。",
            "x": 10, "y": 7,
            "danger_level": 2, "loot_tier": 2,
            "connections": ["valley_substation", "valley_hotel", "valley_checkpoint"],
            "is_spawn": False, "is_extract": False
        },
        "valley_hotel": {
            "name": "钻石皇后酒店",
            "description": "溪谷中最豪华的酒店建筑，曾是富商聚集之所，内有保险柜和贵重物品。",
            "x": 14, "y": 10,
            "danger_level": 4, "loot_tier": 4,
            "connections": ["valley_storage", "valley_superstar", "valley_checkpoint", "valley_amiya"],
            "is_spawn": False, "is_extract": False
        },
        "valley_checkpoint": {
            "name": "检查站",
            "description": "控制溪谷南北交通的重要关卡，武装人员巡逻频繁。",
            "x": 15, "y": 12,
            "danger_level": 3, "loot_tier": 2,
            "connections": ["valley_spawn_north", "valley_storage", "valley_superstar", "valley_hotel"],
            "is_spawn": False, "is_extract": False
        },
        # ============ 右侧区域 ============
        "valley_amiya": {
            "name": "阿米娅小镇",
            "description": "溪谷东部的小型聚居点，民居与商铺交错分布。",
            "x": 17, "y": 11,
            "danger_level": 3, "loot_tier": 3,
            "connections": ["valley_hotel", "valley_small_station", "valley_abandoned_village"],
            "is_spawn": False, "is_extract": False
        },
        "valley_small_station": {
            "name": "小火车站",
            "description": "已停运的小型铁路车站，铁轨锈蚀，月台尚完整。",
            "x": 19, "y": 8,
            "danger_level": 2, "loot_tier": 2,
            "connections": ["valley_spawn_southeast", "valley_amiya", "valley_blue_harbor"],
            "is_spawn": False, "is_extract": False
        },
        "valley_abandoned_village": {
            "name": "荒废村庄",
            "description": "被战乱清空的村庄，房屋虽破败但仍有生活物资遗留。",
            "x": 17, "y": 14,
            "danger_level": 2, "loot_tier": 2,
            "connections": ["valley_amiya", "valley_extract_road"],
            "is_spawn": False, "is_extract": False
        },
        "valley_blue_harbor": {
            "name": "蓝港码头",
            "description": "曾经繁忙的货运码头，停靠着数艘废弃船只，仓库内物资可观。",
            "x": 21, "y": 5,
            "danger_level": 3, "loot_tier": 3,
            "connections": ["valley_spawn_southeast", "valley_small_station", "valley_extract_speedboat"],
            "is_spawn": False, "is_extract": False
        },
        # ============ 撤离点 ============
        "valley_extract_helipad": {
            "name": "雷达站直升机坪",
            "description": "雷达站顶部的军用直升机停机坪，需支付高额撤离费。",
            "x": 9, "y": 15,
            "danger_level": 1, "loot_tier": 0,
            "connections": ["valley_radar"],
            "is_spawn": False, "is_extract": True,
            "extract_condition": {"type": "paid", "cost": 10000}
        },
        "valley_extract_speedboat": {
            "name": "码头快艇撤离",
            "description": "蓝港码头停靠的快艇，需等待燃料补充后方可启动。",
            "x": 22, "y": 3,
            "danger_level": 1, "loot_tier": 0,
            "connections": ["valley_blue_harbor"],
            "is_spawn": False, "is_extract": True,
            "extract_condition": {"type": "wait", "wait_time": 25}
        },
        "valley_extract_tunnel": {
            "name": "溪谷隧道",
            "description": "穿山而过的逃生隧道，背包过宽无法通行。",
            "x": 1, "y": 16,
            "danger_level": 1, "loot_tier": 0,
            "connections": ["valley_garbi"],
            "is_spawn": False, "is_extract": True,
            "extract_condition": {"type": "drop_backpack", "drop_backpack": True}
        },
        "valley_extract_road": {
            "name": "公路撤离点",
            "description": "荒废村庄外的公路撤离区，全程开放。",
            "x": 19, "y": 16,
            "danger_level": 1, "loot_tier": 0,
            "connections": ["valley_abandoned_village"],
            "is_spawn": False, "is_extract": True,
            "extract_condition": {"type": "open", "open_time": 0}
        }
    }
}

# ============== 航天基地地图 ==============
MAP_SPACE = {
    "name": "航天基地",
    "description": "一座废弃的航天发射基地，巨大的火箭发射架耸立在荒漠之中，内部研究设施仍藏有大量机密...",
    "width": 22,
    "height": 16,
    "zones": {
        # ============ 出生点 ============
        "space_spawn_south": {
            "name": "南侧荒漠",
            "description": "基地南方的无垠荒漠，沙尘暴频繁。",
            "x": 10, "y": 1,
            "danger_level": 1, "loot_tier": 1,
            "connections": ["space_industrial", "space_assembly"],
            "is_spawn": True, "is_extract": False
        },
        "space_spawn_east": {
            "name": "东侧公路",
            "description": "连接基地与外界的主干公路，路面留有车辙痕迹。",
            "x": 20, "y": 8,
            "danger_level": 1, "loot_tier": 1,
            "connections": ["space_launch_zone", "space_hoist"],
            "is_spawn": True, "is_extract": False
        },
        "space_spawn_northwest": {
            "name": "西北隐蔽点",
            "description": "基地西北角的岩石掩体群，适合隐蔽渗透。",
            "x": 2, "y": 13,
            "danger_level": 1, "loot_tier": 1,
            "connections": ["space_dorm", "space_control_building"],
            "is_spawn": True, "is_extract": False
        },
        # ============ 外围区域 ============
        "space_industrial": {
            "name": "工业区",
            "description": "基地外围的工业生产区，存放大量工程材料与设备。",
            "x": 7, "y": 3,
            "danger_level": 2, "loot_tier": 2,
            "connections": ["space_spawn_south", "space_assembly", "space_dorm", "space_extract_desert"],
            "is_spawn": False, "is_extract": False
        },
        "space_dorm": {
            "name": "宿舍区",
            "description": "科研人员与技术工人的生活区，个人物品和生活用品仍有留存。",
            "x": 4, "y": 10,
            "danger_level": 2, "loot_tier": 2,
            "connections": ["space_spawn_northwest", "space_industrial", "space_control_building", "space_extract_pipe"],
            "is_spawn": False, "is_extract": False
        },
        "space_control_building": {
            "name": "中控楼",
            "description": "基地综合指挥大楼，通信与监控设备集中于此。",
            "x": 6, "y": 13,
            "danger_level": 3, "loot_tier": 3,
            "connections": ["space_spawn_northwest", "space_dorm", "space_h2", "space_print_room"],
            "is_spawn": False, "is_extract": False
        },
        "space_launch_zone": {
            "name": "发射区",
            "description": "巨型火箭发射架耸立的核心区域，辐射警告标志遍布四周。",
            "x": 18, "y": 5,
            "danger_level": 4, "loot_tier": 4,
            "connections": ["space_spawn_east", "space_test_bay", "space_hoist"],
            "is_spawn": False, "is_extract": False
        },
        "space_test_bay": {
            "name": "水平试车间",
            "description": "火箭发动机水平测试厂房，高温痕迹遍布墙壁。",
            "x": 16, "y": 3,
            "danger_level": 3, "loot_tier": 3,
            "connections": ["space_launch_zone", "space_assembly", "space_extract_sidedoor"],
            "is_spawn": False, "is_extract": False
        },
        "space_assembly": {
            "name": "组装室",
            "description": "火箭部件组装车间，大型机械臂悬挂于顶部。",
            "x": 12, "y": 4,
            "danger_level": 3, "loot_tier": 3,
            "connections": ["space_spawn_south", "space_industrial", "space_test_bay", "space_h1"],
            "is_spawn": False, "is_extract": False
        },
        "space_hoist": {
            "name": "吊装室",
            "description": "用于吊装大型设备的高大厂房，顶部天车轨道错综复杂。",
            "x": 18, "y": 10,
            "danger_level": 3, "loot_tier": 3,
            "connections": ["space_spawn_east", "space_launch_zone", "space_h4"],
            "is_spawn": False, "is_extract": False
        },
        "space_print_room": {
            "name": "打印室",
            "description": "精密零件3D打印车间，设备先进，存有珍贵的技术图纸。",
            "x": 8, "y": 11,
            "danger_level": 2, "loot_tier": 2,
            "connections": ["space_control_building", "space_h2", "space_h3"],
            "is_spawn": False, "is_extract": False
        },
        # ============ 核心研究设施 ============
        "space_h4": {
            "name": "黑室H4",
            "description": "绝密研究区域H4，黑色涂装的墙壁令人不安，内藏高价值研究成果。",
            "x": 16, "y": 11,
            "danger_level": 4, "loot_tier": 4,
            "connections": ["space_hoist", "space_h3", "space_director"],
            "is_spawn": False, "is_extract": False
        },
        "space_h3": {
            "name": "蓝室H3",
            "description": "蓝色警示灯常亮的研究区域H3，存放着重要的实验数据。",
            "x": 13, "y": 11,
            "danger_level": 4, "loot_tier": 4,
            "connections": ["space_h4", "space_print_room", "space_h2"],
            "is_spawn": False, "is_extract": False
        },
        "space_h2": {
            "name": "浮力室H2",
            "description": "模拟失重环境的特殊研究舱室，内有大型悬浮装置。",
            "x": 10, "y": 13,
            "danger_level": 4, "loot_tier": 3,
            "connections": ["space_control_building", "space_print_room", "space_h3", "space_h1"],
            "is_spawn": False, "is_extract": False
        },
        "space_h1": {
            "name": "离心机室H1",
            "description": "装备超大型离心机的测试室，模拟宇航员承受的过载环境。",
            "x": 13, "y": 7,
            "danger_level": 4, "loot_tier": 3,
            "connections": ["space_assembly", "space_h2", "space_director"],
            "is_spawn": False, "is_extract": False
        },
        "space_director": {
            "name": "总裁室",
            "description": "基地最高指挥官的私人办公室，深藏基地最核心的机密文件与贵重物品。",
            "x": 15, "y": 8,
            "danger_level": 5, "loot_tier": 5,
            "connections": ["space_h4", "space_h1", "space_extract_helipad"],
            "is_spawn": False, "is_extract": False,
            "requires_key": "director_keycard"
        },
        # ============ 撤离点 ============
        "space_extract_helipad": {
            "name": "发射台直升机",
            "description": "发射台顶部的紧急直升机平台，撤离费用高昂。",
            "x": 17, "y": 7,
            "danger_level": 1, "loot_tier": 0,
            "connections": ["space_director"],
            "is_spawn": False, "is_extract": True,
            "extract_condition": {"type": "paid", "cost": 12000}
        },
        "space_extract_desert": {
            "name": "荒漠撤离点",
            "description": "南侧荒漠中预设的开放撤离区域。",
            "x": 8, "y": 1,
            "danger_level": 1, "loot_tier": 0,
            "connections": ["space_industrial"],
            "is_spawn": False, "is_extract": True,
            "extract_condition": {"type": "open", "open_time": 0}
        },
        "space_extract_pipe": {
            "name": "地下管道",
            "description": "基地地下排水管道出口，背包过大无法通行。",
            "x": 3, "y": 15,
            "danger_level": 1, "loot_tier": 0,
            "connections": ["space_dorm"],
            "is_spawn": False, "is_extract": True,
            "extract_condition": {"type": "drop_backpack", "drop_backpack": True}
        },
        "space_extract_sidedoor": {
            "name": "试车间侧门",
            "description": "水平试车间的紧急侧门，需等待安保巡逻间隙。",
            "x": 19, "y": 2,
            "danger_level": 1, "loot_tier": 0,
            "connections": ["space_test_bay"],
            "is_spawn": False, "is_extract": True,
            "extract_condition": {"type": "wait", "wait_time": 20}
        }
    }
}

# ============== 巴克什地图 ==============
MAP_BAKSH = {
    "name": "巴克什",
    "description": "一座古老的中东城镇，巴别塔高耸于城市中心，各方势力为争夺塔内宝藏而激战不休...",
    "width": 20,
    "height": 16,
    "zones": {
        # ============ 出生点 ============
        "baksh_spawn_south": {
            "name": "城南入口",
            "description": "巴克什城镇南侧的主要入口，残破的城门依然矗立。",
            "x": 10, "y": 1,
            "danger_level": 1, "loot_tier": 1,
            "connections": ["baksh_bazaar", "baksh_cherry_town"],
            "is_spawn": True, "is_extract": False
        },
        "baksh_spawn_east": {
            "name": "东部废墟",
            "description": "城镇东侧的战争废墟区，断壁残垣提供大量掩体。",
            "x": 18, "y": 7,
            "danger_level": 1, "loot_tier": 1,
            "connections": ["baksh_rooftop", "baksh_bell_tower"],
            "is_spawn": True, "is_extract": False
        },
        "baksh_spawn_west": {
            "name": "西侧小巷",
            "description": "城镇西侧蜿蜒的小巷网络，熟悉地形者可快速穿行。",
            "x": 2, "y": 9,
            "danger_level": 1, "loot_tier": 1,
            "connections": ["baksh_bathhouse", "baksh_mosque"],
            "is_spawn": True, "is_extract": False
        },
        # ============ 外围区域 ============
        "baksh_cherry_town": {
            "name": "樱桃小镇",
            "description": "城南的居民区，彩色涂装的建筑与茂盛的樱桃树形成鲜明对比。",
            "x": 7, "y": 3,
            "danger_level": 2, "loot_tier": 2,
            "connections": ["baksh_spawn_south", "baksh_bazaar", "baksh_inn"],
            "is_spawn": False, "is_extract": False
        },
        "baksh_bazaar": {
            "name": "集市广场",
            "description": "城镇中心的传统集市，摊位林立，曾是商贸往来的热闹场所。",
            "x": 10, "y": 4,
            "danger_level": 2, "loot_tier": 2,
            "connections": ["baksh_spawn_south", "baksh_cherry_town", "baksh_inn", "baksh_museum", "baksh_babel_base", "baksh_extract_south_gate"],
            "is_spawn": False, "is_extract": False
        },
        "baksh_inn": {
            "name": "蓝汀旅馆",
            "description": "城中历史最悠久的旅馆，蓝色外墙已斑驳，客房内遗留大量旅客物品。",
            "x": 7, "y": 6,
            "danger_level": 3, "loot_tier": 3,
            "connections": ["baksh_cherry_town", "baksh_bazaar", "baksh_bathhouse", "baksh_mosque"],
            "is_spawn": False, "is_extract": False
        },
        "baksh_bathhouse": {
            "name": "大浴场",
            "description": "传统式公共浴室建筑，穹顶结构独特，地下有古老的供水管道。",
            "x": 4, "y": 7,
            "danger_level": 3, "loot_tier": 3,
            "connections": ["baksh_spawn_west", "baksh_inn", "baksh_sewer", "baksh_extract_bathhouse"],
            "is_spawn": False, "is_extract": False
        },
        "baksh_mosque": {
            "name": "清真寺",
            "description": "城镇的宗教中心，宣礼塔居高临下，内部装饰精美，藏有珍贵文物。",
            "x": 3, "y": 12,
            "danger_level": 3, "loot_tier": 3,
            "connections": ["baksh_spawn_west", "baksh_inn", "baksh_sewer"],
            "is_spawn": False, "is_extract": False
        },
        # ============ 核心区域 ============
        "baksh_museum": {
            "name": "皇家博物馆",
            "description": "收藏着大量珍贵文物和历史典藏的博物馆，保险库深处据说存有无价之宝。",
            "x": 13, "y": 5,
            "danger_level": 4, "loot_tier": 4,
            "connections": ["baksh_bazaar", "baksh_babel_base", "baksh_bell_tower"],
            "is_spawn": False, "is_extract": False
        },
        "baksh_bell_tower": {
            "name": "钟楼",
            "description": "城镇东侧的古老钟楼，登顶可俯瞰全城，是狙击手的理想阵地。",
            "x": 16, "y": 6,
            "danger_level": 3, "loot_tier": 3,
            "connections": ["baksh_spawn_east", "baksh_museum", "baksh_rooftop"],
            "is_spawn": False, "is_extract": False
        },
        "baksh_rooftop": {
            "name": "屋顶通道",
            "description": "连接城镇各楼宇的屋顶跑道，视野开阔但暴露风险极高。",
            "x": 16, "y": 10,
            "danger_level": 3, "loot_tier": 2,
            "connections": ["baksh_spawn_east", "baksh_bell_tower", "baksh_babel_top", "baksh_extract_harbor"],
            "is_spawn": False, "is_extract": False
        },
        "baksh_sewer": {
            "name": "地下水道",
            "description": "延伸至城镇各处的古老地下水道系统，黑暗潮湿，危险重重。",
            "x": 6, "y": 11,
            "danger_level": 4, "loot_tier": 3,
            "connections": ["baksh_bathhouse", "baksh_mosque", "baksh_babel_base"],
            "is_spawn": False, "is_extract": False
        },
        "baksh_babel_base": {
            "name": "巴别塔底层",
            "description": "巴别塔的地面入口层，厚重的铁门和武装警卫阻挡着闯入者。",
            "x": 11, "y": 9,
            "danger_level": 4, "loot_tier": 4,
            "connections": ["baksh_bazaar", "baksh_museum", "baksh_sewer", "baksh_babel_top"],
            "is_spawn": False, "is_extract": False
        },
        # ============ 高价值区域 ============
        "baksh_babel_top": {
            "name": "巴别塔",
            "description": "城镇中央的巨型古塔，层层设防，塔顶据说藏有传说中的无尽财富，是整座城市的战略核心。",
            "x": 11, "y": 12,
            "danger_level": 5, "loot_tier": 5,
            "connections": ["baksh_babel_base", "baksh_rooftop", "baksh_extract_babel"],
            "is_spawn": False, "is_extract": False,
            "requires_key": "babel_key"
        },
        # ============ 撤离点 ============
        "baksh_extract_babel": {
            "name": "巴别塔顶撤离",
            "description": "巴别塔顶部的撤离平台，俯瞰全城，需支付高额撤离费。",
            "x": 13, "y": 14,
            "danger_level": 1, "loot_tier": 0,
            "connections": ["baksh_babel_top"],
            "is_spawn": False, "is_extract": True,
            "extract_condition": {"type": "paid", "cost": 15000}
        },
        "baksh_extract_bathhouse": {
            "name": "浴场地道",
            "description": "大浴场地下的古老逃生地道，空间狭窄无法携带背包。",
            "x": 2, "y": 6,
            "danger_level": 1, "loot_tier": 0,
            "connections": ["baksh_bathhouse"],
            "is_spawn": False, "is_extract": True,
            "extract_condition": {"type": "drop_backpack", "drop_backpack": True}
        },
        "baksh_extract_south_gate": {
            "name": "城南大门",
            "description": "城镇南侧的主城门，需等待守卫换岗间隙方可通过。",
            "x": 10, "y": 14,
            "danger_level": 1, "loot_tier": 0,
            "connections": ["baksh_bazaar"],
            "is_spawn": False, "is_extract": True,
            "extract_condition": {"type": "wait", "wait_time": 30}
        },
        "baksh_extract_harbor": {
            "name": "码头撤离",
            "description": "城镇东侧的小型码头，全时段开放的撤离通道。",
            "x": 18, "y": 12,
            "danger_level": 1, "loot_tier": 0,
            "connections": ["baksh_rooftop"],
            "is_spawn": False, "is_extract": True,
            "extract_condition": {"type": "open", "open_time": 0}
        }
    }
}

# 所有地图列表
ALL_MAPS = {
    "dam": MAP_DAM,
    "valley": MAP_VALLEY,
    "space": MAP_SPACE,
    "baksh": MAP_BAKSH
}

# 根据地图获取撤离点
def get_extraction_points(map_data: dict) -> list:
    return [zid for zid, z in map_data["zones"].items() if z.get("is_extract")]

EXTRACTION_POINTS = get_extraction_points(MAP_DAM)

# ============== 武器配件系统 ==============
ATTACHMENTS = {
    # 瞄准镜
    "sight_red_dot": {
        "name": "红点瞄准镜",
        "slot": "sight",
        "effects": {"accuracy": 0.05},
        "value": 500,
        "rarity": Rarity.COMMON,
        "description": "基础红点瞄具，提升命中率"
    },
    "sight_holographic": {
        "name": "全息瞄准镜",
        "slot": "sight",
        "effects": {"accuracy": 0.08},
        "value": 1200,
        "rarity": Rarity.UNCOMMON,
        "description": "全息瞄具，明显提升命中率"
    },
    "sight_acog": {
        "name": "ACOG 4倍镜",
        "slot": "sight",
        "effects": {"accuracy": 0.12, "fire_rate": -1},
        "value": 3000,
        "rarity": Rarity.RARE,
        "description": "4倍放大瞄准镜，大幅提升精度但降低射速"
    },
    "sight_thermal": {
        "name": "热成像瞄准镜",
        "slot": "sight",
        "effects": {"accuracy": 0.15},
        "value": 15000,
        "rarity": Rarity.LEGENDARY,
        "description": "热成像技术，极大提升命中率"
    },
    # 枪口
    "muzzle_suppressor": {
        "name": "消音器",
        "slot": "muzzle",
        "effects": {"accuracy": 0.03, "aggro_reduce": True},
        "value": 2000,
        "rarity": Rarity.UNCOMMON,
        "description": "降低开火噪音，略微提升精度"
    },
    "muzzle_compensator": {
        "name": "补偿器",
        "slot": "muzzle",
        "effects": {"accuracy": 0.05},
        "value": 1500,
        "rarity": Rarity.UNCOMMON,
        "description": "减少后坐力，提升精度"
    },
    "muzzle_flash_hider": {
        "name": "消焰器",
        "slot": "muzzle",
        "effects": {"accuracy": 0.02},
        "value": 800,
        "rarity": Rarity.COMMON,
        "description": "隐藏枪口火焰"
    },
    # 握把
    "grip_vertical": {
        "name": "垂直握把",
        "slot": "grip",
        "effects": {"accuracy": 0.04},
        "value": 600,
        "rarity": Rarity.COMMON,
        "description": "改善射击稳定性"
    },
    "grip_angled": {
        "name": "角度握把",
        "slot": "grip",
        "effects": {"accuracy": 0.03, "fire_rate": 1},
        "value": 900,
        "rarity": Rarity.UNCOMMON,
        "description": "更快切枪速度，略提精度和射速"
    },
    # 弹匣
    "mag_extended": {
        "name": "扩容弹匣",
        "slot": "magazine",
        "effects": {"mag_size": 10},
        "value": 800,
        "rarity": Rarity.UNCOMMON,
        "description": "增加弹匣容量10发"
    },
    "mag_drum": {
        "name": "弹鼓",
        "slot": "magazine",
        "effects": {"mag_size": 30, "accuracy": -0.03},
        "value": 2500,
        "rarity": Rarity.RARE,
        "description": "大幅增加弹匣容量，略降精度"
    },
    # 枪托
    "stock_tactical": {
        "name": "战术枪托",
        "slot": "stock",
        "effects": {"accuracy": 0.04},
        "value": 1000,
        "rarity": Rarity.UNCOMMON,
        "description": "可调节的战术枪托，提升精度"
    },
    "stock_skeleton": {
        "name": "骨架枪托",
        "slot": "stock",
        "effects": {"accuracy": 0.02, "fire_rate": 1},
        "value": 700,
        "rarity": Rarity.COMMON,
        "description": "轻量化枪托，提升机动性"
    }
}

import math

def get_zone_distance(zones: dict, zone1_id: str, zone2_id: str) -> float:
    """计算两个区域之间的距离"""
    z1 = zones.get(zone1_id, {})
    z2 = zones.get(zone2_id, {})
    x1, y1 = z1.get("x", 0), z1.get("y", 0)
    x2, y2 = z2.get("x", 0), z2.get("y", 0)
    return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)

def select_distant_extraction(zones: dict, spawn_zone: str) -> str:
    """选择一个距离玩家出生点较远的撤离点"""
    extraction_points = [zid for zid, z in zones.items() if z.get("is_extract")]
    distances = []
    for ep in extraction_points:
        if ep in zones:
            dist = get_zone_distance(zones, spawn_zone, ep)
            distances.append((ep, dist))

    # 按距离排序，选择最远的
    distances.sort(key=lambda x: x[1], reverse=True)

    # 从最远的两个中随机选择一个，增加变化性
    if len(distances) >= 2:
        candidates = distances[:2]
        return random.choice(candidates)[0]
    elif distances:
        return distances[0][0]
    return EXTRACTION_POINTS[0]

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
    # ===== 新增敌人 =====
    "scav_sniper": {
        "name": "游荡者狙击手",
        "hp": 120,
        "armor_class": 2,
        "accuracy": 0.80,
        "weapon": "sniper_mosin",
        "aggro_range": 6,
        "loot_table": "scav_veteran",
        "xp": 250
    },
    "scav_shotgunner": {
        "name": "游荡者散弹手",
        "hp": 180,
        "armor_class": 2,
        "accuracy": 0.55,
        "weapon": "shotgun_m870",
        "aggro_range": 2,
        "loot_table": "scav_normal",
        "xp": 150
    },
    "raider_assault": {
        "name": "突袭者突击兵",
        "hp": 250,
        "armor_class": 4,
        "accuracy": 0.70,
        "weapon": "ar_hk416",
        "aggro_range": 5,
        "loot_table": "pmc_normal",
        "xp": 400
    },
    "raider_lmg": {
        "name": "突袭者机枪手",
        "hp": 350,
        "armor_class": 4,
        "accuracy": 0.50,
        "weapon": "lmg_pkm",
        "aggro_range": 5,
        "loot_table": "pmc_elite",
        "xp": 450
    },
    "raider_sniper": {
        "name": "突袭者狙击手",
        "hp": 200,
        "armor_class": 3,
        "accuracy": 0.90,
        "weapon": "sniper_awm",
        "aggro_range": 7,
        "loot_table": "pmc_elite",
        "xp": 500
    },
    "pmc_medic": {
        "name": "佣兵医疗兵",
        "hp": 180,
        "armor_class": 3,
        "accuracy": 0.55,
        "weapon": "smg_vector",
        "aggro_range": 3,
        "loot_table": "pmc_normal",
        "xp": 250
    },
    "pmc_heavy": {
        "name": "佣兵重装兵",
        "hp": 400,
        "armor_class": 5,
        "accuracy": 0.60,
        "weapon": "lmg_m249",
        "aggro_range": 4,
        "loot_table": "pmc_elite",
        "xp": 600
    },
    "boss_guardian": {
        "name": "守卫者",
        "hp": 600,
        "armor_class": 5,
        "accuracy": 0.80,
        "weapon": "ar_scarh",
        "aggro_range": 6,
        "loot_table": "boss_killa",
        "xp": 1500,
        "is_boss": True
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
        ("loot_wire", 0.3),
        ("med_bandage", 0.2),
        ("drink_water", 0.15)
    ],
    "scav_normal": [
        ("loot_electronics", 0.3),
        ("loot_circuit_board", 0.2),
        ("med_ai2", 0.2),
        ("loot_tape", 0.3),
        ("food_mre", 0.15),
        ("grenade_flash", 0.05)
    ],
    "scav_veteran": [
        ("loot_cpu", 0.2),
        ("med_ifak", 0.2),
        ("loot_electronics", 0.3),
        ("loot_military_flash", 0.15),
        ("armor_2_police", 0.1),
        ("grenade_frag", 0.08),
        ("key_safe", 0.03)
    ],
    "pmc_normal": [
        ("loot_cpu", 0.3),
        ("loot_document", 0.1),
        ("loot_hdd", 0.2),
        ("med_ifak", 0.2),
        ("loot_military_radio", 0.1),
        ("armor_3_umka", 0.1),
        ("stim_adrenaline", 0.05),
        ("key_lab_keycard", 0.03)
    ],
    "pmc_elite": [
        ("loot_gpu", 0.15),
        ("loot_document", 0.2),
        ("loot_intel_folder", 0.1),
        ("med_surgery", 0.1),
        ("armor_4_korund", 0.15),
        ("loot_rolex", 0.05),
        ("loot_nv_goggles", 0.08),
        ("stim_propital", 0.08),
        ("key_armory", 0.03),
        ("key_server", 0.02)
    ],
    "boss_killa": [
        ("loot_gpu", 0.3),
        ("loot_rolex", 0.3),
        ("loot_bitcoin", 0.1),
        ("loot_usb_secret", 0.1),
        ("armor_5_killa", 0.4),
        ("loot_goldbar", 0.05),
        ("loot_thermal_scope", 0.15),
        ("loot_diamond", 0.08),
        ("loot_lion_statue", 0.05),
        ("loot_tank_model", 0.03)
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
    grid: int = 1  # 占用格子数
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
    attachments: Dict = field(default_factory=dict)  # slot -> attachment_id

    def get_item_type(self):
        return "weapon"

    def get_effective_accuracy(self) -> float:
        """计算包含配件加成的实际精度"""
        acc = self.accuracy
        for slot, att_id in self.attachments.items():
            att = ATTACHMENTS.get(att_id)
            if att:
                acc += att["effects"].get("accuracy", 0)
        return min(0.99, max(0.1, acc))

    def get_effective_fire_rate(self) -> int:
        """计算包含配件加成的实际射速"""
        fr = self.fire_rate
        for slot, att_id in self.attachments.items():
            att = ATTACHMENTS.get(att_id)
            if att:
                fr += att["effects"].get("fire_rate", 0)
        return max(1, fr)

    def get_effective_mag_size(self) -> int:
        """计算包含配件加成的实际弹匣"""
        ms = self.mag_size
        for slot, att_id in self.attachments.items():
            att = ATTACHMENTS.get(att_id)
            if att:
                ms += att["effects"].get("mag_size", 0)
        return max(1, ms)

    def install_attachment(self, att_id: str) -> Tuple[bool, str]:
        """安装配件"""
        att = ATTACHMENTS.get(att_id)
        if not att:
            return False, "配件不存在"
        slot = att["slot"]
        old = self.attachments.get(slot)
        self.attachments[slot] = att_id
        msg = f"已安装{att['name']}到{self.name}"
        if old:
            msg += f"（替换了{ATTACHMENTS[old]['name']}）"
        return True, msg

    def remove_attachment(self, slot: str) -> Tuple[bool, str]:
        """拆卸配件"""
        if slot not in self.attachments:
            return False, "该槽位没有配件"
        att_id = self.attachments.pop(slot)
        att = ATTACHMENTS.get(att_id, {})
        return True, f"已拆卸{att.get('name', att_id)}"

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
class Debuff:
    """状态异常"""
    name: str           # 内部名称: bleeding, stunned, slowed
    cn_name: str        # 中文名
    remaining: int      # 剩余回合数
    damage: int = 0     # 每回合伤害（流血用）

@dataclass
class OperatorSkill:
    """干员技能"""
    skill_id: str
    name: str
    description: str
    cooldown: int
    current_cooldown: int = 0
    uses: int = 0
    max_uses: int = 3   # 每局可使用次数

    def can_use(self) -> bool:
        return self.current_cooldown == 0 and self.uses < self.max_uses

    def use(self):
        if self.can_use():
            self.uses += 1
            self.current_cooldown = self.cooldown
            return True
        return False

    def tick(self):
        if self.current_cooldown > 0:
            self.current_cooldown -= 1

@dataclass
class Operator:
    """干员实例"""
    operator_id: str
    name: str
    operator_class: OperatorClass
    description: str
    primary_skill: OperatorSkill
    secondary_skill: OperatorSkill
    bonus: Dict = field(default_factory=dict)
    is_player: bool = False
    is_ai: bool = False

    @classmethod
    def create(cls, operator_id: str, is_player: bool = False, is_ai: bool = False) -> 'Operator':
        """从模板创建干员"""
        data = OPERATORS.get(operator_id)
        if not data:
            raise ValueError(f"Unknown operator: {operator_id}")

        # 创建技能实例
        class_code = data["class"].code
        primary_data = OPERATOR_SKILLS[class_code][data["primary_skill"]]
        secondary_data = OPERATOR_SKILLS[class_code][data["secondary_skill"]]

        primary_skill = OperatorSkill(
            skill_id=data["primary_skill"],
            name=primary_data["name"],
            description=primary_data["description"],
            cooldown=primary_data["cooldown"]
        )
        secondary_skill = OperatorSkill(
            skill_id=data["secondary_skill"],
            name=secondary_data["name"],
            description=secondary_data["description"],
            cooldown=secondary_data["cooldown"]
        )

        return cls(
            operator_id=operator_id,
            name=data["name"],
            operator_class=data["class"],
            description=data["description"],
            primary_skill=primary_skill,
            secondary_skill=secondary_skill,
            bonus=data.get("bonus", {}),
            is_player=is_player,
            is_ai=is_ai
        )

@dataclass
class VehicleWeapon:
    """载具武器状态"""
    weapon_id: str
    name: str
    damage: int
    fire_rate: int
    accuracy: float
    range: int
    current_ammo: int
    max_ammo: int
    reload_time: int
    reload_remaining: int = 0

    @classmethod
    def create(cls, weapon_id: str) -> 'VehicleWeapon':
        data = VEHICLE_WEAPONS.get(weapon_id)
        if not data:
            raise ValueError(f"Unknown weapon: {weapon_id}")
        return cls(
            weapon_id=weapon_id,
            name=data["name"],
            damage=data["damage"],
            fire_rate=data["fire_rate"],
            accuracy=data["accuracy"],
            range=data["range"],
            current_ammo=data["ammo"],
            max_ammo=data["ammo"],
            reload_time=data.get("reload_time", 5)
        )

    def can_fire(self) -> bool:
        return self.current_ammo > 0 and self.reload_remaining == 0

    def fire(self) -> int:
        """开火，返回发射的弹药数"""
        if not self.can_fire():
            return 0
        shots = min(self.fire_rate, self.current_ammo)
        self.current_ammo -= shots
        return shots

    def reload(self):
        if self.current_ammo < self.max_ammo and self.reload_remaining == 0:
            self.reload_remaining = self.reload_time

    def tick(self):
        if self.reload_remaining > 0:
            self.reload_remaining -= 1
            if self.reload_remaining == 0:
                self.current_ammo = self.max_ammo

@dataclass
class Vehicle:
    """载具实例"""
    vehicle_id: str
    name: str
    vehicle_type: VehicleType
    hp: int
    max_hp: int
    armor: int
    seats: int
    speed: int
    weapons: List[VehicleWeapon]
    description: str
    value: int
    occupants: List[str] = field(default_factory=list)  # 占用者ID列表
    driver: Optional[str] = None
    current_zone: str = ""
    destroyed: bool = False

    @classmethod
    def create(cls, vehicle_id: str) -> 'Vehicle':
        data = VEHICLES.get(vehicle_id)
        if not data:
            raise ValueError(f"Unknown vehicle: {vehicle_id}")

        weapons = [VehicleWeapon.create(w) for w in data["weapons"]]

        return cls(
            vehicle_id=vehicle_id,
            name=data["name"],
            vehicle_type=data["type"],
            hp=data["hp"],
            max_hp=data["max_hp"],
            armor=data["armor"],
            seats=data["seats"],
            speed=data["speed"],
            weapons=weapons,
            description=data["description"],
            value=data["value"]
        )

    def can_board(self) -> bool:
        return len(self.occupants) < self.seats and not self.destroyed

    def board(self, player_id: str, as_driver: bool = False) -> bool:
        if not self.can_board():
            return False
        if player_id not in self.occupants:
            self.occupants.append(player_id)
        if as_driver and self.driver is None:
            self.driver = player_id
        return True

    def exit_vehicle(self, player_id: str) -> bool:
        if player_id in self.occupants:
            self.occupants.remove(player_id)
            if self.driver == player_id:
                self.driver = self.occupants[0] if self.occupants else None
            return True
        return False

    def take_damage(self, damage: int, penetration: int) -> int:
        """载具受伤，返回实际伤害"""
        if self.destroyed:
            return 0

        # 护甲减伤
        if self.armor > 0:
            armor_reduction = max(0, (self.armor - penetration) * 0.15)
            actual_damage = int(damage * (1 - armor_reduction))
        else:
            actual_damage = damage

        self.hp -= actual_damage
        if self.hp <= 0:
            self.hp = 0
            self.destroyed = True

        return actual_damage

    def repair(self, amount: int) -> int:
        """修复载具"""
        if self.destroyed:
            return 0
        repaired = min(amount, self.max_hp - self.hp)
        self.hp += repaired
        return repaired

    def get_weapon(self, weapon_id: str = None) -> Optional[VehicleWeapon]:
        """获取武器"""
        if weapon_id:
            for w in self.weapons:
                if w.weapon_id == weapon_id:
                    return w
            return None
        return self.weapons[0] if self.weapons else None

    def tick(self):
        """每回合更新"""
        for weapon in self.weapons:
            weapon.tick()

@dataclass
class SquadMember:
    """小队成员"""
    member_id: str
    name: str
    operator: Operator
    stats: 'PlayerStats'
    equipment: 'EquipmentSlots'
    is_downed: bool = False
    is_dead: bool = False
    vehicle_id: Optional[str] = None  # 当前所在的载具

    @property
    def hp(self):
        return self.operator.stats.hp if hasattr(self.operator, 'stats') else 100

    @property
    def is_ai(self):
        """便捷访问 operator.is_ai"""
        return self.operator.is_ai if hasattr(self.operator, 'is_ai') else False

    def is_alive(self) -> bool:
        return not self.is_dead and self.stats.is_alive()

    def revive(self, heal_amount: int = 30):
        """复活倒地队友"""
        if self.is_downed and not self.is_dead:
            self.is_downed = False
            self.stats.heal(heal_amount)

@dataclass
class Squad:
    """3人小队 - 三角洲行动核心机制"""
    squad_id: str
    name: str
    members: List[SquadMember] = field(default_factory=list)
    vehicles: List[Vehicle] = field(default_factory=list)
    leader_id: str = ""

    def add_member(self, member: SquadMember):
        if len(self.members) < 3:  # 三角洲行动：3人小队
            self.members.append(member)
            if not self.leader_id:
                self.leader_id = member.member_id

    def get_alive_members(self) -> List[SquadMember]:
        return [m for m in self.members if m.is_alive()]

    def get_downed_members(self) -> List[SquadMember]:
        return [m for m in self.members if m.is_downed and not m.is_dead]

    def all_downed(self) -> bool:
        return all(m.is_downed or m.is_dead for m in self.members)

    def all_dead(self) -> bool:
        return all(m.is_dead for m in self.members)

    def get_member(self, member_id: str) -> Optional[SquadMember]:
        for m in self.members:
            if m.member_id == member_id:
                return m
        return None

    def get_leader(self) -> Optional[SquadMember]:
        return self.get_member(self.leader_id)

    def add_vehicle(self, vehicle: Vehicle):
        self.vehicles.append(vehicle)

    def get_vehicle(self, vehicle_id: str) -> Optional[Vehicle]:
        for v in self.vehicles:
            if v.vehicle_id == vehicle_id:
                return v
        return None

    def tick(self):
        """每回合更新所有成员和载具状态"""
        for member in self.members:
            if member.is_alive() and not member.is_downed:
                member.stats.tick()
                member.operator.primary_skill.tick()
                member.operator.secondary_skill.tick()
        for vehicle in self.vehicles:
            vehicle.tick()

@dataclass
class DecodeProgress:
    """破译进度"""
    item_id: str
    item_name: str
    total_time: int       # 总破译时间（回合）
    current_progress: int = 0  # 当前进度
    decoder_id: str = ""  # 正在破译的成员ID
    interrupted: bool = False

    def advance(self, bonus: float = 0.0) -> Tuple[bool, str]:
        """推进破译进度，返回(是否完成, 消息)"""
        if self.interrupted:
            return False, "破译已被打断"

        progress = 1 + int(bonus)
        self.current_progress += progress

        if self.current_progress >= self.total_time:
            return True, f"破译完成！{self.item_name}已解锁"
        return False, f"破译进度: {self.current_progress}/{self.total_time}"

    def interrupt(self) -> int:
        """打断破译，返回损失的进度"""
        lost = int(self.current_progress * DECODE_CONFIG["decode_interrupt_penalty"])
        self.current_progress = 0
        self.interrupted = True
        return lost

@dataclass
class DecodeManager:
    """破译管理器"""
    active_decodes: List[DecodeProgress] = field(default_factory=list)
    completed_rewards: List[Dict] = field(default_factory=list)

    def start_decode(self, item_id: str, item_name: str, decode_time: int, decoder_id: str, class_bonus: float = 0.0) -> bool:
        """开始破译"""
        if len(self.active_decodes) >= DECODE_CONFIG["max_concurrent_decodes"]:
            return False

        # 应用职业加成
        actual_time = max(1, int(decode_time * (1 - class_bonus)))

        progress = DecodeProgress(
            item_id=item_id,
            item_name=item_name,
            total_time=actual_time,
            decoder_id=decoder_id
        )
        self.active_decodes.append(progress)
        return True

    def tick(self, member_bonuses: Dict[str, float] = None) -> List[Tuple[str, str, Dict]]:
        """每回合更新破译进度，返回完成的破译列表[(item_id, msg, rewards)]"""
        completed = []
        member_bonuses = member_bonuses or {}

        for decode in self.active_decodes[:]:
            bonus = member_bonuses.get(decode.decoder_id, 0)
            done, msg = decode.advance(bonus)

            if done:
                # 从LOOT_ITEMS获取奖励
                item_data = LOOT_ITEMS.get(decode.item_id, {})
                reward_config = item_data.get("decode_reward", {})
                rewards = self._generate_rewards(reward_config)
                completed.append((decode.item_id, msg, rewards))
                self.active_decodes.remove(decode)

        return completed

    def interrupt_all(self):
        """打断所有破译"""
        for decode in self.active_decodes:
            decode.interrupt()

    def _generate_rewards(self, reward_config: Dict) -> Dict:
        """生成破译奖励"""
        rewards = {"money": 0, "items": []}

        if "money" in reward_config:
            money_options = reward_config["money"]
            rewards["money"] = random.choice(money_options)

        if "items" in reward_config:
            item_ids = reward_config["items"]
            # 随机选择1-2个物品
            num_items = random.randint(1, min(2, len(item_ids)))
            chosen = random.sample(item_ids, num_items)
            rewards["items"] = chosen

        return rewards

@dataclass
class ArmorStatus:
    """护甲状态"""
    armor_value: int = 0       # 护甲值
    max_armor: int = 0         # 最大护甲值
    durability: int = 0        # 耐久度
    max_durability: int = 0    # 最大耐久度

    def absorb_damage(self, damage: int) -> tuple:
        """吸收伤害，返回(实际伤害, 护甲消耗)"""
        if self.armor_value <= 0 or self.durability <= 0:
            return damage, 0

        # 护甲吸收比例（基于耐久度）
        absorb_ratio = min(0.7, self.durability / self.max_durability * 0.7)
        absorbed = int(damage * absorb_ratio)
        actual_damage = damage - absorbed

        # 护甲耐久消耗
        durability_loss = int(absorbed * 0.5)
        self.durability = max(0, self.durability - durability_loss)

        # 耐久度降低后护甲值也降低
        if self.durability < 30:
            self.armor_value = int(self.max_armor * self.durability / self.max_durability)

        return actual_damage, durability_loss

    def repair(self, amount: int) -> int:
        """修理护甲"""
        repaired = min(amount, self.max_durability - self.durability)
        self.durability += repaired
        # 修理后恢复护甲值
        self.armor_value = int(self.max_armor * self.durability / self.max_durability)
        return repaired

@dataclass
class PlayerStats:
    """玩家状态 - 统一HP + 分部位护甲 + debuff"""
    # 统一生命值
    hp: int = 100
    max_hp: int = 100

    # 护甲 (头部和胸部有护甲，腿部无护甲)
    head_armor: ArmorStatus = field(default_factory=ArmorStatus)
    chest_armor: ArmorStatus = field(default_factory=ArmorStatus)

    # debuff列表
    debuffs: List = field(default_factory=list)

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
        """HP大于0即存活"""
        return self.hp > 0

    def get_total_hp(self) -> int:
        """总HP"""
        return self.hp

    def get_max_hp(self) -> int:
        """最大总HP"""
        return self.max_hp

    def get_armor(self, zone: DamageZone) -> ArmorStatus:
        """获取对应部位的护甲"""
        if zone == DamageZone.HEAD:
            return self.head_armor
        elif zone == DamageZone.CHEST:
            return self.chest_armor
        return ArmorStatus()  # 腿部无护甲

    def has_debuff(self, name: str) -> bool:
        return any(d.name == name for d in self.debuffs)

    def get_debuff(self, name: str) -> Optional[Debuff]:
        return next((d for d in self.debuffs if d.name == name), None)

    def add_debuff(self, name: str, cn_name: str, duration: int, damage: int = 0):
        """添加或刷新debuff"""
        existing = self.get_debuff(name)
        if existing:
            existing.remaining = max(existing.remaining, duration)
            if damage > 0:
                existing.damage = damage
        else:
            self.debuffs.append(Debuff(name=name, cn_name=cn_name, remaining=duration, damage=damage))

    def remove_debuff(self, name: str):
        self.debuffs = [d for d in self.debuffs if d.name != name]

    def clear_debuffs(self):
        self.debuffs.clear()

    def apply_pain_relief(self, duration: int):
        self.pain_relief_timer = duration

    def heal(self, amount: int) -> int:
        """治疗"""
        need = self.max_hp - self.hp
        healed = min(amount, need)
        self.hp += healed
        return healed

    def take_damage(self, damage: int) -> int:
        """扣除HP"""
        actual = min(damage, self.hp)
        self.hp -= actual
        return actual

    def reset_for_base(self):
        """重置状态回基地"""
        self.hp = self.max_hp
        self.debuffs = []
        # 重置护甲
        if self.head_armor.max_durability > 0:
            self.head_armor.durability = self.head_armor.max_durability
        if self.chest_armor.max_durability > 0:
            self.chest_armor.durability = self.chest_armor.max_durability

    def tick(self):
        """每回合更新状态"""
        if self.pain_relief_timer > 0:
            self.pain_relief_timer -= 1
        # 饥渴消耗
        self.energy = max(0, self.energy - 1)
        self.hydration = max(0, self.hydration - 1)
        # 处理debuff
        bleed_damage = 0
        expired = []
        for debuff in self.debuffs:
            if debuff.name == 'bleeding' and debuff.damage > 0:
                bleed_damage += debuff.damage
            debuff.remaining -= 1
            if debuff.remaining <= 0:
                expired.append(debuff.name)
        # 流血扣HP（不致死，最低1）
        if bleed_damage > 0:
            self.hp = max(1, self.hp - bleed_damage)
        # 再生恢复HP
        regen = self.get_debuff('regen')
        if regen and regen.damage < 0:
            heal_amount = abs(regen.damage)
            self.heal(heal_amount)
        # 移除过期debuff
        self.debuffs = [d for d in self.debuffs if d.remaining > 0]
        return bleed_damage

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
    backpack: Optional['Backpack'] = None  # 敌人背包，可被搜索

    def __post_init__(self):
        """初始化敌人背包，随机放入一些物品"""
        if self.backpack is None:
            self.backpack = Backpack(rows=3, cols=3)  # 敌人背包较小
            # 随机放入一些物品
            if random.random() < 0.5:  # 50%概率有物品
                possible_items = [
                    ("bandage", "绷带", 0.3),
                    ("medkit", "急救包", 0.15),
                    ("ammo_9mm", "9mm弹药", 0.4),
                    ("repair_kit", "修理工具", 0.1)
                ]
                for item_id, item_name, chance in possible_items:
                    if random.random() < chance:
                        item = Consumable(
                            id=f"enemy_{item_id}_{random.randint(100,999)}",
                            name=item_name,
                            weight=0.1,
                            value=random.randint(50, 200),
                            rarity=Rarity.COMMON,
                            effect={"heal": 30} if "med" in item_id or "bandage" in item_id else {}
                        )
                        self.backpack.add_item(item)

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

    def get_total_capacity(self) -> int:
        """获取背包总容量"""
        return self.rows * self.cols

    def get_used_slots(self) -> int:
        """获取已使用的格子数"""
        used = 0
        for item in self.items.values():
            used += getattr(item, 'grid', 1)
        return used

    def get_free_slots(self) -> int:
        """获取剩余空闲格子数"""
        return self.get_total_capacity() - self.get_used_slots()

    def can_fit(self, item: Item) -> bool:
        """检查是否能放入物品（考虑物品占用的格子数）"""
        grid_size = getattr(item, 'grid', 1) if item else 1
        return self.get_free_slots() >= grid_size

    def add_item(self, item: Item) -> bool:
        """添加物品到背包（占用grid指定的格子数）"""
        grid_size = getattr(item, 'grid', 1)
        if self.get_free_slots() < grid_size:
            return False

        # 找到足够的空格子并标记
        slots_needed = grid_size
        for row in range(self.rows):
            for col in range(self.cols):
                if self.grid[row][col] is None:
                    self.grid[row][col] = item.id
                    slots_needed -= 1
                    if slots_needed == 0:
                        break
            if slots_needed == 0:
                break

        self.items[item.id] = item
        return True

    def remove_item(self, item_id: str) -> Optional[Item]:
        """从背包移除物品（释放所有占用的格子）"""
        if item_id in self.items:
            item = self.items.pop(item_id)
            # 释放所有该物品占用的格子
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

    def equip_armor(self, armor: Armor, player_stats: 'PlayerStats' = None):
        self.armor = armor
        if player_stats and armor:
            player_stats.chest_armor = ArmorStatus(
                armor_value=armor.armor_class,
                max_armor=armor.armor_class,
                durability=armor.durability,
                max_durability=armor.max_durability
            )

    def equip_helmet(self, helmet: Armor, player_stats: 'PlayerStats' = None):
        self.helmet = helmet
        if player_stats and helmet:
            player_stats.head_armor = ArmorStatus(
                armor_value=helmet.armor_class,
                max_armor=helmet.armor_class,
                durability=helmet.durability,
                max_durability=helmet.max_durability
            )

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
    """玩家类 - 支持干员系统和3人小队"""
    def __init__(self, name: str = "玩家", operator_id: str = "operator_wyatt"):
        self.name = name
        # 干员系统
        self.operator = Operator.create(operator_id, is_player=True)
        self.stats = PlayerStats()
        self.equipment = EquipmentSlots()
        self.stash_weapons: List[Weapon] = []  # 武器仓库
        self.stash_armors: List[Armor] = []    # 护甲仓库
        self.stash_helmets: List[Armor] = []   # 头盔仓库
        self.stash_items: List[Item] = []      # 物品仓库
        self.current_zone: str = ""
        self.action_points: int = 100
        self.max_action_points: int = 100
        self.kills: int = 0
        self.total_loot_value: int = 0

        # 载具相关
        self.current_vehicle: Optional[Vehicle] = None
        self.is_driver: bool = False

    def set_operator(self, operator_id: str):
        """切换干员"""
        if operator_id in OPERATORS:
            self.operator = Operator.create(operator_id, is_player=True)

    def use_skill(self, skill_type: str = "primary") -> Tuple[bool, str]:
        """使用干员技能"""
        skill = self.operator.primary_skill if skill_type == "primary" else self.operator.secondary_skill
        if not skill.can_use():
            return False, f"技能冷却中或使用次数已用完"

        skill.use()
        return True, f"使用技能: {skill.name}"

    def board_vehicle(self, vehicle: Vehicle, as_driver: bool = False) -> Tuple[bool, str]:
        """登上载具"""
        if not vehicle.can_board():
            return False, "载具已满或已损坏"

        if vehicle.board(self.name, as_driver):
            self.current_vehicle = vehicle
            self.is_driver = as_driver
            return True, f"登上了 {vehicle.name}"
        return False, "无法登上载具"

    def exit_vehicle(self) -> Tuple[bool, str]:
        """离开载具"""
        if not self.current_vehicle:
            return False, "你不在载具中"

        vehicle = self.current_vehicle
        if vehicle.exit_vehicle(self.name):
            self.current_vehicle = None
            self.is_driver = False
            return True, f"离开了 {vehicle.name}"
        return False, "无法离开载具"

    def vehicle_attack(self, target, weapon_id: str = None) -> Tuple[int, str]:
        """使用载具武器攻击"""
        if not self.current_vehicle or not self.is_driver:
            return 0, "你需要驾驶载具才能使用武器"

        weapon = self.current_vehicle.get_weapon(weapon_id)
        if not weapon:
            return 0, "找不到该武器"

        if not weapon.can_fire():
            return 0, "武器需要装填或正在冷却"

        # 计算伤害
        shots = weapon.fire()
        total_damage = 0

        if isinstance(target, Enemy):
            for _ in range(shots):
                if random.random() < weapon.accuracy:
                    damage = target.take_damage(weapon.damage, getattr(weapon, 'penetration', 1))
                    total_damage += damage

            msg = f"{self.current_vehicle.name}的{weapon.name}命中！造成{total_damage}伤害"

            if not target.is_alive():
                self.add_xp(target.xp)
                self.kills += 1
                msg += f"\n{target.name}被击毁！获得{target.xp}经验！"
        elif isinstance(target, Vehicle):
            for _ in range(shots):
                if random.random() < weapon.accuracy:
                    pen = getattr(weapon, 'penetration', 1)
                    damage = target.take_damage(weapon.damage, pen)
                    total_damage += damage

            msg = f"{self.current_vehicle.name}的{weapon.name}命中{target.name}！造成{total_damage}伤害"

            if target.destroyed:
                msg += f"\n{target.name}被击毁！"

        return total_damage, msg

    def heal(self, amount: int, body_part: DamageZone = None):
        """治疗统一HP"""
        return self.stats.heal(amount)

    def take_damage(self, damage: int, zone: DamageZone, penetration: int = 0) -> Tuple[int, str]:
        """受到伤害 - 统一HP + 分部位护甲"""
        armor_msg = ""
        armor = self.stats.get_armor(zone)

        # 护甲吸收伤害（头部和胸部有护甲）
        if armor and armor.armor_value > 0 and armor.durability > 0:
            actual_damage, durability_loss = armor.absorb_damage(damage)
            armor_reduction = damage - actual_damage
            if armor_reduction > 0:
                armor_msg = f"护甲抵挡了{armor_reduction}点伤害！(耐久-{durability_loss})"
            damage = actual_damage
        else:
            # 无护甲或护甲已损坏
            if zone != DamageZone.LEGS and armor and armor.max_durability > 0:
                armor_msg = "护甲已损坏！"

        # 应用部位伤害倍率
        actual_damage = int(damage * zone.multiplier)
        self.stats.take_damage(actual_damage)

        msg = f"你的{zone.cn_name}受到{actual_damage}点伤害！(HP:{self.stats.hp}/{self.stats.max_hp})"
        if armor_msg:
            msg += f" {armor_msg}"

        # 根据命中部位概率触发debuff
        debuff_msg = ""
        if zone == DamageZone.HEAD and random.random() < 0.4:
            self.stats.add_debuff('stunned', '眩晕', 2)
            debuff_msg = "头部受击，你陷入眩晕！"
        elif zone == DamageZone.CHEST and random.random() < 0.3:
            bleed_dmg = random.randint(5, 12)
            self.stats.add_debuff('bleeding', '流血', 4, bleed_dmg)
            debuff_msg = f"胸部受击，你开始流血！(-{bleed_dmg}/回合)"
        elif zone == DamageZone.LEGS and random.random() < 0.5:
            self.stats.add_debuff('slowed', '减速', 3)
            debuff_msg = "腿部受击，移动速度下降！"

        if debuff_msg:
            msg += f" {debuff_msg}"

        return actual_damage, msg

    def attack(self, target: Enemy, aim: str = "chest") -> Tuple[int, str]:
        """攻击敌人 - 使用简化的三部位瞄准系统"""
        weapon = self.equipment.primary_weapon
        if not weapon:
            return 0, "你没有装备武器！"

        if weapon.current_ammo <= 0:
            return 0, "弹药耗尽！需要换弹！"

        # 消耗弹药（使用配件加成后的射速）
        effective_fire_rate = weapon.get_effective_fire_rate()
        shots = min(effective_fire_rate, weapon.current_ammo)
        weapon.current_ammo -= shots

        # 计算基础命中（使用配件加成后的精度）
        base_accuracy = weapon.get_effective_accuracy()

        # 眩晕debuff降低命中率
        if self.stats.has_debuff('stunned'):
            base_accuracy *= 0.7

        # 瞄准部位映射和命中率修正
        aim_zone_map = {
            "head": DamageZone.HEAD,
            "chest": DamageZone.CHEST,
            "legs": DamageZone.LEGS
        }
        target_zone = aim_zone_map.get(aim, DamageZone.CHEST)

        # 瞄准修正：瞄准特定部位降低整体命中，但提高该部位的命中权重
        # 基础命中率 = 武器精度 * 部位基础命中率 * 瞄准修正
        aim_accuracy_modifier = {
            "head": 0.6,   # 瞄准头部降低整体命中率
            "chest": 1.0,  # 瞄准胸部正常
            "legs": 0.85   # 瞄准腿部略微降低
        }

        total_damage = 0
        hits = 0
        hit_zones = {}

        for _ in range(shots):
            # 计算这一发是否命中
            shot_accuracy = base_accuracy * aim_accuracy_modifier.get(aim, 1.0)

            if random.random() < shot_accuracy:
                # 命中后决定打中哪个部位
                # 如果瞄准特定部位，有更高概率打中该部位
                if aim == "head":
                    zone_weights = {DamageZone.HEAD: 0.5, DamageZone.CHEST: 0.35, DamageZone.LEGS: 0.15}
                elif aim == "legs":
                    zone_weights = {DamageZone.HEAD: 0.1, DamageZone.CHEST: 0.3, DamageZone.LEGS: 0.6}
                else:  # chest
                    zone_weights = {DamageZone.HEAD: 0.1, DamageZone.CHEST: 0.7, DamageZone.LEGS: 0.2}

                # 根据权重随机选择部位
                r = random.random()
                cumulative = 0
                hit_zone = DamageZone.CHEST
                for zone, weight in zone_weights.items():
                    cumulative += weight
                    if r < cumulative:
                        hit_zone = zone
                        break

                # 造成伤害（部位倍率）
                zone_damage = int(weapon.damage * hit_zone.multiplier)
                actual_damage = target.take_damage(zone_damage, weapon.penetration)
                total_damage += actual_damage
                hits += 1
                hit_zones[hit_zone.cn_name] = hit_zones.get(hit_zone.cn_name, 0) + 1

        if hits > 0:
            zone_str = "、".join([f"{k}×{v}" for k, v in hit_zones.items()])
            msg = f"你使用{weapon.name}射击，命中{hits}发（{zone_str}），造成{total_damage}点伤害！"
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
            if self.stats.debuffs:
                self.stats.clear_debuffs()
                msg += "清除了所有异常状态。"

        if "stop_bleed" in effect and effect["stop_bleed"]:
            if self.stats.has_debuff('bleeding'):
                self.stats.remove_debuff('bleeding')
                msg += "止住了流血。"

        if "pain_relief" in effect:
            self.stats.apply_pain_relief(effect["pain_relief"])
            msg += f"止痛效果持续{effect['pain_relief']}秒。"

        if "energy" in effect:
            self.stats.energy = min(100, self.stats.energy + effect["energy"])
            msg += f"恢复了{effect['energy']}点能量。"

        if "hydration" in effect:
            self.stats.hydration = min(100, self.stats.hydration + effect["hydration"])
            msg += f"恢复了{effect['hydration']}点水分。"

        if "stamina_boost" in effect:
            self.stats.stamina = min(100, self.stats.stamina + effect["stamina_boost"])
            msg += f"恢复了{effect['stamina_boost']}点耐力。"

        if "ap_boost" in effect:
            self.action_points = min(self.max_action_points, self.action_points + effect["ap_boost"])
            msg += f"恢复了{effect['ap_boost']}行动点。"

        if "regen" in effect:
            regen_amount = effect["regen"]
            regen_dur = effect.get("regen_duration", 3)
            self.stats.add_debuff('regen', '再生', regen_dur, -regen_amount)
            msg += f"持续恢复生命值{regen_amount}/回合，持续{regen_dur}回合。"

        if "reload_weapon" in effect:
            weapon = self.equipment.primary_weapon
            if weapon:
                ammo_type = effect.get("ammo_type", "")
                if not ammo_type or weapon.ammo_type == ammo_type:
                    weapon.current_ammo = weapon.mag_size
                    msg += f"{weapon.name}已补充弹药。"
                else:
                    msg += f"弹药类型不匹配！武器需要{weapon.ammo_type}。"
            else:
                msg += "没有装备武器。"

        if "repair_armor" in effect:
            repair_amount = effect["repair_armor"]
            head_armor = self.stats.head_armor
            chest_armor = self.stats.chest_armor

            repaired = 0
            if head_armor.max_durability > 0 or chest_armor.max_durability > 0:
                if head_armor.max_durability > 0 and (chest_armor.max_durability == 0 or head_armor.durability < chest_armor.durability):
                    repaired = head_armor.repair(repair_amount)
                    msg += f"头部护甲修复了{repaired}点耐久。"
                elif chest_armor.max_durability > 0:
                    repaired = chest_armor.repair(repair_amount)
                    msg += f"胸部护甲修复了{repaired}点耐久。"
                else:
                    msg += "没有可修理的护甲。"
            else:
                msg += "没有可修理的护甲。"

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
    SEARCH = "search"  # 搜索敌人背包
    DEAD = "dead"  # 死亡
    EXTRACTED = "extracted"  # 成功撤离

# ============== 突击行动管理 ==============
class Raid:
    """突击行动 - 支持载具和破译系统"""
    def __init__(self, map_data: dict):
        self.map_data = map_data
        self.zones = deepcopy(map_data["zones"])
        self.enemies: List[Enemy] = []
        self.vehicles: List[Vehicle] = []  # 地图中的载具
        self.time_elapsed: int = 0
        self.max_time: int = 60  # 最大行动时间（回合）
        self.loot_generated: bool = False
        self.active_extraction: str = ""  # 当前激活的撤离点ID
        self.visited_zones: set = set()  # 玩家访问过的区域
        self.pending_events: List[dict] = []  # 待通知的事件
        self.decode_manager: DecodeManager = DecodeManager()  # 破译管理器

    def spawn_vehicles(self):
        """在地图中生成载具"""
        # 根据地图类型生成不同的载具
        vehicle_spawns = []

        if "dam" in str(self.map_data.get("name", "")).lower() or "大坝" in self.map_data.get("name", ""):
            vehicle_spawns = [
                ("apc_m2_bradley", "dam_barracks"),
                ("apc_stryker", "dam_admin_district"),
            ]
        elif "溪谷" in self.map_data.get("name", ""):
            vehicle_spawns = [
                ("heli_little_bird", "valley_radar"),
                ("apc_bmp3", "valley_checkpoint"),
            ]
        elif "航天" in self.map_data.get("name", ""):
            vehicle_spawns = [
                ("heli_black_hawk", "space_launch_zone"),
                ("tank_t90", "space_h4"),
            ]
        elif "巴克什" in self.map_data.get("name", ""):
            vehicle_spawns = [
                ("apc_stryker", "baksh_bazaar"),
            ]

        for vehicle_id, zone_id in vehicle_spawns:
            if zone_id in self.zones:
                vehicle = Vehicle.create(vehicle_id)
                vehicle.current_zone = zone_id
                self.vehicles.append(vehicle)

    def get_vehicles_in_zone(self, zone_id: str) -> List[Vehicle]:
        """获取区域内的载具"""
        return [v for v in self.vehicles if v.current_zone == zone_id and not v.destroyed]

    def start_decode(self, item_id: str, item_name: str, decoder_id: str, operator_class: OperatorClass = None) -> Tuple[bool, str]:
        """开始破译物品"""
        item_data = LOOT_ITEMS.get(item_id, {})
        decode_time = item_data.get("decode_time", 3)

        # 计算职业加成
        class_bonus = 0.0
        if operator_class == OperatorClass.ENGINEER:
            class_bonus = DECODE_CONFIG["engineer_bonus"]
        elif operator_class == OperatorClass.RECON:
            class_bonus = DECODE_CONFIG["recon_bonus"]

        success = self.decode_manager.start_decode(item_id, item_name, decode_time, decoder_id, class_bonus)
        if success:
            return True, f"开始破译 {item_name}，预计需要 {max(1, int(decode_time * (1 - class_bonus)))} 回合"
        return False, "无法开始破译（可能已达到最大同时破译数量）"

    def set_active_extraction(self, spawn_zone: str):
        """设置激活的撤离点（距离出生点较远）"""
        self.active_extraction = select_distant_extraction(self.zones, spawn_zone)

    def spawn_enemies(self, player_level: int):
        """根据玩家等级生成敌人"""
        enemy_count = 5 + player_level * 2

        for i in range(enemy_count):
            # 根据等级选择敌人类型
            if player_level <= 2:
                enemy_type = random.choice(["scav_weak", "scav_weak", "scav_normal", "scav_shotgunner"])
            elif player_level <= 4:
                enemy_type = random.choice(["scav_normal", "scav_veteran", "scav_sniper", "scav_shotgunner", "pmc_medic"])
            elif player_level <= 6:
                enemy_type = random.choice(["scav_veteran", "pmc_grunt", "pmc_medic", "raider_assault", "scav_sniper"])
            elif player_level <= 8:
                enemy_type = random.choice(["pmc_grunt", "pmc_elite", "pmc_heavy", "raider_assault", "raider_lmg"])
            else:
                enemy_type = random.choice(["pmc_elite", "pmc_heavy", "raider_assault", "raider_lmg", "raider_sniper"])

            # 小概率刷Boss
            if random.random() < 0.06 and not any(e.is_boss for e in self.enemies):
                enemy_type = random.choice(["boss_killa", "boss_guardian"])

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
        self.pending_events = []

        # 更新破译进度
        completed_decodes = self.decode_manager.tick()
        for item_id, msg, rewards in completed_decodes:
            self.pending_events.append({
                "type": "decode_complete",
                "item_id": item_id,
                "message": f"🔓 {msg} 获得奖励: ${rewards['money']}",
                "rewards": rewards
            })

        # 更新载具状态
        for vehicle in self.vehicles:
            vehicle.tick()

        # 随机事件系统（每5回合检查一次）
        if self.time_elapsed > 0 and self.time_elapsed % 5 == 0:
            event_roll = random.random()
            if event_roll < 0.25:
                self._event_airdrop()
            elif event_roll < 0.40:
                self._event_reinforcements()
            elif event_roll < 0.50:
                self._event_supply_cache()
            elif event_roll < 0.58:
                self._event_gas_zone()
            elif event_roll < 0.68:
                self._event_vehicle_spawn()  # 新增：载具刷新事件

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

    def _event_vehicle_spawn(self):
        """载具刷新事件"""
        zone_ids = [zid for zid, z in self.zones.items()
                   if not z.get("is_spawn") and not z.get("is_extract")]
        if not zone_ids:
            return
        target = random.choice(zone_ids)

        # 随机选择一种载具
        vehicle_options = ["apc_stryker", "apc_bmp3", "heli_little_bird"]
        vehicle_id = random.choice(vehicle_options)

        vehicle = Vehicle.create(vehicle_id)
        vehicle.current_zone = target
        self.vehicles.append(vehicle)

        self.pending_events.append({
            "type": "vehicle_spawn",
            "zone": target,
            "zone_name": self.zones[target]["name"],
            "vehicle_name": vehicle.name,
            "message": f"🚗 一辆 {vehicle.name} 已部署到 {self.zones[target]['name']}！"
        })

    def _event_airdrop(self):
        """空投事件 - 在随机区域生成高价值物品"""
        zone_ids = [zid for zid, z in self.zones.items()
                   if not z.get("is_spawn") and not z.get("is_extract")]
        if not zone_ids:
            return
        target = random.choice(zone_ids)
        zone = self.zones[target]
        # 添加高价值空投物品
        airdrop_items = [
            ("loot_gpu", LOOT_ITEMS.get("loot_gpu", {})),
            ("loot_thermal_scope", LOOT_ITEMS.get("loot_thermal_scope", {})),
            ("loot_diamond", LOOT_ITEMS.get("loot_diamond", {})),
        ]
        chosen_id, chosen_data = random.choice(airdrop_items)
        if chosen_data:
            if "loot" not in zone:
                zone["loot"] = []
            zone["loot"].append({
                "id": f"airdrop_{random.randint(1000, 9999)}",
                "item_id": chosen_id,
                "data": chosen_data
            })
        self.pending_events.append({
            "type": "airdrop",
            "zone": target,
            "zone_name": zone["name"],
            "message": f"📦 空投物资已投放到 {zone['name']}！"
        })

    def _event_reinforcements(self):
        """敌人增援事件"""
        zone_ids = [zid for zid, z in self.zones.items()
                   if not z.get("is_spawn") and not z.get("is_extract")]
        if not zone_ids:
            return
        target = random.choice(zone_ids)
        # 添加2-3个增援敌人
        reinforcement_types = ["scav_veteran", "pmc_grunt", "raider_assault"]
        count = random.randint(2, 3)
        for i in range(count):
            etype = random.choice(reinforcement_types)
            edata = ENEMY_TYPES[etype]
            enemy = Enemy(
                id=f"reinforce_{self.time_elapsed}_{i}",
                name=edata["name"] + "(增援)",
                hp=edata["hp"], max_hp=edata["hp"],
                armor_class=edata["armor_class"],
                accuracy=edata["accuracy"],
                weapon_id=edata["weapon"],
                aggro_range=edata["aggro_range"],
                loot_table=edata["loot_table"],
                xp=int(edata["xp"] * 1.5),
                is_boss=False
            )
            enemy.current_zone = target
            self.enemies.append(enemy)
        self.pending_events.append({
            "type": "reinforcements",
            "zone": target,
            "zone_name": self.zones[target]["name"],
            "message": f"⚠️ 敌人增援部队已抵达 {self.zones[target]['name']}！({count}人)"
        })

    def _event_supply_cache(self):
        """补给站发现事件 - 在随机区域添加医疗/弹药"""
        zone_ids = [zid for zid, z in self.zones.items()
                   if not z.get("is_spawn") and not z.get("is_extract")]
        if not zone_ids:
            return
        target = random.choice(zone_ids)
        zone = self.zones[target]
        if "loot" not in zone:
            zone["loot"] = []
        supply_items = [
            ("med_ifak", CONSUMABLES.get("med_ifak", {})),
            ("med_salewa", CONSUMABLES.get("med_salewa", {})),
            ("stim_adrenaline", CONSUMABLES.get("stim_adrenaline", {})),
            ("ammo_box_556", CONSUMABLES.get("ammo_box_556", {})),
        ]
        for item_id, item_data in random.sample(supply_items, 2):
            if item_data:
                zone["loot"].append({
                    "id": f"supply_{random.randint(1000, 9999)}",
                    "item_id": item_id,
                    "data": item_data
                })
        self.pending_events.append({
            "type": "supply",
            "zone": target,
            "zone_name": zone["name"],
            "message": f"🏥 补给物资已在 {zone['name']} 刷新！"
        })

    def _event_gas_zone(self):
        """毒气区域事件 - 标记区域为危险"""
        zone_ids = [zid for zid, z in self.zones.items()
                   if not z.get("is_spawn") and not z.get("is_extract") and not z.get("gas_active")]
        if not zone_ids:
            return
        target = random.choice(zone_ids)
        self.zones[target]["gas_active"] = True
        self.zones[target]["gas_duration"] = 10  # 持续10回合
        self.pending_events.append({
            "type": "gas",
            "zone": target,
            "zone_name": self.zones[target]["name"],
            "message": f"☠️ 毒气扩散到 {self.zones[target]['name']}！进入该区域会持续受到伤害！"
        })

# ============== 任务系统 ==============
MISSION_TEMPLATES = {
    "kill_scavs": {
        "name": "清剿游荡者",
        "description": "击杀{target}名游荡者",
        "type": "kill",
        "target_type": "scav",
        "target_count": [3, 5, 8],
        "rewards": {"money": [2000, 4000, 8000], "xp": [100, 200, 400]},
        "department": "战斗部门"
    },
    "kill_pmc": {
        "name": "猎杀佣兵",
        "description": "击杀{target}名佣兵或突袭者",
        "type": "kill",
        "target_type": "pmc",
        "target_count": [2, 3, 5],
        "rewards": {"money": [5000, 8000, 15000], "xp": [200, 400, 800]},
        "department": "战斗部门"
    },
    "kill_boss": {
        "name": "斩首行动",
        "description": "击杀任意Boss",
        "type": "kill",
        "target_type": "boss",
        "target_count": [1],
        "rewards": {"money": [20000], "xp": [1000]},
        "department": "战斗部门"
    },
    "extract_loot": {
        "name": "物资回收",
        "description": "成功撤离并携带价值{target}以上的物资",
        "type": "extract_value",
        "target_count": [5000, 15000, 30000],
        "rewards": {"money": [3000, 8000, 15000], "xp": [150, 300, 600]},
        "department": "后勤部门"
    },
    "extract_survive": {
        "name": "安全撤离",
        "description": "成功撤离{target}次",
        "type": "extract_count",
        "target_count": [1, 3, 5],
        "rewards": {"money": [1000, 5000, 12000], "xp": [100, 300, 600]},
        "department": "后勤部门"
    },
    "visit_zones": {
        "name": "区域侦察",
        "description": "在一次行动中访问{target}个不同区域",
        "type": "visit",
        "target_count": [5, 8, 12],
        "rewards": {"money": [2000, 5000, 10000], "xp": [100, 250, 500]},
        "department": "战术部门"
    },
    "headshot_kills": {
        "name": "精准射手",
        "description": "瞄准头部击杀{target}名敌人",
        "type": "headshot",
        "target_count": [2, 4],
        "rewards": {"money": [4000, 10000], "xp": [200, 500]},
        "department": "战斗部门"
    },
    "use_medkits": {
        "name": "战地医疗",
        "description": "在行动中使用{target}个医疗物品",
        "type": "use_medical",
        "target_count": [3, 5],
        "rewards": {"money": [1500, 4000], "xp": [100, 250]},
        "department": "医疗部门"
    }
}

@dataclass
class Mission:
    """任务实例"""
    id: str
    template_id: str
    name: str
    description: str
    mission_type: str
    department: str
    target: int
    progress: int = 0
    completed: bool = False
    reward_money: int = 0
    reward_xp: int = 0

    def update_progress(self, amount: int = 1) -> bool:
        """更新任务进度，返回是否刚完成"""
        if self.completed:
            return False
        self.progress = min(self.progress + amount, self.target)
        if self.progress >= self.target:
            self.completed = True
            return True
        return False

def generate_missions(count: int = 3) -> List[Mission]:
    """生成随机任务"""
    templates = list(MISSION_TEMPLATES.items())
    selected = random.sample(templates, min(count, len(templates)))
    missions = []
    for i, (tid, tmpl) in enumerate(selected):
        diff = random.randint(0, len(tmpl["target_count"]) - 1)
        target = tmpl["target_count"][diff]
        rewards = tmpl["rewards"]
        missions.append(Mission(
            id=f"mission_{i}_{random.randint(100,999)}",
            template_id=tid,
            name=tmpl["name"],
            description=tmpl["description"].format(target=target),
            mission_type=tmpl["type"],
            department=tmpl["department"],
            target=target,
            reward_money=rewards["money"][diff],
            reward_xp=rewards["xp"][diff]
        ))
    return missions

# ============== 主游戏类 ==============
class Game:
    """主游戏类 - 支持3人小队系统"""
    def __init__(self, player_operator_id: str = "operator_wyatt"):
        self.state = GameState.MAIN_MENU
        self.player = Player(operator_id=player_operator_id)
        self.squad: Optional[Squad] = None  # 3人小队
        self.current_raid: Optional[Raid] = None
        self.current_enemy: Optional[Enemy] = None
        self.current_vehicle_enemy: Optional[Vehicle] = None  # 载具战斗目标
        self.messages: List[str] = []
        self.game_log: List[str] = []
        self.missions: List[Mission] = generate_missions(3)
        self.completed_missions: int = 0
        self.raid_kills_this_run: int = 0
        self.raid_headshots: int = 0
        self.raid_medical_used: int = 0
        self.total_extractions: int = 0

        # 可解锁的干员列表
        self.unlocked_operators = ["operator_wyatt"]  # 初始只有一个
        self.available_operators = list(OPERATORS.keys())

        # 初始装备
        self._give_starting_gear()

    def create_squad(self, member_operator_ids: List[str] = None):
        """创建3人小队"""
        if member_operator_ids is None:
            # 默认小队配置
            member_operator_ids = ["operator_wyatt", "operator_luna", "operator_hack"]

        self.squad = Squad(squad_id=f"squad_{random.randint(1000,9999)}", name="三角洲小队")

        for i, op_id in enumerate(member_operator_ids[:3]):  # 最多3人
            if op_id in OPERATORS:
                operator = Operator.create(op_id, is_player=(i == 0), is_ai=(i > 0))
                stats = PlayerStats()
                equipment = EquipmentSlots()

                member = SquadMember(
                    member_id=f"member_{i}",
                    name=operator.name,
                    operator=operator,
                    stats=stats,
                    equipment=equipment
                )
                self.squad.add_member(member)

        # 玩家始终是第一个成员
        if self.squad.members:
            self.player.stats = self.squad.members[0].stats
            self.player.equipment = self.squad.members[0].equipment

    def get_player_member(self) -> Optional[SquadMember]:
        """获取玩家控制的小队成员"""
        if self.squad:
            return self.squad.members[0] if self.squad.members else None
        return None

    def select_operator(self, operator_id: str) -> Tuple[bool, str]:
        """切换干员"""
        if operator_id not in self.unlocked_operators:
            return False, f"干员 {operator_id} 未解锁"
        if operator_id not in OPERATORS:
            return False, f"无效的干员ID"
        # 创建新干员实例
        self.player.operator = Operator.create(operator_id, is_player=True)
        # 如果有小队，更新小队成员
        if self.squad and self.squad.members:
            self.squad.members[0].operator = self.player.operator
        return True, f"已选择干员: {self.player.operator.name}"

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
        self.player.equipment.equip_armor(armor, self.player.stats)

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

    def track_mission(self, event_type: str, amount: int = 1, value: int = 0):
        """追踪任务进度"""
        for mission in self.missions:
            if mission.completed:
                continue
            triggered = False
            if event_type == "kill_scav" and mission.mission_type == "kill" and mission.template_id == "kill_scavs":
                triggered = mission.update_progress(amount)
            elif event_type == "kill_pmc" and mission.mission_type == "kill" and mission.template_id == "kill_pmc":
                triggered = mission.update_progress(amount)
            elif event_type == "kill_boss" and mission.mission_type == "kill" and mission.template_id == "kill_boss":
                triggered = mission.update_progress(amount)
            elif event_type == "headshot" and mission.mission_type == "headshot":
                triggered = mission.update_progress(amount)
            elif event_type == "extract" and mission.mission_type == "extract_count":
                triggered = mission.update_progress(amount)
            elif event_type == "extract_value" and mission.mission_type == "extract_value":
                if value >= mission.target:
                    triggered = mission.update_progress(mission.target)
            elif event_type == "visit" and mission.mission_type == "visit":
                if self.current_raid:
                    mission.progress = len(self.current_raid.visited_zones)
                    if mission.progress >= mission.target and not mission.completed:
                        mission.completed = True
                        triggered = True
            elif event_type == "use_medical" and mission.mission_type == "use_medical":
                triggered = mission.update_progress(amount)
            if triggered:
                self.add_message(f"🎯 任务完成: {mission.name}！奖励: ${mission.reward_money} + {mission.reward_xp}XP")
                self.player.stats.money += mission.reward_money
                self.player.add_xp(mission.reward_xp)
                self.completed_missions += 1

    def refresh_missions(self):
        """刷新任务（完成的任务替换为新的）"""
        new_missions = []
        for m in self.missions:
            if m.completed:
                new_missions.extend(generate_missions(1))
            else:
                new_missions.append(m)
        self.missions = new_missions

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
        self.current_raid.spawn_vehicles()  # 生成载具

        # 随机选择出生点
        spawn_zones = [zid for zid, z in self.current_raid.zones.items() if z.get("is_spawn")]
        spawn_zone = random.choice(spawn_zones)
        self.player.current_zone = spawn_zone

        # 设置撤离点并标记已访问区域
        self.current_raid.set_active_extraction(spawn_zone)
        self.current_raid.visited_zones.add(spawn_zone)

        # 如果有小队，所有成员部署到同一位置
        if self.squad:
            for member in self.squad.members:
                # 为AI成员生成基础装备
                if member.operator.is_ai:
                    self._give_ai_gear(member)

        self.state = GameState.RAID
        self.add_message(f"=== 行动开始 ===")
        self.add_message(f"你已部署到 {map_data['name']}")
        self.add_message(f"当前位置: {self.current_raid.zones[self.player.current_zone]['name']}")
        self.add_message(f"撤离点: {self.current_raid.zones[self.current_raid.active_extraction]['name']}")

        # 显示干员信息
        self.add_message(f"干员: {self.player.operator.name} ({self.player.operator.operator_class.cn_name})")

        # 显示区域内的载具
        vehicles = self.current_raid.get_vehicles_in_zone(spawn_zone)
        if vehicles:
            self.add_message(f"发现载具: {', '.join([v.name for v in vehicles])}")

        # 显示撤离点距离提示
        distance = get_zone_distance(self.current_raid.zones, spawn_zone, self.current_raid.active_extraction)
        if distance > 7:
            self.add_message("撤离点非常远，你需要穿越大半个地图！")
        elif distance > 5:
            self.add_message("撤离点较远，小心行事。")
        else:
            self.add_message("撤离点不算太远。")

    def _give_ai_gear(self, member: SquadMember):
        """为AI队友生成装备"""
        # 根据职业给装备
        op_class = member.operator.operator_class

        if op_class == OperatorClass.ASSAULT:
            weapon_id = "ar_ak74n"
        elif op_class == OperatorClass.SUPPORT:
            weapon_id = "lmg_pkm"
        elif op_class == OperatorClass.RECON:
            weapon_id = "dmr_svd"
        else:  # ENGINEER
            weapon_id = "shotgun_saiga12"

        weapon_data = WEAPONS.get(weapon_id, WEAPONS["pistol_p226"])
        weapon = Weapon(
            id=f"ai_{member.member_id}_weapon",
            name=weapon_data["name"],
            weight=weapon_data["weight"],
            value=weapon_data["value"],
            rarity=weapon_data["rarity"],
            damage=weapon_data["damage"],
            accuracy=weapon_data["accuracy"],
            fire_rate=weapon_data["fire_rate"],
            penetration=weapon_data["penetration"],
            ammo_type=weapon_data.get("ammo_type", ""),
            mag_size=weapon_data["mag_size"],
            current_ammo=weapon_data["mag_size"]
        )
        member.equipment.equip_weapon(weapon, "primary")

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

        # 检查是否需要钥匙
        required_key = target_zone.get("requires_key")
        if required_key:
            key_mapping = {
                "lab_keycard": "key_lab_keycard",
                "armory_key": "key_armory",
                "server_keycard": "key_server",
            }
            key_item_id = key_mapping.get(required_key, required_key)
            has_key = False
            for item in self.player.equipment.backpack.get_all_items():
                if isinstance(item, LootItem) and item.id.startswith("loot_") and key_item_id in item.id:
                    has_key = True
                    break
                if item.name and key_item_id.replace("key_", "") in item.id:
                    has_key = True
                    break
            # 检查仓库中的钥匙
            for item in self.player.stash_items:
                if hasattr(item, 'item_type') and item.item_type == '钥匙':
                    if required_key in item.id or key_item_id in item.id:
                        has_key = True
                        break
            if not has_key:
                zone_name = target_zone.get('name', zone_id)
                return False, f"{zone_name}已锁定！需要对应钥匙才能进入。"

        # 消耗行动点（减速debuff增加50%消耗）
        ap_cost = 2
        if self.player.stats.has_debuff('slowed'):
            ap_cost = int(ap_cost * 1.5)
        if self.player.action_points < ap_cost:
            self.handle_action_failed()
            return False, "行动力耗尽！行动失败，丢失所有物品..."

        self.player.action_points -= ap_cost
        self.player.current_zone = zone_id

        # 标记已访问区域
        self.current_raid.visited_zones.add(zone_id)

        msg = f"你移动到了 {target_zone['name']}。"
        self.add_message(msg)

        # 毒气区域伤害
        if target_zone.get("gas_active"):
            gas_dmg = random.randint(15, 30)
            self.player.stats.take_damage(gas_dmg)
            self.add_message(f"☠️ 毒气区域！你受到{gas_dmg}点毒气伤害！")
            if not self.player.stats.is_alive():
                self.state = GameState.DEAD
                self.add_message("你被毒气夺去了生命...")
                return True, msg

        # 检查是否到达撤离点
        if zone_id == self.current_raid.active_extraction:
            self.add_message("★ 你到达了撤离点！可以尝试撤离。")

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

        ap_cost = 3
        if self.player.action_points < ap_cost:
            self.handle_action_failed()
            return False, "行动力耗尽！行动失败，丢失所有物品..."

        self.player.action_points -= ap_cost

        loot = zone.get("loot", [])
        if not loot:
            msg = "你仔细搜索了这个区域，但没有发现任何有价值的东西。"
            self.add_message(msg)
            return True, msg

        # 不自动拾取，只提示发现了物品
        msg = f"你发现了 {len(loot)} 件物品！点击拾取按钮将物品放入背包。"
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
            # 攻击消耗行动点
            ap_cost = 3
            if self.player.action_points < ap_cost:
                self.handle_action_failed()
                return False, "行动力耗尽！行动失败，丢失所有物品..."
            self.player.action_points -= ap_cost

            damage, attack_msg = self.player.attack(self.current_enemy, target or "body")
            msg = attack_msg

            if not self.current_enemy.is_alive():
                # 敌人死亡
                self.player.add_xp(self.current_enemy.xp)
                self.player.kills += 1
                msg += f"\n获得 {self.current_enemy.xp} 经验值！"
                # 任务追踪
                enemy_name = self.current_enemy.name.lower()
                if self.current_enemy.is_boss:
                    self.track_mission("kill_boss")
                elif "佣兵" in enemy_name or "突袭" in enemy_name:
                    self.track_mission("kill_pmc")
                else:
                    self.track_mission("kill_scav")
                if target == "head":
                    self.track_mission("headshot")

                # 掉落物品
                loot_table = LOOT_TABLES.get(self.current_enemy.loot_table, [])
                for item_id, chance in loot_table:
                    if random.random() < chance:
                        if item_id in LOOT_ITEMS:
                            item_data = LOOT_ITEMS[item_id]
                            item = LootItem(
                                id=f"loot_{random.randint(1000, 9999)}",
                                name=item_data["name"],
                                weight=0.1,
                                grid=item_data.get("grid", 1),
                                value=item_data["value"],
                                rarity=item_data["rarity"],
                                item_type=item_data.get("type", "物资"),
                                description=item_data.get("description", "")
                            )
                            if self.player.equipment.backpack.add_item(item):
                                msg += f"\n获得: {item.name}"

                # 检查敌人背包是否有物品可搜索
                if self.current_enemy.backpack and self.current_enemy.backpack.get_all_items():
                    self.state = GameState.SEARCH
                    msg += f"\n\n📦 {self.current_enemy.name}的背包可以搜索！"
                else:
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

        elif action == "grenade":
            # 使用手雷/闪光弹/烟雾弹
            grenade = None
            for item in self.player.equipment.backpack.get_all_items():
                if isinstance(item, Consumable) and "grenade_type" in item.effect:
                    if target and item.effect.get("grenade_type") != target:
                        continue
                    grenade = item
                    break
            if grenade:
                eff = grenade.effect
                g_type = eff.get("grenade_type", "frag")
                self.player.equipment.backpack.remove_item(grenade.id)
                if g_type == "frag":
                    g_dmg = eff.get("grenade_damage", 120)
                    actual = self.current_enemy.take_damage(g_dmg, 0)
                    msg = f"你投出{grenade.name}！爆炸造成{actual}点伤害！"
                    if not self.current_enemy.is_alive():
                        self.player.add_xp(self.current_enemy.xp)
                        self.player.kills += 1
                        msg += f"\n{self.current_enemy.name}被炸死！获得{self.current_enemy.xp}经验！"
                        self.current_enemy = None
                        self.state = GameState.RAID
                elif g_type == "flash":
                    stun_dur = eff.get("stun_duration", 2)
                    msg = f"你投出{grenade.name}！敌人被致盲{stun_dur}回合！"
                    self.current_enemy.accuracy *= 0.3
                elif g_type == "smoke":
                    msg = f"你释放{grenade.name}，烟雾弥漫！趁机撤退！"
                    self.current_enemy = None
                    self.state = GameState.RAID
            else:
                msg = "没有可用的投掷物！"
                success = False

        elif action == "flee":
            # 撤退（烟雾弹提高成功率）
            flee_chance = 0.5
            for item in self.player.equipment.backpack.get_all_items():
                if isinstance(item, Consumable) and item.effect.get("grenade_type") == "smoke":
                    flee_chance += item.effect.get("flee_bonus", 0.3)
                    break
            if random.random() < flee_chance:
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

    def search_enemy_backpack(self, action: str, item_id: str = None) -> Tuple[bool, str]:
        """搜索敌人背包"""
        if self.state != GameState.SEARCH:
            return False, "当前不在搜索状态！"

        if not self.current_enemy or not self.current_enemy.backpack:
            self.state = GameState.RAID
            return False, "没有可搜索的背包！"

        msg = ""

        if action == "take_all":
            # 拿走所有物品
            items = self.current_enemy.backpack.get_all_items()
            taken = 0
            for item in items[:]:
                if self.player.equipment.backpack.add_item(item):
                    self.current_enemy.backpack.remove_item(item.id)
                    taken += 1
                    msg += f"\n获得: {item.name}"
            if taken == 0:
                msg = "背包已满，无法拿取更多物品！"
            else:
                msg = f"拿走了{taken}件物品！" + msg

        elif action == "take_one" and item_id:
            # 拿走指定物品
            item = self.current_enemy.backpack.get_item(item_id)
            if item:
                if self.player.equipment.backpack.add_item(item):
                    self.current_enemy.backpack.remove_item(item_id)
                    msg = f"获得: {item.name}"
                else:
                    msg = "背包已满！"
            else:
                msg = "找不到该物品！"

        elif action == "leave":
            # 离开搜索
            self.current_enemy = None
            self.state = GameState.RAID
            msg = "你离开了敌人的背包。"

        # 检查是否还有物品
        if self.current_enemy and (not self.current_enemy.backpack or not self.current_enemy.backpack.get_all_items()):
            self.current_enemy = None
            self.state = GameState.RAID
            if action != "leave":
                msg += "\n\n背包已空。"

        self.add_message(msg)
        return True, msg

    def try_extract(self) -> Tuple[bool, str]:
        """尝试撤离"""
        if self.state != GameState.RAID:
            return False, "当前不在行动中！"

        zone = self.current_raid.get_zone(self.player.current_zone)

        # 检查是否在激活的撤离点
        if self.player.current_zone != self.current_raid.active_extraction:
            # 检查是否是其他撤离点
            if zone.get("is_extract"):
                return False, f"这个撤离点不可用！你需要前往 {self.current_raid.zones[self.current_raid.active_extraction]['name']}。"
            return False, "当前区域没有撤离点！"

        condition = zone.get("extract_condition", {})
        extract_type = condition.get("type", "open")

        if extract_type == "paid":
            cost = condition.get("cost", 5000)
            if self.player.stats.money < cost:
                return False, f"撤离费用不足！需要 ${cost}，你只有 ${self.player.stats.money}"
            self.player.stats.money -= cost
            self.add_message(f"支付了 ${cost} 撤离费用。")
        elif extract_type == "wait":
            wait_time = condition.get("wait_time", 30)
            self.add_message(f"撤离点需要等待 {wait_time} 秒...")
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

        # 将背包物品移入仓库
        backpack_items = self.player.equipment.backpack.get_all_items()
        for item in backpack_items:
            self.player.stash_items.append(item)
        self.player.equipment.backpack.clear()

        msg = f"=== 撤离成功 ===\n"
        msg += f"获得物资价值: {loot_value}\n"
        if backpack_items:
            msg += f"物品已存入仓库: {len(backpack_items)} 件\n"
        msg += f"当前余额: {self.player.stats.money}"
        self.add_message(msg)

        # 任务追踪
        self.total_extractions += 1
        self.track_mission("extract", 1)
        self.track_mission("extract_value", value=loot_value)
        self.track_mission("visit")
        # 完成的任务自动刷新
        self.refresh_missions()

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

    def handle_action_failed(self):
        """处理行动失败（行动点耗尽）"""
        self.state = GameState.DEAD
        msg = "=== 行动力耗尽 ===\n"
        msg += "你的行动力已耗尽，无法继续行动！\n"
        msg += "在撤离前力竭倒下，丢失了背包中的所有物品...\n"

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

    def buy_weapon(self, weapon_id: str) -> Tuple[bool, str]:
        """购买武器"""
        if weapon_id not in WEAPONS:
            return False, "武器不存在！"

        weapon_data = WEAPONS[weapon_id]
        price = weapon_data["value"]

        if self.player.stats.money < price:
            return False, f"金钱不足！需要 {price} 金币"

        self.player.stats.money -= price
        weapon = Weapon(
            id=f"{weapon_id}_{len(self.player.stash_weapons)}",
            name=weapon_data["name"],
            damage=weapon_data["damage"],
            accuracy=weapon_data["accuracy"],
            fire_rate=weapon_data["fire_rate"],
            penetration=weapon_data["penetration"],
            mag_size=weapon_data["mag_size"],
            weight=weapon_data["weight"],
            value=price,
            rarity=weapon_data["rarity"]
        )
        self.player.stash_weapons.append(weapon)
        return True, f"购买了 {weapon.name}，花费 {price} 金币"

    def buy_armor(self, armor_id: str) -> Tuple[bool, str]:
        """购买护甲"""
        if armor_id not in ARMORS:
            return False, "护甲不存在！"

        armor_data = ARMORS[armor_id]
        price = armor_data["value"]

        if self.player.stats.money < price:
            return False, f"金钱不足！需要 {price} 金币"

        self.player.stats.money -= price
        armor = Armor(
            id=f"{armor_id}_{len(self.player.stash_armors)}",
            name=armor_data["name"],
            durability=armor_data["durability"],
            max_durability=armor_data["max_durability"],
            armor_class=armor_data["class"],
            weight=armor_data["weight"],
            value=price,
            rarity=armor_data["rarity"]
        )
        self.player.stash_armors.append(armor)
        return True, f"购买了 {armor.name}，花费 {price} 金币"

    def equip_weapon(self, weapon_id: str) -> Tuple[bool, str]:
        """从仓库装备武器"""
        for weapon in self.player.stash_weapons:
            if weapon.id == weapon_id:
                # 将当前武器放回仓库
                if self.player.equipment.primary_weapon:
                    self.player.stash_weapons.append(self.player.equipment.primary_weapon)
                self.player.equipment.primary_weapon = weapon
                self.player.stash_weapons.remove(weapon)
                return True, f"装备了 {weapon.name}"
        return False, "找不到该武器"

    def equip_armor(self, armor_id: str) -> Tuple[bool, str]:
        """从仓库装备护甲"""
        for armor in self.player.stash_armors:
            if armor.id == armor_id:
                # 将当前护甲放回仓库
                if self.player.equipment.armor:
                    self.player.stash_armors.append(self.player.equipment.armor)
                self.player.equipment.equip_armor(armor, self.player.stats)
                self.player.stash_armors.remove(armor)
                return True, f"装备了 {armor.name}"
        return False, "找不到该护甲"

    def unequip_weapon(self) -> Tuple[bool, str]:
        """卸下当前武器"""
        if self.player.equipment.primary_weapon:
            weapon = self.player.equipment.primary_weapon
            self.player.stash_weapons.append(weapon)
            self.player.equipment.primary_weapon = None
            return True, f"卸下了 {weapon.name}"
        return False, "没有装备武器"

    def unequip_armor(self) -> Tuple[bool, str]:
        """卸下当前护甲"""
        if self.player.equipment.armor:
            armor = self.player.equipment.armor
            self.player.stash_armors.append(armor)
            self.player.equipment.armor = None
            # 清除护甲状态
            self.player.stats.chest_armor = ArmorStatus()
            return True, f"卸下了 {armor.name}"
        return False, "没有装备护甲"

    def unequip_helmet(self) -> Tuple[bool, str]:
        """卸下当前头盔"""
        if self.player.equipment.helmet:
            helmet = self.player.equipment.helmet
            self.player.stash_helmets.append(helmet)
            self.player.equipment.helmet = None
            # 清除头盔护甲状态
            self.player.stats.head_armor = ArmorStatus()
            return True, f"卸下了 {helmet.name}"
        return False, "没有装备头盔"

    def unequip_all(self) -> str:
        """卸下所有装备"""
        msgs = []
        success, msg = self.unequip_weapon()
        if success:
            msgs.append(msg)
        success, msg = self.unequip_armor()
        if success:
            msgs.append(msg)
        success, msg = self.unequip_helmet()
        if success:
            msgs.append(msg)
        return "\n".join(msgs) if msgs else "没有可卸下的装备"

    def drop_backpack_item(self, item_id: str) -> Tuple[bool, str]:
        """丢弃背包中的物品到当前区域"""
        item = self.player.equipment.backpack.remove_item(item_id)
        if item:
            # 将物品放入当前区域的战利品列表
            if self.state == GameState.RAID and self.current_raid:
                zone = self.current_raid.get_zone(self.player.current_zone)
                if zone:
                    if "loot" not in zone:
                        zone["loot"] = []
                    zone["loot"].append({
                        "id": item.id,
                        "item_id": item.id,
                        "data": {
                            "name": item.name,
                            "weight": item.weight,
                            "value": item.value,
                            "rarity": item.rarity,
                            "type": getattr(item, 'item_type', '物资'),
                            "description": getattr(item, 'description', ''),
                            "grid": getattr(item, 'grid', 1)
                        }
                    })
            return True, f"丢弃了 {item.name}"
        return False, "找不到该物品"

    def pickup_loot(self, loot_id: str) -> Tuple[bool, str]:
        """从当前区域拾取物品到背包"""
        if self.state != GameState.RAID:
            return False, "当前不在行动中！"

        zone = self.current_raid.get_zone(self.player.current_zone)
        if not zone:
            return False, "区域错误！"

        loot_list = zone.get("loot", [])
        for loot_entry in loot_list[:]:
            if loot_entry["id"] == loot_id:
                item_data = loot_entry["data"]

                # 检查是否是可破译物品
                if item_data.get("type") == "可破译":
                    decode_time = item_data.get("decode_time", 3)
                    return False, f"此物品需要破译！使用 decode 命令开始破译（需要{decode_time}回合）"

                item = LootItem(
                    id=loot_entry["id"],
                    name=item_data["name"],
                    weight=item_data.get("weight", 0.1),
                    value=item_data["value"],
                    rarity=item_data["rarity"],
                    item_type=item_data.get("type", "物资"),
                    description=item_data.get("description", ""),
                    grid=item_data.get("grid", 1)
                )

                # 检查背包容量（考虑物品占用格子数）
                if not self.player.equipment.backpack.can_fit(item):
                    free = self.player.equipment.backpack.get_free_slots()
                    return False, f"背包容量不足！需要 {item.grid} 格，剩余 {free} 格"

                self.player.equipment.backpack.add_item(item)
                zone["loot"].remove(loot_entry)
                return True, f"拾取了 {item.name} ({item.grid}格)"

        return False, "找不到该物品"

    def start_decode(self, loot_id: str) -> Tuple[bool, str]:
        """开始破译物品"""
        if self.state != GameState.RAID:
            return False, "当前不在行动中！"

        zone = self.current_raid.get_zone(self.player.current_zone)
        if not zone:
            return False, "区域错误！"

        loot_list = zone.get("loot", [])
        for loot_entry in loot_list[:]:
            if loot_entry["id"] == loot_id:
                item_data = loot_entry["data"]
                if item_data.get("type") != "可破译":
                    return False, "此物品不需要破译！"

                ap_cost = 2
                if self.player.action_points < ap_cost:
                    return False, "行动力不足！"

                self.player.action_points -= ap_cost

                success, msg = self.current_raid.start_decode(
                    loot_entry["id"],
                    item_data["name"],
                    self.player.name,
                    self.player.operator.operator_class
                )

                if success:
                    zone["loot"].remove(loot_entry)
                    self.add_message(msg)

                return success, msg

        return False, "找不到该物品！"

    def board_vehicle(self, vehicle_id: str, as_driver: bool = False) -> Tuple[bool, str]:
        """登上载具"""
        if self.state != GameState.RAID:
            return False, "当前不在行动中！"

        vehicles = self.current_raid.get_vehicles_in_zone(self.player.current_zone)
        for vehicle in vehicles:
            if vehicle.vehicle_id == vehicle_id or vehicle.name == vehicle_id:
                success, msg = self.player.board_vehicle(vehicle, as_driver)
                if success:
                    self.add_message(msg)
                return success, msg

        return False, "找不到该载具！"

    def exit_vehicle(self) -> Tuple[bool, str]:
        """离开载具"""
        success, msg = self.player.exit_vehicle()
        if success:
            self.add_message(msg)
        return success, msg

    def use_operator_skill(self, skill_type: str = "primary") -> Tuple[bool, str]:
        """使用干员技能"""
        success, msg = self.player.use_skill(skill_type)
        if success:
            self.add_message(f"🎯 {msg}")
        return success, msg

    def move_to_stash(self, item_id: str) -> Tuple[bool, str]:
        """将背包物品移到仓库"""
        item = self.player.equipment.backpack.remove_item(item_id)
        if item:
            self.player.stash_items.append(item)
            return True, f"{item.name} 已移至仓库"
        return False, "找不到该物品"

    def move_to_backpack(self, item_id: str) -> Tuple[bool, str]:
        """将仓库物品移到背包"""
        for item in self.player.stash_items[:]:
            if item.id == item_id:
                if not self.player.equipment.backpack.can_fit(item):
                    free = self.player.equipment.backpack.get_free_slots()
                    return False, f"背包容量不足！需要 {item.grid} 格，剩余 {free} 格"
                self.player.stash_items.remove(item)
                self.player.equipment.backpack.add_item(item)
                return True, f"{item.name} 已放入背包"
        return False, "找不到该物品"

    def clear_backpack(self) -> str:
        """清空背包所有物品到仓库"""
        items = self.player.equipment.backpack.get_all_items()
        if not items:
            return "背包是空的"
        count = len(items)
        for item in items:
            self.player.equipment.backpack.remove_item(item.id)
            self.player.stash_items.append(item)
        return f"已将{count}件物品移至仓库"

    def sell_stash_weapon(self, weapon_id: str) -> Tuple[bool, str]:
        """出售仓库武器"""
        for weapon in self.player.stash_weapons:
            if weapon.id == weapon_id:
                price = weapon.value // 2
                self.player.stats.money += price
                self.player.stash_weapons.remove(weapon)
                return True, f"出售了 {weapon.name}，获得 {price} 金币"
        return False, "找不到该武器"

    def sell_stash_armor(self, armor_id: str) -> Tuple[bool, str]:
        """出售仓库护甲"""
        for armor in self.player.stash_armors:
            if armor.id == armor_id:
                price = armor.value // 2
                self.player.stats.money += price
                self.player.stash_armors.remove(armor)
                return True, f"出售了 {armor.name}，获得 {price} 金币"
        return False, "找不到该护甲"

    def auto_equip_best(self) -> str:
        """自动装备最好的武器和护甲"""
        msgs = []
        # 装备最好的武器
        if self.player.stash_weapons and (not self.player.equipment.primary_weapon or
            self.player.equipment.primary_weapon.value < max(w.value for w in self.player.stash_weapons)):
            best_weapon = max(self.player.stash_weapons, key=lambda w: w.value)
            success, msg = self.equip_weapon(best_weapon.id)
            if success:
                msgs.append(msg)

        # 装备最好的护甲
        if self.player.stash_armors and (not self.player.equipment.armor or
            self.player.equipment.armor.value < max(a.value for a in self.player.stash_armors)):
            best_armor = max(self.player.stash_armors, key=lambda a: a.value)
            success, msg = self.equip_armor(best_armor.id)
            if success:
                msgs.append(msg)

        return "\n".join(msgs) if msgs else "无需更换装备"

    def return_to_base(self):
        """返回基地"""
        self.state = GameState.BASE
        self.current_raid = None
        self.current_enemy = None

        # 不要创建新对象
        self.player.action_points = self.player.max_action_points
        # 重置状态而不是创建新对象
        self.player.stats.reset_for_base()
        # 同步小队成员
        if self.squad and self.squad.members:
            for member in self.squad.members:
                member.stats.reset_for_base()

# ============== 存档系统 ==============
def serialize_weapon(weapon: Weapon) -> dict:
    """序列化武器"""
    return {
        'id': weapon.id, 'name': weapon.name, 'weight': weapon.weight,
        'value': weapon.value, 'rarity': weapon.rarity.name,
        'damage': weapon.damage, 'accuracy': weapon.accuracy,
        'fire_rate': weapon.fire_rate, 'penetration': weapon.penetration,
        'ammo_type': weapon.ammo_type, 'mag_size': weapon.mag_size,
        'current_ammo': weapon.current_ammo,
        'attachments': weapon.attachments
    }

def deserialize_weapon(data: dict) -> Weapon:
    """反序列化武器"""
    return Weapon(
        id=data['id'], name=data['name'], weight=data['weight'],
        value=data['value'], rarity=Rarity[data['rarity']],
        damage=data['damage'], accuracy=data['accuracy'],
        fire_rate=data['fire_rate'], penetration=data['penetration'],
        ammo_type=data.get('ammo_type', ''), mag_size=data['mag_size'],
        current_ammo=data.get('current_ammo', data['mag_size']),
        attachments=data.get('attachments', {})
    )

def serialize_armor(armor: Armor) -> dict:
    """序列化护甲"""
    return {
        'id': armor.id, 'name': armor.name, 'weight': armor.weight,
        'value': armor.value, 'rarity': armor.rarity.name,
        'armor_class': armor.armor_class, 'durability': armor.durability,
        'max_durability': armor.max_durability
    }

def deserialize_armor(data: dict) -> Armor:
    """反序列化护甲"""
    return Armor(
        id=data['id'], name=data['name'], weight=data['weight'],
        value=data['value'], rarity=Rarity[data['rarity']],
        armor_class=data['armor_class'], durability=data['durability'],
        max_durability=data['max_durability']
    )

def serialize_item(item: Item) -> dict:
    """序列化物品"""
    data = {
        'id': item.id, 'name': item.name, 'weight': item.weight,
        'grid': item.grid, 'value': item.value, 'rarity': item.rarity.name,
        'type': type(item).__name__, 'description': item.description
    }
    if isinstance(item, Consumable):
        data['effect'] = item.effect
        data['use_time'] = item.use_time
    elif isinstance(item, LootItem):
        data['item_type'] = item.item_type
    return data

def deserialize_item(data: dict) -> Item:
    """反序列化物品"""
    rarity = Rarity[data['rarity']]
    item_type = data.get('type', 'Item')
    if item_type == 'Consumable':
        return Consumable(
            id=data['id'], name=data['name'], weight=data.get('weight', 0.1),
            grid=data.get('grid', 1),
            value=data['value'], rarity=rarity,
            effect=data.get('effect', {}), use_time=data.get('use_time', 2)
        )
    elif item_type == 'LootItem':
        return LootItem(
            id=data['id'], name=data['name'], weight=data.get('weight', 0.1),
            grid=data.get('grid', 1),
            value=data['value'], rarity=rarity,
            item_type=data.get('item_type', '物资'),
            description=data.get('description', '')
        )
    elif item_type == 'Armor':
        return deserialize_armor(data)
    return Item(
        id=data['id'], name=data['name'], weight=data['weight'],
        value=data['value'], rarity=rarity
    )

def save_game(game: 'Game') -> dict:
    """将游戏状态序列化为字典"""
    p = game.player
    save_data = {
        'version': '0.3.0',
        'state': game.state.value,
        'player': {
            'name': p.name,
            'money': p.stats.money,
            'xp': p.stats.xp,
            'level': p.stats.level,
            'kills': p.kills,
            'total_loot_value': p.total_loot_value,
        },
        'equipment': {
            'primary_weapon': serialize_weapon(p.equipment.primary_weapon) if p.equipment.primary_weapon else None,
            'armor': serialize_armor(p.equipment.armor) if p.equipment.armor else None,
            'helmet': serialize_armor(p.equipment.helmet) if p.equipment.helmet else None,
            'backpack_rows': p.equipment.backpack.rows,
            'backpack_cols': p.equipment.backpack.cols,
        },
        'backpack_items': [serialize_item(i) for i in p.equipment.backpack.get_all_items()],
        'secure_items': [serialize_item(i) for i in p.equipment.secure_container.get_all_items()],
        'stash_weapons': [serialize_weapon(w) for w in p.stash_weapons],
        'stash_armors': [serialize_armor(a) for a in p.stash_armors],
        'stash_items': [serialize_item(i) for i in p.stash_items],
    }
    return save_data

def load_game(save_data: dict) -> 'Game':
    """从字典恢复游戏状态"""
    game = Game()
    game.state = GameState.BASE  # 读档总是回到基地

    p = game.player
    pd = save_data['player']
    p.name = pd.get('name', '玩家')
    p.stats.money = pd['money']
    p.stats.xp = pd['xp']
    p.stats.level = pd['level']
    p.kills = pd.get('kills', 0)
    p.total_loot_value = pd.get('total_loot_value', 0)

    # 装备
    eq = save_data['equipment']
    if eq.get('primary_weapon'):
        weapon = deserialize_weapon(eq['primary_weapon'])
        p.equipment.equip_weapon(weapon, 'primary')
    else:
        p.equipment.primary_weapon = None

    if eq.get('armor'):
        armor = deserialize_armor(eq['armor'])
        p.equipment.equip_armor(armor, p.stats)
    else:
        p.equipment.armor = None

    if eq.get('helmet'):
        helmet = deserialize_armor(eq['helmet'])
        p.equipment.equip_helmet(helmet, p.stats)
    else:
        p.equipment.helmet = None

    # 背包
    p.equipment.backpack = Backpack(
        rows=eq.get('backpack_rows', 5),
        cols=eq.get('backpack_cols', 4)
    )
    for item_data in save_data.get('backpack_items', []):
        item = deserialize_item(item_data)
        p.equipment.backpack.add_item(item)

    # 保险箱
    for item_data in save_data.get('secure_items', []):
        item = deserialize_item(item_data)
        p.equipment.secure_container.add_item(item)

    # 仓库
    p.stash_weapons = [deserialize_weapon(w) for w in save_data.get('stash_weapons', [])]
    p.stash_armors = [deserialize_armor(a) for a in save_data.get('stash_armors', [])]
    p.stash_items = [deserialize_item(i) for i in save_data.get('stash_items', [])]

    return game

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

        print(f"生命值: {stats.hp}/{stats.max_hp}")
        print("护甲:")
        for zone in DamageZone:
            armor = stats.get_armor(zone)
            if armor.armor_value > 0:
                print(f"  {zone.cn_name}: 🛡️{armor.armor_value} (耐久: {armor.durability}/{armor.max_durability})")
            else:
                print(f"  {zone.cn_name}: 无护甲")
        if stats.debuffs:
            print("异常状态:")
            for d in stats.debuffs:
                dmg = f" -{d.damage}/回合" if d.damage > 0 else ""
                print(f"  {d.cn_name}{dmg} ({d.remaining}回合)")

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
                    self.game.start_raid(MAP_DAM)
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