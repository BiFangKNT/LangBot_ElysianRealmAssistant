# typings

这个目录只放当前 v1 旧版 LangBot 插件入口需要的本地类型桩。

## 用途

- 让 Pyright 能识别由 LangBot 宿主环境提供的 `pkg.*` 导入。
- 消除单插件仓库中必然出现的旧 SDK 导入爆红。
- 给编辑器和类型检查器提供最小接口信息。

## 边界

- 这些 `.pyi` 文件不是运行时代码。
- 不要把它当作 LangBot SDK 的完整类型定义。
- 不要在迁移 v4 时继续扩展 `pkg.*` 类型桩。

迁移到 v4 后，应改用真实的 `langbot_plugin.api.*` SDK 类型，并删除这个 legacy stub 目录。
