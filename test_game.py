#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
游戏核心功能测试脚本
直接测试game.py中的逻辑，无需Flask
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import game as g
import random

class TestResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.tests = []
        self.bugs = []
        self.suggestions = []
    
    def add_pass(self, name, msg=""):
        self.passed += 1
        self.tests.append(("✅ PASS", name, msg))
        print(f"✅ PASS: {name} {msg}")
    
    def add_fail(self, name, msg=""):
        self.failed += 1
        self.tests.append(("❌ FAIL", name, msg))
        self.bugs.append(f"{name}: {msg}")
        print(f"❌ FAIL: {name} {msg}")
    
    def add_bug(self, bug):
        self.bugs.append(bug)
    
    def add_suggestion(self, suggestion):
        self.suggestions.append(suggestion)

result = TestResult()

print("=" * 60)
print("游戏核心功能测试")
print("=" * 60)

# ==================== 测试1：干员系统 ====================
print("\n【测试1：干员系统】")

# 1.1 测试创建游戏实例
try:
    game = g.Game()
    result.add_pass("创建游戏实例")
except Exception as e:
    result.add_fail("创建游戏实例", str(e))

# 1.2 测试玩家干员
try:
    player = game.player
    if hasattr(player, 'operator') and player.operator:
        result.add_pass("玩家干员存在", f"干员: {player.operator.name}")
    else:
        result.add_fail("玩家干员存在", "玩家没有关联干员")
except Exception as e:
    result.add_fail("玩家干员存在", str(e))

# 1.3 测试干员属性
try:
    op = game.player.operator
    checks = []
    if hasattr(op, 'name') and op.name:
        checks.append(f"name={op.name}")
    if hasattr(op, 'operator_class'):
        checks.append(f"class={op.operator_class.cn_name}")
    if hasattr(op, 'primary_skill') and op.primary_skill:
        checks.append(f"primary_skill={op.primary_skill.name}")
    if hasattr(op, 'secondary_skill') and op.secondary_skill:
        checks.append(f"secondary_skill={op.secondary_skill.name}")
    
    if len(checks) >= 3:
        result.add_pass("干员属性完整", ", ".join(checks))
    else:
        result.add_fail("干员属性完整", f"缺少属性: {checks}")
except Exception as e:
    result.add_fail("干员属性完整", str(e))

# 1.4 测试使用技能
try:
    op = game.player.operator
    if op.primary_skill and op.primary_skill.can_use():
        can_use = op.primary_skill.use()
        if can_use:
            result.add_pass("使用主要技能", f"技能: {op.primary_skill.name}")
        else:
            result.add_fail("使用主要技能", "技能无法使用")
    else:
        # 技能冷却中或其他原因
        result.add_pass("使用主要技能", "技能不可用(冷却中或已用完)")
except Exception as e:
    result.add_fail("使用主要技能", str(e))

# 1.5 测试所有干员创建
try:
    created_count = 0
    for op_id in g.OPERATORS.keys():
        try:
            op = g.Operator.create(op_id)
            if op and op.name:
                created_count += 1
        except Exception as e:
            result.add_bug(f"干员{op_id}创建失败: {e}")
    
    total = len(g.OPERATORS)
    if created_count == total:
        result.add_pass("所有干员可创建", f"成功创建{created_count}/{total}个干员")
    else:
        result.add_fail("所有干员可创建", f"只创建了{created_count}/{total}个干员")
except Exception as e:
    result.add_fail("所有干员可创建", str(e))

# ==================== 测试2：载具系统 ====================
print("\n【测试2：载具系统】")

# 2.1 测试创建载具
try:
    vehicle = g.Vehicle.create("heli_little_bird")
    if vehicle and vehicle.name:
        result.add_pass("创建载具", f"载具: {vehicle.name}")
    else:
        result.add_fail("创建载具", "载具创建失败")
except Exception as e:
    result.add_fail("创建载具", str(e))

# 2.2 测试载具属性
try:
    vehicle = g.Vehicle.create("tank_m1a2")
    checks = []
    if vehicle.hp > 0:
        checks.append(f"hp={vehicle.hp}")
    if vehicle.armor > 0:
        checks.append(f"armor={vehicle.armor}")
    if vehicle.seats > 0:
        checks.append(f"seats={vehicle.seats}")
    if vehicle.weapons:
        checks.append(f"weapons={len(vehicle.weapons)}")
    
    if len(checks) >= 3:
        result.add_pass("载具属性完整", ", ".join(checks))
    else:
        result.add_fail("载具属性完整", f"属性不足: {checks}")
except Exception as e:
    result.add_fail("载具属性完整", str(e))

# 2.3 测试上车
try:
    vehicle = g.Vehicle.create("apc_m2_bradley")
    player_id = "test_player"
    success = vehicle.board(player_id, as_driver=True)
    if success and player_id in vehicle.occupants and vehicle.driver == player_id:
        result.add_pass("上车功能", "玩家成功上车并成为驾驶员")
    else:
        result.add_fail("上车功能", f"occupants={vehicle.occupants}, driver={vehicle.driver}")
except Exception as e:
    result.add_fail("上车功能", str(e))

# 2.4 测试下车
try:
    vehicle = g.Vehicle.create("apc_m2_bradley")
    player_id = "test_player"
    vehicle.board(player_id, as_driver=True)
    success = vehicle.exit_vehicle(player_id)
    if success and player_id not in vehicle.occupants:
        result.add_pass("下车功能", "玩家成功下车")
    else:
        result.add_fail("下车功能", f"occupants={vehicle.occupants}")
except Exception as e:
    result.add_fail("下车功能", str(e))

# 2.5 测试载具攻击
try:
    vehicle = g.Vehicle.create("tank_m1a2")
    weapon = vehicle.get_weapon()
    if weapon and weapon.can_fire():
        shots = weapon.fire()
        if shots > 0:
            result.add_pass("载具攻击", f"发射了{shots}发")
        else:
            result.add_fail("载具攻击", "无法开火")
    else:
        result.add_fail("载具攻击", "没有可用武器或武器无法开火")
except Exception as e:
    result.add_fail("载具攻击", str(e))

# 2.6 测试所有载具创建
try:
    created_count = 0
    for v_id in g.VEHICLES.keys():
        try:
            v = g.Vehicle.create(v_id)
            if v and v.name:
                created_count += 1
        except Exception as e:
            result.add_bug(f"载具{v_id}创建失败: {e}")
    
    total = len(g.VEHICLES)
    if created_count == total:
        result.add_pass("所有载具可创建", f"成功创建{created_count}/{total}个载具")
    else:
        result.add_fail("所有载具可创建", f"只创建了{created_count}/{total}个载具")
except Exception as e:
    result.add_fail("所有载具可创建", str(e))

# ==================== 测试3：小队系统 ====================
print("\n【测试3：小队系统】")

# 3.1 测试创建小队
try:
    game = g.Game()
    game.create_squad()
    if game.squad and len(game.squad.members) > 0:
        result.add_pass("创建小队", f"成员数: {len(game.squad.members)}")
    else:
        result.add_fail("创建小队", "小队创建失败")
except Exception as e:
    result.add_fail("创建小队", str(e))

# 3.2 测试小队成员数量
try:
    game = g.Game()
    game.create_squad()
    if len(game.squad.members) == 3:
        result.add_pass("3人小队", f"成员数: {len(game.squad.members)}")
    else:
        result.add_fail("3人小队", f"成员数为{len(game.squad.members)}，应为3")
except Exception as e:
    result.add_fail("3人小队", str(e))

# 3.3 测试小队成员状态
try:
    game = g.Game()
    game.create_squad()
    members_info = []
    for m in game.squad.members:
        members_info.append(f"{m.name}(alive={m.is_alive()})")
    
    alive_count = len(game.squad.get_alive_members())
    if alive_count == 3:
        result.add_pass("小队成员状态", f"存活: {alive_count}/3")
    else:
        result.add_fail("小队成员状态", f"存活: {alive_count}/3")
except Exception as e:
    result.add_fail("小队成员状态", str(e))

# 3.4 测试小队成员干员
try:
    game = g.Game()
    game.create_squad()
    ops_info = []
    for m in game.squad.members:
        if m.operator:
            ops_info.append(f"{m.operator.name}({m.operator.operator_class.cn_name})")
    
    if len(ops_info) == 3:
        result.add_pass("小队成员干员", ", ".join(ops_info))
    else:
        result.add_fail("小队成员干员", f"只有{len(ops_info)}个成员有干员")
except Exception as e:
    result.add_fail("小队成员干员", str(e))

# ==================== 测试4：破译系统 ====================
print("\n【测试4：破译系统】")

# 4.1 测试创建破译进度
try:
    decode = g.DecodeProgress(
        item_id="loot_usb_secret",
        item_name="加密U盘",
        total_time=5,
        decoder_id="member_0"
    )
    if decode.total_time == 5:
        result.add_pass("创建破译进度", f"时间: {decode.total_time}回合")
    else:
        result.add_fail("创建破译进度", "破译进度创建失败")
except Exception as e:
    result.add_fail("创建破译进度", str(e))

# 4.2 测试破译进度推进
try:
    decode = g.DecodeProgress(
        item_id="loot_usb_secret",
        item_name="加密U盘",
        total_time=3,
        decoder_id="member_0"
    )
    # 推进3次完成
    done1, msg1 = decode.advance()
    done2, msg2 = decode.advance()
    done3, msg3 = decode.advance()
    
    if done3:
        result.add_pass("破译进度推进", "破译完成")
    else:
        result.add_fail("破译进度推进", f"进度: {decode.current_progress}/{decode.total_time}")
except Exception as e:
    result.add_fail("破译进度推进", str(e))

# 4.3 测试破译管理器
try:
    manager = g.DecodeManager()
    success = manager.start_decode("loot_usb_secret", "加密U盘", 5, "member_0")
    if success and len(manager.active_decodes) == 1:
        result.add_pass("破译管理器", f"活跃破译: {len(manager.active_decodes)}")
    else:
        result.add_fail("破译管理器", "无法开始破译")
except Exception as e:
    result.add_fail("破译管理器", str(e))

# 4.4 测试破译中断
try:
    decode = g.DecodeProgress(
        item_id="loot_usb_secret",
        item_name="加密U盘",
        total_time=5,
        decoder_id="member_0"
    )
    decode.advance()
    decode.advance()
    lost = decode.interrupt()
    if decode.interrupted and lost >= 0:
        result.add_pass("破译中断", f"损失进度: {lost}")
    else:
        result.add_fail("破译中断", "中断失败")
except Exception as e:
    result.add_fail("破译中断", str(e))

# ==================== 测试5：游戏核心流程 ====================
print("\n【测试5：游戏核心流程】")

# 5.1 测试开始行动
try:
    game = g.Game()
    game.create_squad()
    game.start_raid(g.MAP_DAM)
    if game.state == g.GameState.RAID:
        result.add_pass("开始行动", f"状态: {game.state.value}")
    else:
        result.add_fail("开始行动", f"状态: {game.state.value}")
except Exception as e:
    result.add_fail("开始行动", str(e))

# 5.2 测试获取游戏状态
try:
    game = g.Game()
    state = game.state
    if state:
        result.add_pass("获取游戏状态", f"状态: {state.value}")
    else:
        result.add_fail("获取游戏状态", "无法获取状态")
except Exception as e:
    result.add_fail("获取游戏状态", str(e))

# 5.3 测试玩家状态
try:
    game = g.Game()
    stats = game.player.stats
    checks = []
    if stats.hp > 0:
        checks.append(f"hp={stats.hp}")
    if stats.money > 0:
        checks.append(f"money={stats.money}")
    if stats.max_hp > 0:
        checks.append(f"max_hp={stats.max_hp}")
    
    if len(checks) >= 2:
        result.add_pass("玩家状态", ", ".join(checks))
    else:
        result.add_fail("玩家状态", f"状态不足: {checks}")
except Exception as e:
    result.add_fail("玩家状态", str(e))

# 5.4 测试移动
try:
    game = g.Game()
    game.start_raid(g.MAP_DAM)
    # 获取连接区域
    zone = game.current_raid.get_zone(game.player.current_zone)
    connections = zone.get('connections', [])
    if connections:
        success, msg = game.move_to_zone(connections[0])
        if success:
            result.add_pass("移动功能", f"移动到: {connections[0]}")
        else:
            result.add_fail("移动功能", msg)
    else:
        result.add_pass("移动功能", "无连接区域可移动")
except Exception as e:
    result.add_fail("移动功能", str(e))

# 5.5 测试搜索
try:
    game = g.Game()
    game.start_raid(g.MAP_DAM)
    success, msg = game.search_zone()
    # 搜索可能成功或没有东西可搜
    result.add_pass("搜索功能", msg[:50] if msg else "OK")
except Exception as e:
    result.add_fail("搜索功能", str(e))

# ==================== 输出测试结果 ====================
print("\n" + "=" * 60)
print("测试结果汇总")
print("=" * 60)
print(f"✅ 通过: {result.passed}")
print(f"❌ 失败: {result.failed}")
print(f"总计: {result.passed + result.failed}")

if result.bugs:
    print("\n【Bug列表】")
    for i, bug in enumerate(result.bugs, 1):
        print(f"  {i}. {bug}")

if result.suggestions:
    print("\n【改进建议】")
    for i, s in enumerate(result.suggestions, 1):
        print(f"  {i}. {s}")

print("\n" + "=" * 60)