# AGENTS.md

本文件给 Codex 等agent提供仓库维护说明。

## 项目概览

这是一个 LangBot 插件，插件名为 `ElysianRealmAssistant`，用于响应崩坏3 往世乐土相关查询，返回推荐攻略、角色攻略图片或配置列表。

当前插件版本在 [main.py](main.py) 的 `@register(...)` 中声明为 `1.7.0`。

## 运行环境

- Python 版本要求：`>=3.10`
  - 依据：[pyproject.toml](pyproject.toml) 的 `requires-python = ">=3.10"`
- 包管理优先使用 `uv`
- 也保留 [requirements.txt](requirements.txt)，用于传统 `pip` 安装

核心依赖：

- `langbot-plugin`
- `PyYAML`
- `httpx`
- `regex`

注意：当前实现使用 `httpx.AsyncClient`，不是 `requests`。

## 主要文件

- [main.py](main.py)：插件主体逻辑，包含注册、消息处理、查询路由、网络请求、图片缓存、配置更新。
- [ElysianRealmConfig.yaml](ElysianRealmConfig.yaml)：角色攻略键与用户可输入别名的映射。
- [pyproject.toml](pyproject.toml)：项目元数据、Python 版本和依赖声明。
- [uv.lock](uv.lock)：`uv` 锁文件。
- [README.md](README.md)：面向用户的安装和使用说明。

## 插件入口与消息流程

插件通过 `@register(...)` 注册 `ElysianRealmAssistant` 类，并监听：

- `PersonNormalMessageReceived`
- `GroupNormalMessageReceived`

处理流程：

1. `initialize()` 加载 `ElysianRealmConfig.yaml`，并清理过期缓存。
2. `on_message()` 将私聊/群聊普通消息交给 `ElysianRealmAssistant(ctx)`。
3. 正则 `self.url_pattern` 判断是否为插件指令。
4. `convert_message()` 根据指令类型路由到对应处理函数。
5. 命中后通过 LangBot 消息链返回文本或图片，并调用 `prevent_default()` / `prevent_postorder()`。

## 支持的指令

正则入口定义在 `main.py` 的 `self.url_pattern`。当前支持：

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

- 根据 `ElysianRealmConfig.yaml` 匹配用户输入。
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
uv sync
```

虚拟环境协作：

- 不共享同一个 venv；user可用默认 `.venv`，agent用自己可写的本地环境。
- agent可设置 `UV_PROJECT_ENVIRONMENT` 指向本地忽略目录，例如 `.codex-venv`。
- 依赖版本以 `uv.lock` 为准，不在项目配置中写死本地 venv 路径。

运行语法检查：

```powershell
uv run python -m py_compile main.py
```

当前仓库没有发现专门的测试脚本；修改后至少运行语法检查。

## 维护注意事项

- 保持异步实现风格：网络请求使用 `httpx.AsyncClient`，阻塞文件 IO 通过 `asyncio.to_thread(...)` 包裹。
- 配置文件读写使用 UTF-8 和 `yaml.safe_load` / `yaml.dump(..., allow_unicode=True, sort_keys=False)`。
- 发送图片时当前实现使用 `platform_types.Image(base64=...)`。
- 变更用户指令匹配逻辑时，同步检查 README 中的使用说明和截图语义。
