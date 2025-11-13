# Telebot

一个使用 **Python + Telethon + Supabase** 构建的群管机器人模板，提供入群校验、内容风控、自动回复、积分体系等核心模块的代码示例。相比之前的思路型文档，此仓库已经包含可以运行的代码骨架与单元测试，方便你直接按需拓展。下文涵盖架构、功能、配置与运行步骤。

## 架构概览

```
┌────────────────┐        ┌─────────────────────┐        ┌────────────────────────┐
│ Telegram Client │ <────> │ TelebotApplication  │ <────> │ SupabaseConfigStore     │
└────────────────┘        │  • Telethon 事件监听 │        │  • REST/Realtime 配置拉取│
                           │  • RuleEngine 策略匹配│        │  • 积分/审计写回        │
                           └─────────────────────┘        └────────────────────────┘
```

- **TelebotApplication**：封装 Telethon `TelegramClient`，注册消息事件，拉取群组配置，执行动作（删除、禁言、回复、积分）。
- **RuleEngine**：将 Supabase 中的关键词、正则、积分规则编译为本地 `Rule` 列表，高性能匹配消息内容。
- **SupabaseConfigStore**：通过 Supabase REST 接口读取/写入配置，默认带缓存；在本地或测试环境下自动回落为内存存储，方便快速启动。

## 代码目录

```
telebot/
├── __init__.py           # 对外导出 Settings、load_settings
├── bot.py                # Telethon 事件循环与动作执行
├── config.py             # 纯标准库实现的环境变量配置
├── rules.py              # 关键词/正则/积分的统一规则引擎
└── supabase.py           # Supabase REST 客户端与本地缓存
```

`tests/test_rules.py` 提供了对规则引擎的基础验证，你可以在此基础上持续补齐更多单元测试。

## 功能特性

- **自动删除 & 惩罚**：配置 `banned_keywords` 或 `punishments` 后，匹配到违规词自动删帖、记录审计日志，并可选触发禁言。
- **自动回复**：`auto_replies` 支持图文模板（代码示例以文本为主），不同关键词可定制删除原消息、回复内容等。
- **积分体系**：`point_rules` 允许用正则表达式定义积分发放逻辑，并通过 Supabase `increment_points` RPC 或本地回退存储用户积分。
- **签到命令**：示例中自带 `/checkin` 监听器，管理员可以按需扩展更多命令（如 `/warn`、`/config` 等）。
- **积分查询**：`/me` 指令会读取 Supabase `points_balances` 视图（或本地缓存）返回当前积分。
- **Supabase 集成**：将配置放入 `group_configs` 表，将动作写入 `action_logs`，并可自定义 `increment_points` 函数实现积分账本。
- **刷屏拦截**：`flood_control` 节点支持配置消息频率阈值，命中后自动禁言并记录审计日志。
- **欢迎消息**：`welcome` 配置允许自定义模板、@提及占位符，以及是否强制设置用户名后再欢迎。

## 配置

1. 复制 `.env.example`（若无可直接新建 `.env`）并填入：
   ```bash
   TELEGRAM_API_ID=123456
   TELEGRAM_API_HASH=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   TELEGRAM_BOT_TOKEN=123456:bot_token
   SUPABASE_URL=https://xxx.supabase.co
   SUPABASE_SERVICE_ROLE_KEY=service_role_secret
   ```
2. 可选：`SUPABASE_ANON_KEY`、`CONFIG_CACHE_SECONDS`、`DEFAULT_LANGUAGE` 等也可以在 `.env` 中覆盖。
3. 在 Supabase 建立如下额外资源：
   - `points_balances` 视图（或表），需至少包含 `chat_id`、`user_id`、`balance` 字段，供 `/me` 查询积分。
   - `group_configs` 表中的 `welcome` 字段示例：
     ```json
     {
       "enabled": true,
       "text": "欢迎 {mention} 加入 {chat_title}，请阅读群公告",
       "require_username": true,
       "missing_username_notice": "{first_name}，请先设置 Telegram 用户名，方便管理员联系"
     }
     ```

## 运行

```bash
pip install -e .[test]
python -m telebot.bot  # 或在代码中 from telebot import TelebotApplication
```

在 Telegram 中与 Bot 对话或拉入群组后，即可享受自动校验、回复与积分等能力。需要扩展功能时，只需在 Supabase 增加配置项，并在 `RuleEngine.from_config` / `TelebotApplication._apply_action` 中实现对应动作即可。

## 测试

```bash
pytest
```

测试覆盖规则引擎的关键词和积分联动，可作为今后添加更多模块的参考。
