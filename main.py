import asyncio
from typing import Optional
from pkg.plugin.context import register, handler, llm_func, BasePlugin, APIHost, EventContext
from pkg.plugin.events import *  # 导入事件类
import pkg.platform.types as platform_types
import yaml
import regex as re
import os
import httpx
import time
import base64
import hashlib


# 注册插件
@register(name="ElysianRealmAssistant", description="崩坏3往世乐土攻略助手", version="1.7.0", author="BiFangKNT")
class ElysianRealmAssistant(BasePlugin):
    # 插件加载时触发
    def __init__(self, host: APIHost):
        super().__init__(host)
        self.config = {}

        self.url_pattern = re.compile(
            r"""
            ^(?:
                ((.{0,5})乐土list) |                        # 匹配0-5个字符后跟"乐土list"
                (乐土推荐\d{0,2}) |                         # 匹配"乐土推荐"后跟0-2个数字
                (全部乐土推荐) |                              # 匹配"全部乐土推荐"
                (?P<角色乐土>(.{1,5})乐土\d?) |             # 匹配1-5个字符后跟"乐土"，可选择性地跟随一个数字
                (?P<角色流派>(.{1,5})(\p{Han}{2})流) |  # 匹配1-5个字符，后跟任意两个中文字符和"流"
                (?P<添加命令>RealmCommand\s+add\s+(\w+)\s+([^,]+(?:,[^,]+)*))  # 匹配添加命令
            )$
            """,
            re.VERBOSE | re.UNICODE,
        )

    # 异步初始化
    async def initialize(self):
        self.config = await self.load_config()
        await self.clear_cache()  # 清理缓存

    @handler(PersonNormalMessageReceived)
    @handler(GroupNormalMessageReceived)
    async def on_message(self, ctx: EventContext):
        await self.ElysianRealmAssistant(ctx)

    async def load_config(self):
        plugin_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(plugin_dir, "ElysianRealmConfig.yaml")

        def _load() -> dict:
            try:
                with open(config_path, encoding="utf-8") as file:
                    return yaml.safe_load(file) or {}
            except FileNotFoundError:
                self.ap.logger.info(f"配置文件未找到: {config_path}")
                return {}
            except yaml.YAMLError as e:
                self.ap.logger.info(f"解析YAML文件时出错: {e}")
                return {}
            except Exception as e:
                self.ap.logger.info(f"加载配置文件时发生未知错误: {e}")
                return {}

        return await asyncio.to_thread(_load)

    async def ElysianRealmAssistant(self, ctx: EventContext):

        msg = ctx.event.text_message

        # 输出信息
        self.ap.logger.info(f"乐土攻略助手正在处理消息: {msg}")

        # 如果正则表达式没有匹配成功，直接终止脚本执行
        if not self.url_pattern.search(msg):
            self.ap.logger.info("乐土攻略助手：格式不匹配，不进行处理")
            return

        optimized_message = await self.convert_message(msg, ctx)

        if optimized_message:
            # 输出信息
            self.ap.logger.debug(f"处理后的消息: {optimized_message}")  # 注意：使用base64的话，此项输出会非常长

            # 添加重试逻辑
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    ctx.add_return("reply", optimized_message)
                    self.ap.logger.info("消息已成功添加到返回队列")
                    break
                except Exception as e:
                    if attempt < max_retries - 1:
                        self.ap.logger.info(f"发送消息失败，正在重试 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
                        await asyncio.sleep(1)  # 等待1秒后重试
                    else:
                        self.ap.logger.info(f"发送消息失败，已达到最大重试次数: {str(e)}")

            # 阻止该事件默认行为
            ctx.prevent_default()

            # 阻止后续插件执行
            ctx.prevent_postorder()
        else:
            self.ap.logger.info("消息处理后为空，不进行回复")

    async def convert_message(self, message, ctx):
        # 统一的回复逻辑
        await ctx.reply(
            platform_types.MessageChain([platform_types.Plain(f"已收到指令：{message}\n正在为您查询攻略……")])
        )

        # 检查是否是添加命令
        match = self.url_pattern.search(message)
        if match and match.group("添加命令"):
            return await self.handle_add_command(match.group("添加命令"))

        if message == "乐土list":
            return [platform_types.Plain(yaml.dump(self.config, allow_unicode=True))]

        if message == "全部乐土推荐":
            return await self.handle_recommendation(ctx, True)

        if "乐土推荐" in message:
            sequence = int(message.split("乐土推荐")[1] or 1)
            return await self.handle_recommendation(ctx, False, sequence)

        if "乐土list" in message:
            return self.handle_list_query(message)

        # 其他情况
        return await self.handle_normal_query(message, ctx)

    async def handle_recommendation(self, ctx, is_all=False, sequence=1):
        """
        处理乐土推荐攻略请求
        从米游社用户文章中获取最新的往世乐土推荐内容
        """
        url = "https://bbs-api.miyoushe.com/post/wapi/userPost?uid=5625196"

        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Connection": "keep-alive",
            }

            async with httpx.AsyncClient(headers=headers, timeout=10.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()

                posts = data.get("data", {}).get("list", [])

                pattern = r"往世乐土丨V\d+\.\d+[一二三四五六七八九十]+期推荐角色BUFF表"

                elysian_posts = []
                for post_item in posts:
                    post = post_item.get("post", {})
                    subject = post.get("subject", "")
                    if re.search(pattern, subject):
                        elysian_posts.append(post_item)

                posts = elysian_posts
                if posts:
                    images = posts[0].get("post", {}).get("images", [])
                    subject = posts[0].get("post", {}).get("subject", "")
                    reply_time = posts[0].get("post", {}).get("reply_time", "")

                    if len(images) > 1:
                        for idx, img_url in enumerate(images):
                            url_md5 = hashlib.md5(img_url.encode()).hexdigest()
                            self.ap.logger.info(f"预缓存第 {idx + 1}/{len(images)} 张图片: {url_md5}")
                            await self.get_image(img_url, ctx, client=client, preload=True)

                        if 1 <= sequence < len(images):
                            image_url = images[sequence]
                            image_data = await self.get_image(image_url, ctx, client=client)
                            if image_data and isinstance(image_data, platform_types.Image):
                                if is_all:
                                    image_urls = images[2:]
                                    return [
                                        platform_types.Plain(
                                            f"标题：{subject}\n更新时间：{reply_time}\n本期乐土推荐为：\n"
                                        ),
                                        image_data,
                                        platform_types.Plain("\n" + "\n".join(image_urls)),
                                    ]
                                else:
                                    return [
                                        platform_types.Plain(
                                            f"标题：{subject}\n更新时间：{reply_time}\n本期乐土推荐为：\n"
                                        ),
                                        image_data,
                                    ]
                        else:
                            self.ap.logger.info(f"序号超出范围，序号为：{sequence}")
                            return [platform_types.Plain(f"序号超出范围，请输入1至{len(images) - 1}之间的序号。")]

        except Exception as e:
            self.ap.logger.info(f"获取推荐攻略时发生错误: {str(e)}")
            return [platform_types.Plain("获取推荐攻略失败。")]

    def handle_list_query(self, message):
        query = message.replace("乐土list", "").strip()
        matched_pairs = {}
        for key, values in self.config.items():
            if any(query in value for value in values):  # 检查是否在任何一个值中
                self.ap.logger.info(f"找到匹配: {key}: {values}")
                matched_pairs[key] = values

        if matched_pairs:
            return [platform_types.Plain(yaml.dump(matched_pairs, allow_unicode=True))]
        return [platform_types.Plain("未找到相关的乐土list信息。")]

    async def handle_normal_query(self, message, ctx):
        for key, values in self.config.items():
            if message in values:
                image_url = f"https://raw.githubusercontent.com/BiFangKNT/ElysianRealm-Data/refs/heads/master/{key}.jpg"
                image_data = await self.get_image(image_url, ctx)
                if image_data and isinstance(image_data, platform_types.Image):
                    return [platform_types.Plain("已为您找到攻略：\n"), image_data]
        return [platform_types.Plain("未找到相关的乐土攻略。")]

    async def get_image(self, url, ctx, client: httpx.AsyncClient | None = None, preload: bool = False):
        start_time = time.time()

        def _read_file_bytes(path: str) -> bytes:
            with open(path, "rb") as file:
                return file.read()

        def _write_file_bytes(path: str, data: bytes) -> None:
            with open(path, "wb") as file:
                file.write(data)

        try:
            url_md5 = hashlib.md5(url.encode()).hexdigest()

            plugin_dir = os.path.dirname(os.path.abspath(__file__))
            cache_dir = os.path.join(plugin_dir, "cache")
            await asyncio.to_thread(lambda: os.makedirs(cache_dir, exist_ok=True))
            cache_path = os.path.join(cache_dir, f"{url_md5}.jpg")

            cache_exists = await asyncio.to_thread(os.path.exists, cache_path)
            if cache_exists:
                cache_start = time.time()
                self.ap.logger.info(f"使用缓存图片: {url_md5}")
                image_data = await asyncio.to_thread(_read_file_bytes, cache_path)
                cache_time = time.time() - cache_start
                self.ap.logger.info(f"缓存读取用时: {cache_time:.2f}秒")

                if preload:
                    return True
                return platform_types.Image(base64=base64.b64encode(image_data).decode("utf-8"))

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
                "Connection": "keep-alive",
            }

            async def _download_image(active_client: httpx.AsyncClient):
                dns_start = time.time()
                response = await active_client.get(url)
                dns_time = time.time() - dns_start

                self.ap.logger.debug(f"DNS解析用时: {dns_time:.2f}秒")
                self.ap.logger.debug(f"响应状态: {response.status_code}")

                if response.status_code == 200:
                    content = response.content
                    size_mb = len(content) / (1024 * 1024)
                    download_time = max(time.time() - dns_start, 1e-6)
                    self.ap.logger.debug(f"图片大小: {size_mb:.2f}MB")
                    self.ap.logger.debug(f"下载用时: {download_time:.2f}秒")
                    self.ap.logger.debug(f"下载速度: {size_mb / download_time:.2f}MB/s")

                    save_start = time.time()
                    await asyncio.to_thread(_write_file_bytes, cache_path, content)
                    save_time = time.time() - save_start
                    self.ap.logger.debug(f"缓存保存用时: {save_time:.2f}秒")

                    total_time = time.time() - start_time
                    self.ap.logger.debug(f"总处理用时: {total_time:.2f}秒")

                    if preload:
                        return True
                    return platform_types.Image(base64=base64.b64encode(content).decode("utf-8"))

                self.ap.logger.info(f"下载图片失败，状态码: {response.status_code}")
                if not preload:
                    await ctx.reply(
                        platform_types.MessageChain(
                            [platform_types.Plain(f"图片下载失败，状态码: {response.status_code}")]
                        )
                    )
                return False if preload else None

            if client is None:
                self.ap.logger.info("未传入客户端，创建新的 AsyncClient")
                async with httpx.AsyncClient(headers=headers, timeout=10.0) as new_client:
                    return await _download_image(new_client)
            else:
                self.ap.logger.info("使用传入的 AsyncClient")
                return await _download_image(client)

        except Exception as e:
            total_time = time.time() - start_time
            self.ap.logger.info(f"获取图片时发生错误: {str(e)}")
            self.ap.logger.info(f"失败用时: {total_time:.2f}秒")
            return False if preload else None

    async def clear_cache(self, max_age_days=365, max_size_mb=1000):
        """清理缓存文件
        Args:
            max_age_days: 最大保留天数
            max_size_mb: 缓存文件夹最大容量(MB)
        """

        def _clear():
            cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")
            if not os.path.exists(cache_dir):
                return

            current_time = time.time()
            for filename in os.listdir(cache_dir):
                filepath = os.path.join(cache_dir, filename)
                if os.path.getmtime(filepath) < current_time - (max_age_days * 86400):
                    try:
                        os.remove(filepath)
                        self.ap.logger.info(f"已删除过期缓存文件: {filepath}")
                    except Exception as e:
                        self.ap.logger.info(f"删除缓存文件失败: {str(e)}")

            total_size = sum(os.path.getsize(os.path.join(cache_dir, f)) for f in os.listdir(cache_dir)) / (1024 * 1024)

            if total_size > max_size_mb:
                files = [
                    (os.path.join(cache_dir, f), os.path.getmtime(os.path.join(cache_dir, f)))
                    for f in os.listdir(cache_dir)
                ]
                files.sort(key=lambda x: x[1])

                for filepath, _ in files:
                    if total_size <= max_size_mb:
                        break
                    try:
                        file_size = os.path.getsize(filepath) / (1024 * 1024)
                        os.remove(filepath)
                        total_size -= file_size
                        self.ap.logger.info(f"因空间限制删除缓存文件: {filepath}")
                    except Exception as e:
                        self.ap.logger.info(f"删除缓存文件失败: {str(e)}")

        await asyncio.to_thread(_clear)

    # 添加新的处理函数
    async def handle_add_command(self, command):
        try:
            # 解析命令
            _, _, key, values = command.split(None, 3)
            value_list = [v.strip() for v in values.split(",")]

            # 读取当前配置
            plugin_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(plugin_dir, "ElysianRealmConfig.yaml")

            def _read_config() -> dict:
                if not os.path.exists(config_path):
                    return {}
                with open(config_path, encoding="utf-8") as file:
                    return yaml.safe_load(file) or {}

            config = await asyncio.to_thread(_read_config)

            # 更新或添加键值对
            if key in config:
                # 添加新值到现有列表，避免重复
                config[key].extend(v for v in value_list if v not in config[key])
            else:
                # 创建新的键值对
                config[key] = value_list

            # 写回文件
            def _write_config(data: dict) -> None:
                with open(config_path, "w", encoding="utf-8") as file:
                    yaml.dump(data, file, allow_unicode=True, sort_keys=False)

            await asyncio.to_thread(_write_config, config)

            # 重新加载配置
            self.config = config

            # 返回更新后的键值对
            if key in config:
                return [platform_types.Plain(f"已成功添加/更新配置：\n{key}:\n  - " + "\n  - ".join(config[key]))]
            else:
                return [platform_types.Plain("添加配置失败。")]

        except Exception as e:
            self.ap.logger.info(f"添加配置时发生错误: {str(e)}")
            return [platform_types.Plain(f"添加配置失败: {str(e)}")]

    # 插件卸载时触发
    def __del__(self):
        pass
