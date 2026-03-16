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

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dark-zone-secret-key-2024')

# 存储游戏实例
games = {}
SAVE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'saves')

def get_game():
    """获取或创建游戏实例"""
    if 'game_id' not in session:
        session['game_id'] = str(uuid.uuid4())

    game_id = session['game_id']
    if game_id not in games:
        games[game_id] = g.Game()

    return games[game_id]

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
            'armor': game.player.equipment.armor.name if game.player.equipment.armor else None,
            'armor_id': game.player.equipment.armor.id if game.player.equipment.armor else None,
            'armor_durability': game.player.equipment.armor.durability if game.player.equipment.armor else 0,
            'armor_max_durability': game.player.equipment.armor.max_durability if game.player.equipment.armor else 0,
        },
        'stash_weapons': [],
        'stash_armors': [],
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

    # 身体部位状态（简化为头/胸/腿）
    for zone in g.DamageZone:
        part = game.player.stats.get_body_part(zone)
        armor = game.player.stats.get_armor(zone)
        state['player']['body_parts'][zone.name.lower()] = {
            'name': zone.cn_name,
            'hp': part.hp,
            'max_hp': part.max_hp,
            'is_broken': part.is_broken,
            'is_bleeding': part.is_bleeding,
            'bleed_damage': part.bleed_damage,
            'has_armor': armor.armor_value > 0 if armor else False,
            'armor_value': armor.armor_value if armor else 0,
            'armor_durability': armor.durability if armor else 0
        }

    # 背包物品
    for item in game.player.equipment.backpack.get_all_items():
        state['backpack'].append({
            'id': item.id,
            'name': item.name,
            'rarity': item.rarity.cn_name,
            'value': item.value,
            'weight': item.weight
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
            'connections': []
        }

        for conn_id in zone.get('connections', []):
            conn_zone = game.current_raid.get_zone(conn_id)
            is_active_extract = (conn_id == game.current_raid.active_extraction)
            state['raid']['connections'].append({
                'id': conn_id,
                'name': conn_zone['name'],
                'is_extract': conn_zone.get('is_extract', False),
                'is_active_extract': is_active_extract
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
        game.start_raid(g.MAP_INDUSTRIAL)
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
        old_id = session.get('game_id')
        if old_id and old_id in games:
            del games[old_id]
        new_id = str(uuid.uuid4())
        session['game_id'] = new_id
        games[new_id] = g.Game()
        games[new_id].state = g.GameState.BASE  # 设置为基地状态
        result['success'] = True
        result['message'] = '新游戏开始'

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

    elif action == 'auto_equip':
        msg = game.auto_equip_best()
        result['success'] = True
        result['message'] = msg

    elif action == 'save_game':
        os.makedirs(SAVE_DIR, exist_ok=True)
        game_id = session.get('game_id', 'default')
        save_path = os.path.join(SAVE_DIR, f'{game_id}.json')
        save_data = g.save_game(game)
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)
        result['success'] = True
        result['message'] = '游戏已保存！'

    elif action == 'load_game':
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