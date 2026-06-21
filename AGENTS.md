# AGENTS.md

本文件给 Codex 等 agent 提供仓库维护说明。

## 项目概览

这是一个 LangBot 插件，插件名为 `ElysianRealmAssistant`，用于响应崩坏3 往世乐土相关查询，返回推荐攻略、角色攻略图片或配置列表。

当前分支已迁移到 LangBot Plugin SDK v4 结构：

- 插件入口由 [manifest.yaml](manifest.yaml) 声明。
- [main.py](main.py) 只保留 `BasePlugin` 入口类，并初始化核心逻辑。
- 事件监听器位于 [components/event_listener/default.py](components/event_listener/default.py)。
- 业务逻辑集中在 [core.py](core.py)。

当前插件版本在 [manifest.yaml](manifest.yaml) 的 `metadata.version` 中声明为 `1.7.0`。

## 运行环境

- Python 版本要求：`>=3.10`
  - 依据：[pyproject.toml](pyproject.toml) 的 `requires-python = ">=3.10"`
- 包管理优先使用 `uv`
- 也保留 [requirements.txt](requirements.txt)，用于传统 `pip` 安装

核心依赖：

- `langbot-plugin>=0.4.5`
- `PyYAML`
- `httpx`
- `regex`

注意：当前实现使用 `httpx.AsyncClient`，不是 `requests`。

## 主要文件

- [manifest.yaml](manifest.yaml)：LangBot v4 插件清单，声明插件元信息、组件目录和 Python 入口。
- [main.py](main.py)：v4 插件主入口，创建 `ElysianRealmAssistantCore`。
- [components/event_listener/default.py](components/event_listener/default.py)：事件监听器，注册私聊/群聊普通消息事件。
- [core.py](core.py)：插件业务逻辑，包含指令匹配、查询路由、网络请求、图片缓存、配置更新。
- [ElysianRealmConfig.yaml](ElysianRealmConfig.yaml)：角色攻略键与用户可输入别名的映射。
- [pyproject.toml](pyproject.toml)：项目元数据、Python 版本、依赖和检查工具配置。
- [uv.lock](uv.lock)：`uv` 锁文件。
- [README.md](README.md)：面向用户的安装和使用说明。

## 插件入口与消息流程

LangBot v4 通过 [manifest.yaml](manifest.yaml) 加载插件：

1. `execution.python` 指向 [main.py](main.py) 的 `ElysianRealmAssistant`。
2. `ElysianRealmAssistant.initialize()` 创建并初始化 `ElysianRealmAssistantCore`。
3. `components.EventListener.fromDirs` 加载 [components/event_listener/default.py](components/event_listener/default.py)。
4. `DefaultEventListener.initialize()` 注册：
   - `PersonNormalMessageReceived`
   - `GroupNormalMessageReceived`
5. `DefaultEventListener.on_message()` 提取文本消息，并交给 `core.handle_message(...)`。
6. `core.handle_message(...)` 根据正则判断是否为插件指令，命中后返回文本或图片消息链，并调用 `prevent_default()` / `prevent_postorder()`。

## 支持的指令

正则入口定义在 [core.py](core.py) 的 `ElysianRealmAssistantCore.url_pattern`。当前支持：

- `乐土list`
- `[关键词]乐土list`
- `乐土推荐`
- `乐土推荐[1-2 位数字]`
- `全部乐土推荐`
- `[1-5 个字符]乐土[可选 1 位数字]`
- `[1-5 个字符][两个汉字]流`
- `RealmCommand add [key] [value1,value2,...]`

`RealmCommand add` 会直接写回 [ElysianRealmConfig.yaml](ElysianRealmConfig.yaml)，修改前需要确认这是预期行为。

## 数据与图片来源

推荐攻略：

- 请求米游社接口：`https://bbs-api.miyoushe.com/post/wapi/userPost?uid=5625196`
- 从返回文章中筛选标题匹配 `往世乐土丨V\d+\.\d+[一二三四五六七八九十]+期推荐角色BUFF表` 的帖子。
- 使用帖子图片列表返回指定序号的推荐图。

角色攻略：

- 根据 [ElysianRealmConfig.yaml](ElysianRealmConfig.yaml) 匹配用户输入。
- 命中后拼接 GitHub Raw 图片地址：
  `https://raw.githubusercontent.com/BiFangKNT/ElysianRealm-Data/refs/heads/master/{key}.jpg`

## 缓存行为

图片缓存目录为仓库/插件目录下的 `cache/`。

- 文件名：图片 URL 的 MD5 值，扩展名固定为 `.jpg`
- 读取缓存命中时直接返回 base64 图片
- 下载成功后写入缓存
- `initialize()` 会调用 `clear_cache()`
- 默认清理策略：
  - 超过 365 天的缓存会被删除
  - 缓存总大小超过 1000 MB 时，按修改时间从旧到新删除

## 本地开发命令

安装依赖：

```powershell
uv sync --locked --dev
```

人和 agent 不共享同一个 venv。用户可继续使用默认 `.venv`；agent 可在自己的 session 中设置 `UV_PROJECT_ENVIRONMENT` 指向本地忽略目录，例如 `.codex-venv`。依赖版本以 [uv.lock](uv.lock) 为准，不在项目配置中写死本地 venv 路径。

检查命令：

```powershell
uv run --locked --dev ruff check .
uv run --locked --dev ruff format --check .
uv run --locked --dev pyright
uv run --locked --dev python -m py_compile main.py core.py components/event_listener/default.py
```

当前仓库没有专门的测试脚本；修改后至少运行语法检查，涉及类型或风格时同步运行 Ruff 和 Pyright。

## 维护注意事项

- 保持 v4 结构：LangBot 接入层放在 [main.py](main.py) 和 `components/`，业务逻辑放在 [core.py](core.py)。
- 保持异步实现风格：网络请求使用 `httpx.AsyncClient`，阻塞文件 IO 通过 `asyncio.to_thread(...)` 包裹。
- 配置文件读写使用 UTF-8 和 `yaml.safe_load` / `yaml.dump(..., allow_unicode=True, sort_keys=False)`。
- 发送图片时使用 `langbot_plugin.api.entities.builtin.platform.message.Image`，并传入带 MIME 前缀的 base64 data URL。
- 变更用户指令匹配逻辑时，同步检查 README 中的使用说明和截图语义。
