#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
暗区文字 - Web版本
Flask Web服务器
"""

from flask import Flask, render_template, request, jsonify, session
import game as g
import uuid
import os
import json
import random
import auth

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dark-zone-secret-key-2024')
# 配置 session
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 24小时

# 存储游戏实例
games = {}
SAVE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'saves')

def get_game():
    """获取或创建游戏实例"""
    # 已登录用户使用 user_{username} 作为 game_id
    if 'username' in session:
        game_id = f"user_{session['username']}"
    else:
        # 游客模式
        if 'game_id' not in session:
            session['game_id'] = str(uuid.uuid4())
        game_id = session['game_id']

    if game_id not in games:
        games[game_id] = g.Game()

    return games[game_id]


def get_save_path(username=None):
    """获取存档路径"""
    if username:
        return os.path.join(SAVE_DIR, username, 'save.json')
    else:
        game_id = session.get('game_id', 'default')
        return os.path.join(SAVE_DIR, f'{game_id}.json')


# ============ 认证路由 ============

@app.route('/api/auth/register', methods=['POST'])
def api_register():
    """用户注册"""
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '')

    success, message = auth.register_user(username, password)

    if success:
        # 注册成功后自动登录
        session['username'] = username
        return jsonify({'success': True, 'message': '注册成功', 'username': username})
    else:
        return jsonify({'success': False, 'message': message})


@app.route('/api/auth/login', methods=['POST'])
def api_login():
    """用户登录"""
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '')

    success, result = auth.login_user(username, password)

    if success:
        session['username'] = result
        # 清除旧的游客 game_id
        session.pop('game_id', None)
        # 尝试加载已登录用户的存档
        save_path = get_save_path(result)
        if os.path.exists(save_path):
            try:
                with open(save_path, 'r', encoding='utf-8') as f:
                    save_data = json.load(f)
                game_id = f"user_{result}"
                games[game_id] = g.load_game(save_data)
            except Exception:
                pass
        return jsonify({'success': True, 'message': '登录成功', 'username': result})
    else:
        return jsonify({'success': False, 'message': result})


@app.route('/api/auth/logout', methods=['POST'])
def api_logout():
    """用户登出"""
    # 保存当前游戏状态
    if 'username' in session:
        game_id = f"user_{session['username']}"
        if game_id in games:
            os.makedirs(os.path.join(SAVE_DIR, session['username']), exist_ok=True)
            save_path = get_save_path(session['username'])
            save_data = g.save_game(games[game_id])
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
            # 清除内存中的游戏实例
            del games[game_id]

    session.clear()
    return jsonify({'success': True, 'message': '已登出'})


@app.route('/api/auth/status')
def api_auth_status():
    """获取登录状态"""
    if 'username' in session:
        username = session['username']
        save_path = get_save_path(username)
        has_save = os.path.exists(save_path)
        return jsonify({
            'logged_in': True,
            'username': username,
            'has_save': has_save
        })
    else:
        return jsonify({
            'logged_in': False,
            'username': None,
            'has_save': False
        })


# ============ 页面路由 ============

@app.route('/')
def index():
    """主页面"""
    return render_template('index.html')

@app.route('/api/state')
def get_state():
    """获取游戏状态"""
    game = get_game()

    state = {
        'game_state': game.state.value,
        'player': {
            'name': game.player.name,
            'level': game.player.stats.level,
            'xp': game.player.stats.xp,
            'xp_needed': game.player.stats.level * 1000,
            'money': game.player.stats.money,
            'total_hp': game.player.stats.get_total_hp(),
            'max_hp': game.player.stats.get_max_hp(),
            'action_points': game.player.action_points,
            'max_action_points': game.player.max_action_points,
            'kills': game.player.kills,
            'body_parts': {}
        },
        'equipment': {
            'weapon': game.player.equipment.primary_weapon.name if game.player.equipment.primary_weapon else None,
            'weapon_id': game.player.equipment.primary_weapon.id if game.player.equipment.primary_weapon else None,
            'weapon_ammo': game.player.equipment.primary_weapon.current_ammo if game.player.equipment.primary_weapon else 0,
            'weapon_mag': game.player.equipment.primary_weapon.mag_size if game.player.equipment.primary_weapon else 0,
            'weapon_ammo_type': game.player.equipment.primary_weapon.ammo_type if game.player.equipment.primary_weapon else None,
            'armor': game.player.equipment.armor.name if game.player.equipment.armor else None,
            'armor_id': game.player.equipment.armor.id if game.player.equipment.armor else None,
            'armor_durability': game.player.equipment.armor.durability if game.player.equipment.armor else 0,
            'armor_max_durability': game.player.equipment.armor.max_durability if game.player.equipment.armor else 0,
            'helmet': game.player.equipment.helmet.name if game.player.equipment.helmet else None,
            'helmet_id': game.player.equipment.helmet.id if game.player.equipment.helmet else None,
            'backpack_name': '标准背包',
            'backpack_capacity': game.player.equipment.backpack.rows * game.player.equipment.backpack.cols,
            'backpack_used_slots': game.player.equipment.backpack.get_used_slots(),
        },
        'stash_weapons': [],
        'stash_armors': [],
        'stash_helmets': [],
        'shop_weapons': [],
        'shop_armors': [],
        'backpack': [],
        'backpack_value': game.player.equipment.backpack.get_total_value(),
        'secure_container': [],
        'messages': game.messages[-10:] if game.messages else []
    }

    # 仓库武器
    for weapon in game.player.stash_weapons:
        state['stash_weapons'].append({
            'id': weapon.id,
            'name': weapon.name,
            'damage': weapon.damage,
            'accuracy': weapon.accuracy,
            'fire_rate': weapon.fire_rate,
            'penetration': weapon.penetration,
            'mag_size': weapon.mag_size,
            'value': weapon.value,
            'rarity': weapon.rarity.cn_name
        })

    # 仓库护甲
    for armor in game.player.stash_armors:
        state['stash_armors'].append({
            'id': armor.id,
            'name': armor.name,
            'armor_class': armor.armor_class,
            'durability': armor.durability,
            'max_durability': armor.max_durability,
            'value': armor.value,
            'rarity': armor.rarity.cn_name
        })

    # 仓库头盔
    for helmet in game.player.stash_helmets:
        state['stash_helmets'].append({
            'id': helmet.id,
            'name': helmet.name,
            'armor_class': helmet.armor_class,
            'durability': helmet.durability,
            'max_durability': helmet.max_durability,
            'value': helmet.value,
            'rarity': helmet.rarity.cn_name
        })

    # 商店武器
    for wid, wdata in g.WEAPONS.items():
        state['shop_weapons'].append({
            'id': wid,
            'name': wdata['name'],
            'type': wdata['type'],
            'damage': wdata['damage'],
            'accuracy': wdata['accuracy'],
            'fire_rate': wdata['fire_rate'],
            'penetration': wdata['penetration'],
            'mag_size': wdata['mag_size'],
            'ammo_type': wdata.get('ammo_type', ''),
            'value': wdata['value'],
            'rarity': wdata['rarity'].cn_name
        })

    # 商店护甲
    for aid, adata in g.ARMORS.items():
        state['shop_armors'].append({
            'id': aid,
            'name': adata['name'],
            'armor_class': adata['class'],
            'durability': adata['durability'],
            'max_durability': adata['max_durability'],
            'value': adata['value'],
            'rarity': adata['rarity'].cn_name
        })

    # 商店头盔
    state['shop_helmets'] = []
    for hid, hdata in g.HELMETS.items():
        if hid == "helmet_none":
            continue
        state['shop_helmets'].append({
            'id': hid,
            'name': hdata['name'],
            'armor_class': hdata['class'],
            'durability': hdata['durability'],
            'max_durability': hdata['max_durability'],
            'value': hdata['value'],
            'rarity': hdata['rarity'].cn_name
        })

    # 仓库头盔
    state['stash_helmets'] = []
    for helmet in game.player.stash_items:
        if isinstance(helmet, g.Armor) and hasattr(helmet, 'armor_class'):
            state['stash_helmets'].append({
                'id': helmet.id,
                'name': helmet.name,
                'armor_class': helmet.armor_class,
                'durability': helmet.durability,
                'max_durability': helmet.max_durability,
                'value': helmet.value,
                'rarity': helmet.rarity.cn_name
            })

    # 当前头盔
    state['equipment']['helmet'] = game.player.equipment.helmet.name if game.player.equipment.helmet else None
    state['equipment']['helmet_id'] = game.player.equipment.helmet.id if game.player.equipment.helmet else None

    # 仓库物品（医疗、护甲修理、子弹、其他）
    state['stash_items'] = []

    # 计算仓库物品总价值
    stash_total_value = 0
    for weapon in game.player.stash_weapons:
        stash_total_value += weapon.value
    for armor in game.player.stash_armors:
        stash_total_value += armor.value
    for helmet in game.player.stash_helmets:
        stash_total_value += helmet.value
    for item in game.player.stash_items:
        stash_total_value += item.value

    state['stash_total_value'] = stash_total_value

    for item in game.player.stash_items:
        item_type = '其他'
        rarity_name = item.rarity.cn_name if hasattr(item.rarity, 'cn_name') else str(item.rarity)

        # 处理Consumable类型
        if isinstance(item, g.Consumable):
            effect = item.effect or {}
            if 'heal' in effect or 'stop_bleed' in effect or 'regen' in effect:
                item_type = '医疗'
            elif 'repair_armor' in effect:
                item_type = '护甲修理'
            elif 'reload_weapon' in effect or 'ammo_type' in effect:
                item_type = '子弹'
            elif 'energy' in effect or 'hydration' in effect:
                item_type = '消耗品'
        # 处理LootItem类型
        elif hasattr(item, 'item_type'):
            item_type = item.item_type or '其他'

        state['stash_items'].append({
            'id': item.id,
            'name': item.name,
            'type': item_type,
            'value': item.value,
            'rarity': rarity_name,
            'description': item.description if hasattr(item, 'description') else ''
        })

    # 商店配件
    state['shop_attachments'] = []
    for aid, adata in g.ATTACHMENTS.items():
        state['shop_attachments'].append({
            'id': aid,
            'name': adata['name'],
            'slot': adata['slot'],
            'effects': adata['effects'],
            'value': adata['value'],
            'rarity': adata['rarity'].cn_name,
            'description': adata['description']
        })

    # 当前武器配件
    weapon = game.player.equipment.primary_weapon
    if weapon:
        state['equipment']['attachments'] = {}
        for slot, att_id in weapon.attachments.items():
            att = g.ATTACHMENTS.get(att_id, {})
            state['equipment']['attachments'][slot] = {
                'id': att_id,
                'name': att.get('name', att_id),
                'effects': att.get('effects', {})
            }
        state['equipment']['effective_accuracy'] = round(weapon.get_effective_accuracy(), 2)
        state['equipment']['effective_fire_rate'] = weapon.get_effective_fire_rate()

    # 商店背包
    state['shop_backpacks'] = []
    for bid, bdata in g.BACKPACKS.items():
        state['shop_backpacks'].append({
            'id': bid,
            'name': bdata['name'],
            'rows': bdata['rows'],
            'cols': bdata['cols'],
            'slots': bdata['rows'] * bdata['cols'],
            'value': bdata['value'],
            'rarity': bdata['rarity'].cn_name,
            'description': bdata['description']
        })

    # 可用地图
    state['available_maps'] = []
    for map_id, map_data in g.ALL_MAPS.items():
        state['available_maps'].append({
            'id': map_id,
            'name': map_data['name'],
            'description': map_data['description'],
            'zone_count': len([z for z in map_data['zones'].values() if not z.get('is_spawn') and not z.get('is_extract')]),
        })

    # 商店消耗品（医疗和修理工具）
    state['shop_consumables'] = []
    for cid, cdata in g.CONSUMABLES.items():
        state['shop_consumables'].append({
            'id': cid,
            'name': cdata['name'],
            'type': cdata['type'],
            'effect': cdata['effect'],
            'value': cdata['value'],
            'rarity': cdata['rarity'].cn_name,
            'description': cdata['description']
        })

    # 当前背包信息
    state['current_backpack'] = {
        'name': '中型背包',  # 默认
        'rows': game.player.equipment.backpack.rows,
        'cols': game.player.equipment.backpack.cols,
        'slots': game.player.equipment.backpack.rows * game.player.equipment.backpack.cols
    }

    # 身体部位护甲状态（HP是整体的，只有护甲分部位）
    for zone in [g.DamageZone.HEAD, g.DamageZone.CHEST, g.DamageZone.LEGS]:
        armor = game.player.stats.get_armor(zone)
        state['player']['body_parts'][zone.name.lower()] = {
            'name': zone.cn_name,
            'has_armor': armor.armor_value > 0 if armor else False,
            'armor_value': armor.armor_value if armor else 0,
            'armor_durability': armor.durability if armor else 0,
            'armor_max_durability': armor.max_durability if armor else 0
        }

    # Debuff状态
    state['player']['debuffs'] = []
    for debuff in game.player.stats.debuffs:
        state['player']['debuffs'].append({
            'name': debuff.cn_name,
            'type': debuff.name,
            'remaining': debuff.remaining,
            'damage': debuff.damage
        })

    # ========== 干员信息 ==========
    state['operator_info'] = {
        'operator_id': game.player.operator.operator_id if hasattr(game.player, 'operator') and game.player.operator else None,
        'operator_class': game.player.operator.operator_class.name if hasattr(game.player, 'operator') and game.player.operator and hasattr(game.player.operator, 'operator_class') else None,
        'operator_name': game.player.operator.name if hasattr(game.player, 'operator') and game.player.operator else None,
        'primary_skill': {
            'name': game.player.operator.primary_skill.name if hasattr(game.player, 'operator') and game.player.operator and hasattr(game.player.operator, 'primary_skill') else None,
            'current_cooldown': game.player.operator.primary_skill.current_cooldown if hasattr(game.player, 'operator') and game.player.operator and hasattr(game.player.operator, 'primary_skill') else 0,
            'max_cooldown': game.player.operator.primary_skill.cooldown if hasattr(game.player, 'operator') and game.player.operator and hasattr(game.player.operator, 'primary_skill') else 0,
            'uses_remaining': game.player.operator.primary_skill.uses_remaining if hasattr(game.player, 'operator') and game.player.operator and hasattr(game.player.operator, 'primary_skill') else 0,
            'can_use': game.player.operator.primary_skill.can_use() if hasattr(game.player, 'operator') and game.player.operator and hasattr(game.player.operator, 'primary_skill') else False
        },
        'secondary_skill': {
            'name': game.player.operator.secondary_skill.name if hasattr(game.player, 'operator') and game.player.operator and hasattr(game.player.operator, 'secondary_skill') else None,
            'current_cooldown': game.player.operator.secondary_skill.current_cooldown if hasattr(game.player, 'operator') and game.player.operator and hasattr(game.player.operator, 'secondary_skill') else 0,
            'max_cooldown': game.player.operator.secondary_skill.cooldown if hasattr(game.player, 'operator') and game.player.operator and hasattr(game.player.operator, 'secondary_skill') else 0,
            'uses_remaining': game.player.operator.secondary_skill.uses_remaining if hasattr(game.player, 'operator') and game.player.operator and hasattr(game.player.operator, 'secondary_skill') else 0,
            'can_use': game.player.operator.secondary_skill.can_use() if hasattr(game.player, 'operator') and game.player.operator and hasattr(game.player.operator, 'secondary_skill') else False
        },
        'unlocked_operators': game.unlocked_operators if hasattr(game, 'unlocked_operators') else ['operator_wyatt'],
        'available_operators': game.available_operators if hasattr(game, 'available_operators') else list(g.OPERATORS.keys())
    }

    # ========== 载具信息 ==========
    state['vehicle_info'] = {
        'in_vehicle': game.player.current_vehicle is not None if hasattr(game.player, 'current_vehicle') else False,
        'is_driver': game.player.is_driver if hasattr(game.player, 'is_driver') else False,
        'current_vehicle': None,
        'zone_vehicles': []
    }
    
    # 当前载具详情
    if hasattr(game.player, 'current_vehicle') and game.player.current_vehicle:
        v = game.player.current_vehicle
        state['vehicle_info']['current_vehicle'] = {
            'vehicle_id': v.vehicle_id,
            'name': v.name,
            'hp': v.hp,
            'max_hp': v.max_hp,
            'destroyed': v.destroyed,
            'passengers': v.passengers if hasattr(v, 'passengers') else [],
            'weapons': [{'name': w.name, 'ammo': w.current_ammo, 'max_ammo': w.mag_size} for w in v.weapons] if hasattr(v, 'weapons') else []
        }

    # ========== 小队信息 ==========
    state['squad_info'] = {
        'has_squad': game.squad is not None if hasattr(game, 'squad') else False,
        'members': []
    }
    
    if hasattr(game, 'squad') and game.squad:
        for member in game.squad.members:
            state['squad_info']['members'].append({
                'id': member.id,
                'name': member.name,
                'is_player': member.is_player if hasattr(member, 'is_player') else False,
                'is_ai': member.is_ai if hasattr(member, 'is_ai') else False,
                'hp': member.stats.hp if hasattr(member, 'stats') else 0,
                'max_hp': member.stats.max_hp if hasattr(member, 'stats') else 0
            })

    # ========== 破译进度 ==========
    state['decode_progress'] = {
        'active_decodes': [],
        'max_concurrent': g.DECODE_CONFIG.get('max_concurrent_decodes', 2) if hasattr(g, 'DECODE_CONFIG') else 2
    }
    
    if game.state == g.GameState.RAID and game.current_raid and hasattr(game.current_raid, 'decode_manager'):
        for decode in game.current_raid.decode_manager.active_decodes:
            state['decode_progress']['active_decodes'].append({
                'item_id': decode.item_id,
                'item_name': decode.item_name,
                'current_progress': decode.current_progress,
                'total_time': decode.total_time,
                'decoder_id': decode.decoder_id,
                'interrupted': decode.interrupted
            })

    # 背包物品
    for item in game.player.equipment.backpack.get_all_items():
        # 确定物品分类
        item_type = '其他'
        if hasattr(item, 'effect'):
            effect = item.effect or {}
            if 'heal' in effect or 'stop_bleed' in effect or 'regen' in effect:
                item_type = '医疗'
            elif 'repair_armor' in effect:
                item_type = '护甲修理'
            elif 'reload_weapon' in effect or 'ammo_type' in effect:
                item_type = '子弹'
            elif 'energy' in effect or 'hydration' in effect:
                item_type = '消耗品'

        state['backpack'].append({
            'id': item.id,
            'name': item.name,
            'rarity': item.rarity.cn_name,
            'value': item.value,
            'weight': item.weight,
            'type': item_type
        })

    # 保险箱物品
    for item in game.player.equipment.secure_container.get_all_items():
        state['secure_container'].append({
            'id': item.id,
            'name': item.name,
            'rarity': item.rarity.cn_name,
            'value': item.value
        })

    # 行动状态
    if game.state == g.GameState.RAID and game.current_raid:
        zone = game.current_raid.get_zone(game.player.current_zone)

        # 构建完整的地图数据
        map_zones = {}
        for zid, z in game.current_raid.zones.items():
            map_zones[zid] = {
                'id': zid,
                'name': z['name'],
                'description': z.get('description', ''),
                'x': z.get('x', 0),
                'y': z.get('y', 0),
                'danger_level': z.get('danger_level', 1),
                'is_spawn': z.get('is_spawn', False),
                'is_extract': z.get('is_extract', False),
                'connections': z.get('connections', []),
                'visited': zid in game.current_raid.visited_zones
            }

        state['raid'] = {
            'map_name': game.current_raid.map_data['name'],
            'map_width': game.current_raid.map_data.get('width', 10),
            'map_height': game.current_raid.map_data.get('height', 8),
            'current_zone': game.player.current_zone,
            'zone_name': zone['name'],
            'zone_description': zone['description'],
            'danger_level': zone.get('danger_level', 1),
            'time_elapsed': game.current_raid.time_elapsed,
            'max_time': game.current_raid.max_time,
            'is_extract': zone.get('is_extract', False),
            'active_extraction': game.current_raid.active_extraction,
            'active_extraction_name': game.current_raid.zones[game.current_raid.active_extraction]['name'] if game.current_raid.active_extraction else '',
            'zones': map_zones,
            'connections': [],
            'events': [e['message'] for e in game.current_raid.pending_events] if game.current_raid.pending_events else [],
            'zone_loot': []
        }

        # 当前区域战利品
        zone_loot = zone.get("loot", [])
        for loot_entry in zone_loot:
            item_data = loot_entry.get("data", {})
            state['raid']['zone_loot'].append({
                'id': loot_entry["id"],
                'name': item_data.get("name", "未知物品"),
                'rarity': item_data.get("rarity", g.Rarity.COMMON).cn_name if hasattr(item_data.get("rarity", g.Rarity.COMMON), 'cn_name') else item_data.get("rarity", "灰色"),
                'value': item_data.get("value", 0),
                'type': item_data.get("type", "物资")
            })

        for conn_id in zone.get('connections', []):
            conn_zone = game.current_raid.get_zone(conn_id)
            is_active_extract = (conn_id == game.current_raid.active_extraction)
            state['raid']['connections'].append({
                'id': conn_id,
                'name': conn_zone['name'],
                'is_extract': conn_zone.get('is_extract', False),
                'is_active_extract': is_active_extract
            })

        # 当前区域载具
        state['raid']['zone_vehicles'] = []
        if hasattr(game.current_raid, 'get_vehicles_in_zone'):
            vehicles = game.current_raid.get_vehicles_in_zone(game.player.current_zone)
            for v in vehicles:
                state['raid']['zone_vehicles'].append({
                    'vehicle_id': v.vehicle_id,
                    'name': v.name,
                    'hp': v.hp,
                    'max_hp': v.max_hp,
                    'destroyed': v.destroyed,
                    'passenger_count': len(v.passengers) if hasattr(v, 'passengers') else 0,
                    'max_passengers': v.max_passengers if hasattr(v, 'max_passengers') else 0
                })
                # 同时更新 vehicle_info 中的 zone_vehicles
                state['vehicle_info']['zone_vehicles'].append({
                    'vehicle_id': v.vehicle_id,
                    'name': v.name,
                    'hp': v.hp,
                    'max_hp': v.max_hp
                })

    # 战斗状态
    if game.state == g.GameState.COMBAT and game.current_enemy:
        enemy = game.current_enemy
        state['combat'] = {
            'enemy_name': enemy.name,
            'enemy_hp': enemy.hp,
            'enemy_max_hp': enemy.max_hp,
            'is_boss': enemy.is_boss
        }

    # 搜索状态
    if game.state == g.GameState.SEARCH and game.current_enemy:
        enemy = game.current_enemy
        enemy_items = []
        if enemy.backpack:
            for item in enemy.backpack.get_all_items():
                enemy_items.append({
                    'id': item.id,
                    'name': item.name,
                    'rarity': item.rarity.cn_name if hasattr(item, 'rarity') else '灰色',
                    'value': item.value if hasattr(item, 'value') else 0
                })
        state['search'] = {
            'enemy_name': enemy.name,
            'items': enemy_items
        }

    return jsonify(state)

@app.route('/api/action', methods=['POST'])
def do_action():
    """执行游戏动作"""
    game = get_game()
    data = request.json
    action = data.get('action')
    params = data.get('params', {})

    result = {
        'success': False,
        'message': ''
    }

    game.clear_messages()

    if action == 'start_raid':
        map_id = params if isinstance(params, str) else params.get('map_id', 'dam') if isinstance(params, dict) else 'dam'
        map_data = g.ALL_MAPS.get(map_id, g.MAP_DAM)
        game.start_raid(map_data)
        result['success'] = True
        result['message'] = '行动开始！'

    elif action == 'move':
        zone_id = params.get('zone_id')
        if zone_id:
            success, msg = game.move_to_zone(zone_id)
            result['success'] = success
            result['message'] = msg

    elif action == 'search':
        success, msg = game.search_zone()
        result['success'] = success
        result['message'] = msg

    elif action == 'extract':
        success, msg = game.try_extract()
        result['success'] = success
        result['message'] = msg

    elif action == 'attack':
        target = params.get('target', 'body')
        success, msg = game.combat_action('attack', target)
        result['success'] = success
        result['message'] = msg

    elif action == 'reload':
        success, msg = game.combat_action('reload')
        result['success'] = success
        result['message'] = msg

    elif action == 'heal':
        success, msg = game.combat_action('heal')
        result['success'] = success
        result['message'] = msg

    elif action == 'flee':
        success, msg = game.combat_action('flee')
        result['success'] = success
        result['message'] = msg

    elif action == 'search_enemy':
        search_action = params.get('search_action', 'take_all')
        item_id = params.get('item_id')
        success, msg = game.search_enemy_backpack(search_action, item_id)
        result['success'] = success
        result['message'] = msg

    elif action == 'buy_backpack':
        backpack_id = params.get('backpack_id')
        if backpack_id and backpack_id in g.BACKPACKS:
            backpack_data = g.BACKPACKS[backpack_id]
            if game.player.stats.money >= backpack_data['value']:
                game.player.stats.money -= backpack_data['value']
                # 创建新背包并转移物品
                old_items = game.player.equipment.backpack.get_all_items()
                game.player.equipment.backpack = g.Backpack(
                    rows=backpack_data['rows'],
                    cols=backpack_data['cols']
                )
                for item in old_items:
                    game.player.equipment.backpack.add_item(item)
                result['success'] = True
                result['message'] = f"购买了{backpack_data['name']}！({backpack_data['rows']*backpack_data['cols']}格)"
            else:
                result['success'] = False
                result['message'] = f"金钱不足！需要${backpack_data['value']}"
        else:
            result['success'] = False
            result['message'] = "无效的背包ID"

    elif action == 'buy_consumable':
        consumable_id = params.get('consumable_id')
        if consumable_id and consumable_id in g.CONSUMABLES:
            cdata = g.CONSUMABLES[consumable_id]
            if game.player.stats.money >= cdata['value']:
                game.player.stats.money -= cdata['value']
                # 创建消耗品并添加到背包
                item = g.Consumable(
                    id=f"buy_{consumable_id}_{random.randint(1000, 9999)}",
                    name=cdata['name'],
                    weight=cdata['weight'],
                    value=cdata['value'],
                    rarity=cdata['rarity'],
                    effect=cdata['effect']
                )
                if game.player.equipment.backpack.add_item(item):
                    result['success'] = True
                    result['message'] = f"购买了{cdata['name']}！"
                else:
                    game.player.stats.money += cdata['value']  # 退款
                    result['success'] = False
                    result['message'] = "背包已满！"
            else:
                result['success'] = False
                result['message'] = f"金钱不足！需要${cdata['value']}"
        else:
            result['success'] = False
            result['message'] = "无效的物品ID"

    elif action == 'use_item':
        item_id = params.get('item_id')
        if item_id:
            success, msg = game.player.use_item(item_id)
            result['success'] = success
            result['message'] = msg

    elif action == 'return_base':
        game.return_to_base()
        result['success'] = True
        result['message'] = '返回基地'

    elif action == 'rest':
        game.player.stats = g.PlayerStats(
            money=game.player.stats.money,
            xp=game.player.stats.xp,
            level=game.player.stats.level
        )
        # 重新同步护甲状态
        if game.player.equipment.armor:
            game.player.stats.chest_armor = g.ArmorStatus(
                armor_value=game.player.equipment.armor.armor_class,
                max_armor=game.player.equipment.armor.armor_class,
                durability=game.player.equipment.armor.durability,
                max_durability=game.player.equipment.armor.max_durability
            )
        if game.player.equipment.helmet:
            game.player.stats.head_armor = g.ArmorStatus(
                armor_value=game.player.equipment.helmet.armor_class,
                max_armor=game.player.equipment.helmet.armor_class,
                durability=game.player.equipment.helmet.durability,
                max_durability=game.player.equipment.helmet.max_durability
            )
        game.add_message('你休息了一段时间，状态已恢复。')
        result['success'] = True
        result['message'] = '状态已恢复'

    elif action == 'emergency_extract':
        game.player.equipment.backpack.clear()
        game.state = g.GameState.BASE
        game.current_raid = None
        game.add_message('紧急撤离成功，丢失了所有背包物品。')
        result['success'] = True
        result['message'] = '紧急撤离成功'

    elif action == 'new_game':
        # 重置游戏
        # 确定当前用户的game_id
        if 'username' in session:
            game_id = f"user_{session['username']}"
        else:
            game_id = session.get('game_id')

        # 删除旧游戏
        if game_id and game_id in games:
            del games[game_id]

        # 创建新游戏
        games[game_id] = g.Game()
        games[game_id].state = g.GameState.BASE  # 设置为基地状态
        result['success'] = True
        result['message'] = '新游戏开始'

    elif action == 'welfare':
        # 低保功能：总资产低于5000时可领取10000元
        # 计算总资产
        total_assets = game.player.stats.money
        for weapon in game.player.stash_weapons:
            total_assets += weapon.value
        for armor in game.player.stash_armors:
            total_assets += armor.value
        for helmet in game.player.stash_helmets:
            total_assets += helmet.value
        for item in game.player.stash_items:
            total_assets += item.value

        if total_assets >= 5000:
            result['success'] = False
            result['message'] = f'总资产为{total_assets}，不低于5000，无法领取低保！'
        else:
            game.player.stats.money += 10000
            game.add_message(f'领取低保成功！获得10000元。当前余额：{game.player.stats.money}')
            result['success'] = True
            result['message'] = '领取低保成功！获得10000元'

    # 商店操作
    elif action == 'buy_weapon':
        weapon_id = params.get('weapon_id')
        if weapon_id:
            success, msg = game.buy_weapon(weapon_id)
            result['success'] = success
            result['message'] = msg

    elif action == 'buy_armor':
        armor_id = params.get('armor_id')
        if armor_id:
            success, msg = game.buy_armor(armor_id)
            result['success'] = success
            result['message'] = msg

    elif action == 'buy_helmet':
        helmet_id = params.get('helmet_id')
        if helmet_id and helmet_id in g.HELMETS:
            hdata = g.HELMETS[helmet_id]
            if game.player.stats.money >= hdata['value']:
                game.player.stats.money -= hdata['value']
                helmet = g.Armor(
                    id=f"{helmet_id}_{random.randint(1000, 9999)}",
                    name=hdata['name'],
                    weight=hdata['weight'],
                    value=hdata['value'],
                    rarity=hdata['rarity'],
                    armor_class=hdata['class'],
                    durability=hdata['durability'],
                    max_durability=hdata['max_durability']
                )
                game.player.stash_items.append(helmet)
                result['success'] = True
                result['message'] = f"购买了{hdata['name']}！"
            else:
                result['success'] = False
                result['message'] = f"金钱不足！需要${hdata['value']}"

    elif action == 'equip_helmet':
        helmet_id = params.get('helmet_id')
        if helmet_id:
            for helmet in game.player.stash_items:
                if helmet.id == helmet_id and isinstance(helmet, g.Armor):
                    if game.player.equipment.helmet:
                        game.player.stash_items.append(game.player.equipment.helmet)
                    game.player.equipment.equip_helmet(helmet, game.player.stats)
                    game.player.stash_items.remove(helmet)
                    result['success'] = True
                    result['message'] = f"装备了{helmet.name}"
                    break
            else:
                result['success'] = False
                result['message'] = "找不到该头盔"

    elif action == 'sell_helmet':
        helmet_id = params.get('helmet_id')
        if helmet_id:
            for helmet in game.player.stash_items:
                if helmet.id == helmet_id:
                    price = helmet.value // 2
                    game.player.stats.money += price
                    game.player.stash_items.remove(helmet)
                    result['success'] = True
                    result['message'] = f"出售了{helmet.name}，获得${price}"
                    break
            else:
                result['success'] = False
                result['message'] = "找不到该头盔"

    # 仓库操作
    elif action == 'equip_weapon':
        weapon_id = params.get('weapon_id')
        if weapon_id:
            success, msg = game.equip_weapon(weapon_id)
            result['success'] = success
            result['message'] = msg

    elif action == 'equip_armor':
        armor_id = params.get('armor_id')
        if armor_id:
            success, msg = game.equip_armor(armor_id)
            result['success'] = success
            result['message'] = msg

    elif action == 'sell_weapon':
        weapon_id = params.get('weapon_id')
        if weapon_id:
            success, msg = game.sell_stash_weapon(weapon_id)
            result['success'] = success
            result['message'] = msg

    elif action == 'sell_armor':
        armor_id = params.get('armor_id')
        if armor_id:
            success, msg = game.sell_stash_armor(armor_id)
            result['success'] = success
            result['message'] = msg

    # 卸下装备
    elif action == 'unequip_weapon':
        success, msg = game.unequip_weapon()
        result['success'] = success
        result['message'] = msg

    elif action == 'unequip_armor':
        success, msg = game.unequip_armor()
        result['success'] = success
        result['message'] = msg

    elif action == 'unequip_helmet':
        success, msg = game.unequip_helmet()
        result['success'] = success
        result['message'] = msg

    elif action == 'unequip_all':
        msg = game.unequip_all()
        result['success'] = True
        result['message'] = msg

    elif action == 'drop_backpack_item':
        item_id = params.get('item_id')
        if item_id:
            success, msg = game.drop_backpack_item(item_id)
            result['success'] = success
            result['message'] = msg

    elif action == 'pickup_loot':
        loot_id = params.get('loot_id')
        if loot_id:
            success, msg = game.pickup_loot(loot_id)
            result['success'] = success
            result['message'] = msg

    elif action == 'clear_backpack':
        msg = game.clear_backpack()
        result['success'] = True
        result['message'] = msg

    elif action == 'move_to_stash':
        item_id = params.get('item_id')
        if item_id:
            success, msg = game.move_to_stash(item_id)
            result['success'] = success
            result['message'] = msg

    elif action == 'move_to_backpack':
        item_id = params.get('item_id')
        if item_id:
            success, msg = game.move_to_backpack(item_id)
            result['success'] = success
            result['message'] = msg

    elif action == 'buy_attachment':
        att_id = params.get('attachment_id') if isinstance(params, dict) else None
        if att_id and att_id in g.ATTACHMENTS:
            att = g.ATTACHMENTS[att_id]
            if game.player.stats.money >= att['value']:
                game.player.stats.money -= att['value']
                # 直接安装到当前武器
                weapon = game.player.equipment.primary_weapon
                if weapon:
                    success, msg = weapon.install_attachment(att_id)
                    result['success'] = success
                    result['message'] = f"花费${att['value']}，{msg}"
                else:
                    game.player.stats.money += att['value']
                    result['success'] = False
                    result['message'] = "没有装备武器，无法安装配件"
            else:
                result['success'] = False
                result['message'] = f"金钱不足！需要${att['value']}"
        else:
            result['success'] = False
            result['message'] = "配件不存在"

    elif action == 'remove_attachment':
        slot = params.get('slot') if isinstance(params, dict) else None
        weapon = game.player.equipment.primary_weapon
        if weapon and slot:
            success, msg = weapon.remove_attachment(slot)
            result['success'] = success
            result['message'] = msg
        else:
            result['success'] = False
            result['message'] = "无法拆卸配件"

    elif action == 'auto_equip':
        msg = game.auto_equip_best()
        result['success'] = True
        result['message'] = msg

    elif action == 'save_game':
        if 'username' in session:
            # 已登录用户保存到用户目录
            username = session['username']
            user_save_dir = os.path.join(SAVE_DIR, username)
            os.makedirs(user_save_dir, exist_ok=True)
            save_path = os.path.join(user_save_dir, 'save.json')
            game_id = f"user_{username}"
        else:
            # 游客模式
            os.makedirs(SAVE_DIR, exist_ok=True)
            game_id = session.get('game_id', 'default')
            save_path = os.path.join(SAVE_DIR, f'{game_id}.json')
        save_data = g.save_game(game)
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)
        result['success'] = True
        result['message'] = '游戏已保存！'

    elif action == 'load_game':
        if 'username' in session:
            # 已登录用户从用户目录加载
            username = session['username']
            game_id = f"user_{username}"
            save_path = os.path.join(SAVE_DIR, username, 'save.json')
        else:
            # 游客模式
            game_id = session.get('game_id', 'default')
            save_path = os.path.join(SAVE_DIR, f'{game_id}.json')
        if os.path.exists(save_path):
            with open(save_path, 'r', encoding='utf-8') as f:
                save_data = json.load(f)
            loaded_game = g.load_game(save_data)
            games[game_id] = loaded_game
            result['success'] = True
            result['message'] = '存档已加载！'
        else:
            result['success'] = False
            result['message'] = '没有找到存档文件！'

    # ========== 干员系统 ==========
    elif action == 'select_operator':
        operator_id = params.get('operator_id')
        if operator_id:
            if operator_id in game.unlocked_operators:
                game.player.set_operator(operator_id)
                result['success'] = True
                result['message'] = f'已切换干员：{g.OPERATORS.get(operator_id, {}).get("name", operator_id)}'
            else:
                result['success'] = False
                result['message'] = '该干员尚未解锁！'
        else:
            result['success'] = False
            result['message'] = '请指定干员ID'

    elif action == 'use_skill':
        skill_type = params.get('skill_type', 'primary')
        success, msg = game.use_operator_skill(skill_type)
        result['success'] = success
        result['message'] = msg

    # ========== 载具系统 ==========
    elif action == 'board_vehicle':
        vehicle_id = params.get('vehicle_id')
        as_driver = params.get('as_driver', False)
        if vehicle_id:
            success, msg = game.board_vehicle(vehicle_id, as_driver)
            result['success'] = success
            result['message'] = msg
        else:
            result['success'] = False
            result['message'] = '请指定载具ID'

    elif action == 'exit_vehicle':
        success, msg = game.exit_vehicle()
        result['success'] = success
        result['message'] = msg

    elif action == 'vehicle_attack':
        target = params.get('target')
        if target:
            # target可能是enemy_id或vehicle_id
            # 查找目标
            enemy = None
            target_vehicle = None
            if game.current_raid:
                for e in game.current_raid.enemies:
                    if e.id == target and e.is_alive():
                        enemy = e
                        break
                for v in game.current_raid.vehicles:
                    if v.vehicle_id == target and not v.destroyed:
                        target_vehicle = v
                        break
            if enemy:
                damage, msg = game.player.vehicle_attack(enemy)
                result['success'] = damage > 0
                result['message'] = msg
            elif target_vehicle:
                damage, msg = game.player.vehicle_attack(target_vehicle)
                result['success'] = damage > 0
                result['message'] = msg
            else:
                result['success'] = False
                result['message'] = '找不到目标'
        else:
            result['success'] = False
            result['message'] = '请指定攻击目标'

    # ========== 破译系统 ==========
    elif action == 'start_decode':
        loot_id = params.get('loot_id')
        if loot_id:
            success, msg = game.start_decode(loot_id)
            result['success'] = success
            result['message'] = msg
        else:
            result['success'] = False
            result['message'] = '请指定要破译的物品ID'

    elif action == 'continue_decode':
        # 破译进度在move/search等行动时自动推进，此action用于手动推进
        if game.state == g.GameState.RAID and game.current_raid:
            game.current_raid.tick()
            result['success'] = True
            result['message'] = '破译进度已推进'
        else:
            result['success'] = False
            result['message'] = '当前不在行动中'

    elif action == 'cancel_decode':
        if game.state == g.GameState.RAID and game.current_raid:
            item_id = params.get('item_id')
            if item_id:
                for decode in game.current_raid.decode_manager.active_decodes:
                    if decode.item_id == item_id:
                        game.current_raid.decode_manager.active_decodes.remove(decode)
                        result['success'] = True
                        result['message'] = f'已取消破译：{decode.item_name}'
                        break
                else:
                    result['success'] = False
                    result['message'] = '找不到该破译任务'
            else:
                # 取消所有破译
                count = len(game.current_raid.decode_manager.active_decodes)
                game.current_raid.decode_manager.active_decodes.clear()
                result['success'] = True
                result['message'] = f'已取消{count}个破译任务'
        else:
            result['success'] = False
            result['message'] = '当前不在行动中'

    # 检查死亡
    if game.state == g.GameState.DEAD:
        game.handle_death()
        result['message'] += '\n你阵亡了！'

    # 检查撤离成功后返回基地
    if game.state == g.GameState.EXTRACTED:
        game.return_to_base()

    return jsonify(result)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)