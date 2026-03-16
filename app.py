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

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dark-zone-secret-key-2024')

# 存储游戏实例
games = {}

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
            'weapon_ammo': game.player.equipment.primary_weapon.current_ammo if game.player.equipment.primary_weapon else 0,
            'weapon_mag': game.player.equipment.primary_weapon.mag_size if game.player.equipment.primary_weapon else 0,
            'armor': game.player.equipment.armor.name if game.player.equipment.armor else None,
            'armor_durability': game.player.equipment.armor.durability if game.player.equipment.armor else 0,
            'armor_max_durability': game.player.equipment.armor.max_durability if game.player.equipment.armor else 0,
        },
        'backpack': [],
        'backpack_value': game.player.equipment.backpack.get_total_value(),
        'secure_container': [],
        'messages': game.messages[-10:] if game.messages else []
    }

    # 身体部位状态
    for zone in g.DamageZone:
        part = game.player.stats.get_body_part(zone)
        state['player']['body_parts'][zone.name.lower()] = {
            'name': zone.cn_name,
            'hp': part.hp,
            'max_hp': part.max_hp,
            'is_broken': part.is_broken
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
        state['raid'] = {
            'map_name': game.current_raid.map_data['name'],
            'current_zone': game.player.current_zone,
            'zone_name': zone['name'],
            'zone_description': zone['description'],
            'danger_level': zone.get('danger_level', 1),
            'time_elapsed': game.current_raid.time_elapsed,
            'max_time': game.current_raid.max_time,
            'connections': []
        }

        for conn_id in zone.get('connections', []):
            conn_zone = game.current_raid.get_zone(conn_id)
            state['raid']['connections'].append({
                'id': conn_id,
                'name': conn_zone['name'],
                'is_extract': conn_zone.get('is_extract', False)
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
        if session.get('game_id') in games:
            del games[session['game_id']]
        session['game_id'] = str(uuid.uuid4())
        result['success'] = True
        result['message'] = '新游戏开始'

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