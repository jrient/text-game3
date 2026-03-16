#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
账号认证模块
处理用户注册、登录、登出等功能
"""

import os
import json
import bcrypt
from datetime import datetime

USERS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'users')
USERS_FILE = os.path.join(USERS_DIR, 'users.json')


def ensure_users_dir():
    """确保用户数据目录存在"""
    os.makedirs(USERS_DIR, exist_ok=True)


def load_users():
    """加载用户数据"""
    ensure_users_dir()
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {"users": {}}
    return {"users": {}}


def save_users(users_data):
    """保存用户数据"""
    ensure_users_dir()
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users_data, f, ensure_ascii=False, indent=2)


def register_user(username, password):
    """
    注册新用户

    Returns:
        (success: bool, message: str)
    """
    if not username or len(username) < 2:
        return False, "用户名至少需要2个字符"

    if not password or len(password) < 4:
        return False, "密码至少需要4个字符"

    if len(username) > 20:
        return False, "用户名不能超过20个字符"

    # 只允许字母、数字和下划线
    if not username.replace('_', '').replace('-', '').isalnum():
        return False, "用户名只能包含字母、数字、下划线和连字符"

    users_data = load_users()

    if username.lower() in [u.lower() for u in users_data["users"].keys()]:
        return False, "用户名已存在"

    # 哈希密码
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    users_data["users"][username] = {
        "username": username,
        "password_hash": password_hash,
        "created_at": datetime.now().isoformat(),
        "last_login": None
    }

    save_users(users_data)
    return True, "注册成功"


def login_user(username, password):
    """
    用户登录验证

    Returns:
        (success: bool, message: str)
    """
    if not username or not password:
        return False, "用户名和密码不能为空"

    users_data = load_users()

    # 查找用户（不区分大小写）
    actual_username = None
    for uname in users_data["users"].keys():
        if uname.lower() == username.lower():
            actual_username = uname
            break

    if not actual_username:
        return False, "用户名或密码错误"

    user = users_data["users"][actual_username]

    # 验证密码
    try:
        if bcrypt.checkpw(password.encode('utf-8'), user["password_hash"].encode('utf-8')):
            # 更新最后登录时间
            users_data["users"][actual_username]["last_login"] = datetime.now().isoformat()
            save_users(users_data)
            return True, actual_username
    except Exception:
        pass

    return False, "用户名或密码错误"


def user_exists(username):
    """检查用户是否存在"""
    users_data = load_users()
    return username in users_data["users"]