import asyncio
import base64
import hashlib
import os
import time
from collections.abc import Sequence
from typing import Any, Protocol

import httpx
import regex as re
import yaml
from langbot_plugin.api.entities.builtin.platform import message as platform_message

MessagePart = platform_message.Plain | platform_message.Image
MessageParts = Sequence[MessagePart]


class LoggerProtocol(Protocol):
    def debug(self, message: object, *args: object, **kwargs: object) -> None: ...
    def info(self, message: object, *args: object, **kwargs: object) -> None: ...


class ElysianRealmAssistantCore:
    def __init__(self, logger: LoggerProtocol) -> None:
        self.logger = logger
        self.realm_config: dict[str, list[str]] = {}
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

    async def initialize(self) -> None:
        self.realm_config = await self.load_config()
        await self.clear_cache()

    async def load_config(self) -> dict[str, list[str]]:
        config_path = self.get_config_path()

        def _load() -> dict[str, list[str]]:
            try:
                with open(config_path, encoding="utf-8") as file:
                    return yaml.safe_load(file) or {}
            except FileNotFoundError:
                self.logger.info(f"配置文件未找到: {config_path}")
                return {}
            except yaml.YAMLError as e:
                self.logger.info(f"解析YAML文件时出错: {e}")
                return {}
            except Exception as e:
                self.logger.info(f"加载配置文件时发生未知错误: {e}")
                return {}

        return await asyncio.to_thread(_load)

    async def handle_message(self, message: str, ctx: Any) -> bool:
        self.logger.info(f"乐土攻略助手正在处理消息: {message}")

        if not self.url_pattern.search(message):
            self.logger.info("乐土攻略助手：格式不匹配，不进行处理")
            return False

        await ctx.reply(platform_message.MessageChain([plain(f"已收到指令：{message}\n正在为您查询攻略……")]))
        optimized_message = await self.convert_message(message, ctx)

        if optimized_message:
            self.logger.debug(f"处理后的消息: {optimized_message}")

            max_retries = 3
            for attempt in range(max_retries):
                try:
                    await ctx.reply(platform_message.MessageChain(list(optimized_message)))
                    self.logger.info("消息已成功添加到返回队列")
                    break
                except Exception as e:
                    if attempt < max_retries - 1:
                        self.logger.info(f"发送消息失败，正在重试 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
                        await asyncio.sleep(1)
                    else:
                        self.logger.info(f"发送消息失败，已达到最大重试次数: {str(e)}")

            ctx.prevent_default()
            ctx.prevent_postorder()
        else:
            self.logger.info("消息处理后为空，不进行回复")

        return True

    async def convert_message(self, message: str, ctx: Any) -> MessageParts | None:
        match = self.url_pattern.search(message)
        if match and match.group("添加命令"):
            return await self.handle_add_command(match.group("添加命令"))

        if message == "乐土list":
            return [plain(yaml.dump(self.realm_config, allow_unicode=True))]

        if message == "全部乐土推荐":
            return await self.handle_recommendation(ctx, True)

        if "乐土推荐" in message:
            sequence = int(message.split("乐土推荐")[1] or 1)
            return await self.handle_recommendation(ctx, False, sequence)

        if "乐土list" in message:
            return self.handle_list_query(message)

        return await self.handle_normal_query(message, ctx)

    async def handle_recommendation(self, ctx: Any, is_all: bool = False, sequence: int = 1) -> MessageParts | None:
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
                            self.logger.info(f"预缓存第 {idx + 1}/{len(images)} 张图片: {url_md5}")
                            await self.get_image(img_url, ctx, client=client, preload=True)

                        if 1 <= sequence < len(images):
                            image_url = images[sequence]
                            image_data = await self.get_image(image_url, ctx, client=client)
                            if image_data and isinstance(image_data, platform_message.Image):
                                if is_all:
                                    image_urls = images[2:]
                                    return [
                                        plain(f"标题：{subject}\n更新时间：{reply_time}\n本期乐土推荐为：\n"),
                                        image_data,
                                        plain("\n" + "\n".join(image_urls)),
                                    ]
                                return [
                                    plain(f"标题：{subject}\n更新时间：{reply_time}\n本期乐土推荐为：\n"),
                                    image_data,
                                ]
                        else:
                            self.logger.info(f"序号超出范围，序号为：{sequence}")
                            return [plain(f"序号超出范围，请输入1至{len(images) - 1}之间的序号。")]

        except Exception as e:
            self.logger.info(f"获取推荐攻略时发生错误: {str(e)}")
            return [plain("获取推荐攻略失败。")]

        return None

    def handle_list_query(self, message: str) -> MessageParts:
        query = message.replace("乐土list", "").strip()
        matched_pairs = {}
        for key, values in self.realm_config.items():
            if any(query in value for value in values):
                self.logger.info(f"找到匹配: {key}: {values}")
                matched_pairs[key] = values

        if matched_pairs:
            return [plain(yaml.dump(matched_pairs, allow_unicode=True))]
        return [plain("未找到相关的乐土list信息。")]

    async def handle_normal_query(self, message: str, ctx: Any) -> MessageParts:
        for key, values in self.realm_config.items():
            if message in values:
                image_url = f"https://raw.githubusercontent.com/BiFangKNT/ElysianRealm-Data/refs/heads/master/{key}.jpg"
                image_data = await self.get_image(image_url, ctx)
                if image_data and isinstance(image_data, platform_message.Image):
                    return [plain("已为您找到攻略：\n"), image_data]
        return [plain("未找到相关的乐土攻略。")]

    async def get_image(
        self,
        url: str,
        ctx: Any,
        client: httpx.AsyncClient | None = None,
        preload: bool = False,
    ) -> platform_message.Image | bool | None:
        start_time = time.time()

        def _read_file_bytes(path: str) -> bytes:
            with open(path, "rb") as file:
                return file.read()

        def _write_file_bytes(path: str, data: bytes) -> None:
            with open(path, "wb") as file:
                file.write(data)

        try:
            url_md5 = hashlib.md5(url.encode()).hexdigest()

            cache_dir = self.get_cache_dir()
            await asyncio.to_thread(lambda: os.makedirs(cache_dir, exist_ok=True))
            cache_path = os.path.join(cache_dir, f"{url_md5}.jpg")

            cache_exists = await asyncio.to_thread(os.path.exists, cache_path)
            if cache_exists:
                cache_start = time.time()
                self.logger.info(f"使用缓存图片: {url_md5}")
                image_data = await asyncio.to_thread(_read_file_bytes, cache_path)
                cache_time = time.time() - cache_start
                self.logger.info(f"缓存读取用时: {cache_time:.2f}秒")

                if preload:
                    return True
                return image_from_bytes(image_data)

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
                "Connection": "keep-alive",
            }

            async def _download_image(active_client: httpx.AsyncClient) -> platform_message.Image | bool | None:
                dns_start = time.time()
                response = await active_client.get(url)
                dns_time = time.time() - dns_start

                self.logger.debug(f"DNS解析用时: {dns_time:.2f}秒")
                self.logger.debug(f"响应状态: {response.status_code}")

                if response.status_code == 200:
                    content = response.content
                    size_mb = len(content) / (1024 * 1024)
                    download_time = max(time.time() - dns_start, 1e-6)
                    self.logger.debug(f"图片大小: {size_mb:.2f}MB")
                    self.logger.debug(f"下载用时: {download_time:.2f}秒")
                    self.logger.debug(f"下载速度: {size_mb / download_time:.2f}MB/s")

                    save_start = time.time()
                    await asyncio.to_thread(_write_file_bytes, cache_path, content)
                    save_time = time.time() - save_start
                    self.logger.debug(f"缓存保存用时: {save_time:.2f}秒")

                    total_time = time.time() - start_time
                    self.logger.debug(f"总处理用时: {total_time:.2f}秒")

                    if preload:
                        return True
                    return image_from_bytes(content)

                self.logger.info(f"下载图片失败，状态码: {response.status_code}")
                if not preload:
                    await ctx.reply(
                        platform_message.MessageChain([plain(f"图片下载失败，状态码: {response.status_code}")])
                    )
                return False if preload else None

            if client is None:
                self.logger.info("未传入客户端，创建新的 AsyncClient")
                async with httpx.AsyncClient(headers=headers, timeout=10.0) as new_client:
                    return await _download_image(new_client)

            self.logger.info("使用传入的 AsyncClient")
            return await _download_image(client)

        except Exception as e:
            total_time = time.time() - start_time
            self.logger.info(f"获取图片时发生错误: {str(e)}")
            self.logger.info(f"失败用时: {total_time:.2f}秒")
            return False if preload else None

    async def clear_cache(self, max_age_days: int = 365, max_size_mb: int = 1000) -> None:
        def _clear() -> None:
            cache_dir = self.get_cache_dir()
            if not os.path.exists(cache_dir):
                return

            current_time = time.time()
            for filename in os.listdir(cache_dir):
                filepath = os.path.join(cache_dir, filename)
                if os.path.getmtime(filepath) < current_time - (max_age_days * 86400):
                    try:
                        os.remove(filepath)
                        self.logger.info(f"已删除过期缓存文件: {filepath}")
                    except Exception as e:
                        self.logger.info(f"删除缓存文件失败: {str(e)}")

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
                        self.logger.info(f"因空间限制删除缓存文件: {filepath}")
                    except Exception as e:
                        self.logger.info(f"删除缓存文件失败: {str(e)}")

        await asyncio.to_thread(_clear)

    async def handle_add_command(self, command: str) -> MessageParts:
        try:
            _, _, key, values = command.split(None, 3)
            value_list = [v.strip() for v in values.split(",")]
            config_path = self.get_config_path()

            def _read_config() -> dict[str, list[str]]:
                if not os.path.exists(config_path):
                    return {}
                with open(config_path, encoding="utf-8") as file:
                    return yaml.safe_load(file) or {}

            config = await asyncio.to_thread(_read_config)

            if key in config:
                config[key].extend(v for v in value_list if v not in config[key])
            else:
                config[key] = value_list

            def _write_config(data: dict[str, list[str]]) -> None:
                with open(config_path, "w", encoding="utf-8") as file:
                    yaml.dump(data, file, allow_unicode=True, sort_keys=False)

            await asyncio.to_thread(_write_config, config)

            self.realm_config = config

            if key in config:
                return [plain(f"已成功添加/更新配置：\n{key}:\n  - " + "\n  - ".join(config[key]))]
            return [plain("添加配置失败。")]

        except Exception as e:
            self.logger.info(f"添加配置时发生错误: {str(e)}")
            return [plain(f"添加配置失败: {str(e)}")]

    @staticmethod
    def get_plugin_dir() -> str:
        return os.path.dirname(os.path.abspath(__file__))

    def get_config_path(self) -> str:
        return os.path.join(self.get_plugin_dir(), "ElysianRealmConfig.yaml")

    def get_cache_dir(self) -> str:
        return os.path.join(self.get_plugin_dir(), "cache")


def plain(text: str) -> platform_message.Plain:
    return platform_message.Plain(text=text)


def image_from_bytes(data: bytes) -> platform_message.Image:
    encoded = base64.b64encode(data).decode("utf-8")
    # LangBot's aiocqhttp adapter adds the `base64://` prefix itself.
    return platform_message.Image(base64=encoded)
