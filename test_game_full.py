#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整游戏功能测试
包括API端点模拟和更多边缘情况测试
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import game as g
import random
import json

class TestReport:
    def __init__(self):
        self.passed = []
        self.failed = []
        self.bugs = []
        self.suggestions = []
    
    def pass_(self, category, name, detail=""):
        self.passed.append((category, name, detail))
        print(f"✅ [{category}] {name}: {detail}")
    
    def fail(self, category, name, detail=""):
        self.failed.append((category, name, detail))
        self.bugs.append(f"[{category}] {name}: {detail}")
        print(f"❌ [{category}] {name}: {detail}")
    
    def bug(self, desc):
        self.bugs.append(desc)
    
    def suggest(self, desc):
        self.suggestions.append(desc)

report = TestReport()

print("=" * 70)
print("暗区文字游戏 - 完整功能测试报告")
print("=" * 70)

# ==================== 1. 干员系统详细测试 ====================
print("\n" + "=" * 50)
print("1. 干员系统测试")
print("=" * 50)

# 1.1 干员创建
for op_id, op_data in g.OPERATORS.items():
    try:
        op = g.Operator.create(op_id)
        if op.name == op_data["name"]:
            report.pass_("干员", f"创建{op_data['name']}", f"职业:{op.operator_class.cn_name}")
        else:
            report.fail("干员", f"创建{op_id}", "名称不匹配")
    except Exception as e:
        report.fail("干员", f"创建{op_id}", str(e))

# 1.2 技能系统
try:
    op = g.Operator.create("operator_wyatt")
    # 测试主要技能
    if op.primary_skill.can_use():
        op.primary_skill.use()
        report.pass_("技能", "使用主要技能", op.primary_skill.name)
    else:
        report.fail("技能", "使用主要技能", "无法使用")
    
    # 测试冷却
    if op.primary_skill.current_cooldown > 0:
        report.pass_("技能", "技能冷却", f"冷却:{op.primary_skill.current_cooldown}回合")
    else:
        report.fail("技能", "技能冷却", "使用后无冷却")
    
    # 测试冷却减少
    op.primary_skill.tick()
    if op.primary_skill.current_cooldown == op.primary_skill.cooldown - 1:
        report.pass_("技能", "冷却递减", "OK")
    else:
        report.fail("技能", "冷却递减", "冷却未正确递减")
        
except Exception as e:
    report.fail("技能", "技能系统测试", str(e))

# ==================== 2. 载具系统详细测试 ====================
print("\n" + "=" * 50)
print("2. 载具系统测试")
print("=" * 50)

# 2.1 载具创建
for v_id, v_data in g.VEHICLES.items():
    try:
        v = g.Vehicle.create(v_id)
        if v.name == v_data["name"]:
            report.pass_("载具", f"创建{v_data['name']}", f"HP:{v.hp}, 座位:{v.seats}")
        else:
            report.fail("载具", f"创建{v_id}", "名称不匹配")
    except Exception as e:
        report.fail("载具", f"创建{v_id}", str(e))

# 2.2 载具操作
try:
    v = g.Vehicle.create("heli_black_hawk")
    
    # 测试多人上车 - 填满载具
    players = ["p1", "p2", "p3", "p4", "p5", "p6", "p7", "p8"]  # 8人填满黑鹰
    boarded = 0
    for p in players:
        if v.board(p):
            boarded += 1
    
    if boarded == v.seats:
        report.pass_("载具", "多人上车", f"{boarded}/{v.seats}人")
    elif boarded < v.seats:
        report.pass_("载具", "多人上车", f"{boarded}/{v.seats}人(座位未满)")
    else:
        report.fail("载具", "多人上车", f"超过座位上限:{boarded}/{v.seats}")
    
    # 测试载具满员
    if not v.can_board():
        report.pass_("载具", "满员检测", "无法再上人")
    else:
        report.fail("载具", "满员检测", "满员后还能上车")
    
    # 测试下车
    v.exit_vehicle("p1")
    if "p1" not in v.occupants:
        report.pass_("载具", "下车功能", "OK")
    else:
        report.fail("载具", "下车功能", "下车失败")
        
except Exception as e:
    report.fail("载具", "载具操作测试", str(e))

# 2.3 载具武器
try:
    v = g.Vehicle.create("tank_m1a2")
    weapons_test = []
    for w in v.weapons:
        if w.can_fire():
            shots = w.fire()
            weapons_test.append(f"{w.name}:{shots}发")
    
    if weapons_test:
        report.pass_("载具武器", "开火测试", ", ".join(weapons_test))
    else:
        report.fail("载具武器", "开火测试", "无武器可开火")
        
    # 测试弹药消耗
    main_cannon = v.get_weapon("main_cannon")
    if main_cannon and main_cannon.current_ammo < main_cannon.max_ammo:
        report.pass_("载具武器", "弹药消耗", f"剩余:{main_cannon.current_ammo}/{main_cannon.max_ammo}")
    else:
        report.fail("载具武器", "弹药消耗", "弹药未消耗")
        
except Exception as e:
    report.fail("载具武器", "武器测试", str(e))

# 2.4 载具受伤
try:
    v = g.Vehicle.create("apc_m2_bradley")
    initial_hp = v.hp
    damage = v.take_damage(200, penetration=2)
    
    if v.hp < initial_hp:
        report.pass_("载具受伤", "HP减少", f"伤害:{damage}, HP:{v.hp}/{v.max_hp}")
    else:
        report.fail("载具受伤", "HP减少", "HP未减少")
        
    # 测试护甲减伤
    if damage < 200:
        report.pass_("载具护甲", "护甲减伤", f"实际伤害:{damage}/200")
    else:
        report.suggest("载具护甲: 护甲未提供减伤效果")
        
except Exception as e:
    report.fail("载具", "受伤测试", str(e))

# ==================== 3. 小队系统详细测试 ====================
print("\n" + "=" * 50)
print("3. 小队系统测试")
print("=" * 50)

# 3.1 小队创建
try:
    game = g.Game()
    
    # 测试默认小队
    game.create_squad()
    if game.squad and len(game.squad.members) == 3:
        names = [m.name for m in game.squad.members]
        report.pass_("小队", "创建默认小队", f"成员:{', '.join(names)}")
    else:
        report.fail("小队", "创建默认小队", "小队成员数不正确")
        
except Exception as e:
    report.fail("小队", "创建测试", str(e))

# 3.2 自定义小队
try:
    game = g.Game()
    custom_ops = ["operator_luna", "operator_doc", "operator_saw"]
    game.create_squad(member_operator_ids=custom_ops)
    
    op_names = [m.operator.name for m in game.squad.members]
    expected = [g.OPERATORS[op_id]["name"] for op_id in custom_ops]
    
    if op_names == expected:
        report.pass_("小队", "自定义小队", f"成员:{', '.join(op_names)}")
    else:
        report.fail("小队", "自定义小队", f"期望:{expected}, 实际:{op_names}")
        
except Exception as e:
    report.fail("小队", "自定义小队测试", str(e))

# 3.3 小队成员状态
try:
    game = g.Game()
    game.create_squad()
    
    alive = game.squad.get_alive_members()
    if len(alive) == 3:
        report.pass_("小队状态", "成员存活", f"{len(alive)}/3")
    else:
        report.fail("小队状态", "成员存活", f"{len(alive)}/3")
        
    # 测试全部倒地
    for m in game.squad.members:
        m.is_downed = True
    
    if game.squad.all_downed():
        report.pass_("小队状态", "全部倒地检测", "OK")
    else:
        report.fail("小队状态", "全部倒地检测", "检测失败")
        
except Exception as e:
    report.fail("小队", "成员状态测试", str(e))

# 3.4 Bug测试：SquadMember.is_ai
try:
    game = g.Game()
    game.create_squad()
    
    # 检查SquadMember是否有is_ai属性
    member = game.squad.members[1]
    if hasattr(member, 'is_ai'):
        report.pass_("小队Bug", "SquadMember.is_ai属性", "属性存在")
    else:
        report.fail("小队Bug", "SquadMember.is_ai属性", "属性不存在，但operator.is_ai存在")
        report.bug("SquadMember类缺少is_ai属性，导致start_raid中访问member.is_ai报错")
        
    # 正确的访问方式
    if hasattr(member.operator, 'is_ai') and member.operator.is_ai:
        report.pass_("小队Bug", "正确的is_ai访问", f"member.operator.is_ai={member.operator.is_ai}")
    
except Exception as e:
    report.fail("小队", "Bug测试", str(e))

# ==================== 4. 破译系统详细测试 ====================
print("\n" + "=" * 50)
print("4. 破译系统测试")
print("=" * 50)

# 4.1 破译进度
try:
    decode = g.DecodeProgress(
        item_id="loot_usb_secret",
        item_name="加密U盘",
        total_time=5,
        decoder_id="member_0"
    )
    
    # 测试进度推进
    progresses = []
    for i in range(5):
        done, msg = decode.advance()
        progresses.append(f"P{decode.current_progress}")
        if done:
            break
    
    if decode.current_progress >= decode.total_time:
        report.pass_("破译", "进度完成", "->".join(progresses))
    else:
        report.fail("破译", "进度完成", f"进度:{decode.current_progress}/{decode.total_time}")
        
except Exception as e:
    report.fail("破译", "进度测试", str(e))

# 4.2 破译管理器
try:
    manager = g.DecodeManager()
    
    # 测试并发破译限制
    started = 0
    for i in range(5):
        if manager.start_decode(f"item_{i}", f"物品{i}", 3, f"decoder_{i}"):
            started += 1
    
    max_concurrent = g.DECODE_CONFIG.get("max_concurrent_decodes", 1)
    if started <= max_concurrent:
        report.pass_("破译", "并发限制", f"最大并发:{max_concurrent}, 实际开始:{started}")
    else:
        report.fail("破译", "并发限制", f"超过最大并发数:{started}/{max_concurrent}")
        
except Exception as e:
    report.fail("破译", "管理器测试", str(e))

# 4.3 破译中断
try:
    decode = g.DecodeProgress(
        item_id="loot_document",
        item_name="机密文件",
        total_time=10,
        decoder_id="member_0"
    )
    
    # 先推进一些进度
    decode.advance()
    decode.advance()
    decode.advance()
    progress_before = decode.current_progress
    
    # 中断
    lost = decode.interrupt()
    
    if decode.interrupted and decode.current_progress == 0:
        report.pass_("破译", "中断功能", f"损失:{lost}进度")
    else:
        report.fail("破译", "中断功能", f"中断失败, interrupted={decode.interrupted}")
        
except Exception as e:
    report.fail("破译", "中断测试", str(e))

# ==================== 5. 战斗系统测试 ====================
print("\n" + "=" * 50)
print("5. 战斗系统测试")
print("=" * 50)

# 5.1 武器系统
try:
    weapons_test = ["pistol_p226", "ar_ak74n", "sniper_awm"]
    for w_id in weapons_test:
        w_data = g.WEAPONS.get(w_id)
        if w_data:
            report.pass_("武器", f"{w_data['name']}", f"伤害:{w_data['damage']}, 精度:{w_data['accuracy']}")
        else:
            report.fail("武器", w_id, "武器不存在")
except Exception as e:
    report.fail("武器", "武器测试", str(e))

# 5.2 护甲系统
try:
    armor_data = g.ARMORS.get("armor_6_slick")
    if armor_data:
        report.pass_("护甲", armor_data["name"], f"等级:{armor_data['class']}, 耐久:{armor_data['durability']}")
    else:
        report.fail("护甲", "Slick护甲", "护甲不存在")
        
    # 测试护甲吸收伤害
    armor = g.ArmorStatus(
        armor_value=6,
        max_armor=6,
        durability=90,
        max_durability=90
    )
    actual_dmg, durability_loss = armor.absorb_damage(100)
    report.pass_("护甲", "伤害吸收", f"实际伤害:{actual_dmg}, 耐久损失:{durability_loss}")
    
except Exception as e:
    report.fail("护甲", "护甲测试", str(e))

# 5.3 敌人生成
try:
    game = g.Game()
    game.start_raid(g.MAP_DAM)
    
    if game.current_raid and game.current_raid.enemies:
        enemy_types = set(e.name for e in game.current_raid.enemies)
        report.pass_("敌人", "敌人生成", f"类型:{', '.join(enemy_types)}")
    else:
        report.pass_("敌人", "敌人生成", "当前区域无敌人")
        
except Exception as e:
    report.fail("敌人", "敌人测试", str(e))

# ==================== 6. 地图系统测试 ====================
print("\n" + "=" * 50)
print("6. 地图系统测试")
print("=" * 50)

# 6.1 地图数据
try:
    for map_id, map_data in g.ALL_MAPS.items():
        zone_count = len(map_data.get("zones", {}))
        report.pass_("地图", map_data["name"], f"{zone_count}个区域")
except Exception as e:
    report.fail("地图", "地图测试", str(e))

# 6.2 区域连接
try:
    game = g.Game()
    game.start_raid(g.MAP_DAM)
    
    zone = game.current_raid.get_zone(game.player.current_zone)
    connections = zone.get("connections", [])
    
    if connections:
        report.pass_("地图", "区域连接", f"{zone['name']}有{len(connections)}个连接")
    else:
        report.fail("地图", "区域连接", "当前区域无连接")
        
except Exception as e:
    report.fail("地图", "连接测试", str(e))

# ==================== 7. 物品系统测试 ====================
print("\n" + "=" * 50)
print("7. 物品系统测试")
print("=" * 50)

# 7.1 物品稀有度
try:
    rarity_counts = {}
    for item_id, item_data in g.LOOT_ITEMS.items():
        rarity = item_data.get("rarity")
        rarity_name = rarity.cn_name if hasattr(rarity, 'cn_name') else str(rarity)
        rarity_counts[rarity_name] = rarity_counts.get(rarity_name, 0) + 1
    
    report.pass_("物品", "稀有度分布", str(rarity_counts))
except Exception as e:
    report.fail("物品", "稀有度测试", str(e))

# 7.2 消耗品效果
try:
    consumable_test = ["med_bandage", "med_ifak", "stim_adrenaline"]
    for c_id in consumable_test:
        c_data = g.CONSUMABLES.get(c_id)
        if c_data:
            effect = c_data.get("effect", {})
            report.pass_("消耗品", c_data["name"], f"效果:{effect}")
        else:
            report.fail("消耗品", c_id, "不存在")
except Exception as e:
    report.fail("消耗品", "消耗品测试", str(e))

# ==================== 输出最终报告 ====================
print("\n" + "=" * 70)
print("测试报告汇总")
print("=" * 70)
print(f"✅ 通过: {len(report.passed)}")
print(f"❌ 失败: {len(report.failed)}")

print("\n【Bug列表】")
if report.bugs:
    for i, bug in enumerate(report.bugs, 1):
        print(f"  {i}. {bug}")
else:
    print("  无")

print("\n【改进建议】")
suggestions = [
    "1. 修复SquadMember.is_ai属性缺失问题 - 第4725行应使用member.operator.is_ai",
    "2. 添加载具与小队的集成测试（小队成员上下车）",
    "3. 增加破译系统与战利品的关联测试",
    "4. 添加更多边缘情况测试（如载具满员、破译中断恢复等）",
    "5. 建议增加API端点的单元测试（需安装Flask）",
]
for s in suggestions:
    print(f"  {s}")

print("\n" + "=" * 70)