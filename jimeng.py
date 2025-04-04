import os
import re
import json
import time
import requests
from io import BytesIO
from typing import List, Tuple
from pathvalidate import sanitize_filename
from PIL import Image
from datetime import datetime, timedelta
import threading

import plugins
from bridge.context import ContextType
from bridge.reply import Reply, ReplyType
from common.log import logger
from plugins import *
from config import conf


@plugins.register(
    name="Jimeng",
    desire_priority=90,
    hidden=False,
    desc="A plugin for generating images using Jimeng AI.",
    version="1.0.0",
    author="Coda",
)
class Jimeng(Plugin):
    def __init__(self):
        super().__init__()
        try:
            conf = super().load_config()
            if not conf:
                raise Exception("配置未找到。")

            self.auth_token = conf.get("auth_token")
            if not self.auth_token:
                raise Exception("在配置中未找到认证令牌。")

            self.api_url = conf.get("api_url") or "http://<jimeng-free-api-ip>:8000/v1/images/generations"
            self.drawing_prefixes = conf.get("drawing_prefixes", ["即梦", "jimeng"])
            self.image_output_dir = conf.get("image_output_dir", "./plugins/jimeng/images")
            self.clean_interval = float(conf.get("clean_interval", 3))  # 天数
            self.clean_check_interval = int(conf.get("clean_check_interval", 3600))  # 秒数，默认1小时
            self.max_images = int(conf.get("max_images", 1))  # 最大输出图片数量

            if not os.path.exists(self.image_output_dir):
                os.makedirs(self.image_output_dir)

            self.handlers[Event.ON_HANDLE_CONTEXT] = self.on_handle_context

            # 启动定时清理任务
            self.schedule_next_run()

            logger.info(f"[Jimeng] 初始化成功，清理间隔设置为 {self.clean_interval} 天，检查间隔为 {self.clean_check_interval} 秒，最大输出图片数量为 {self.max_images}")
        except Exception as e:
            logger.error(f"[Jimeng] 初始化失败，错误：{e}")
            raise e

    def schedule_next_run(self):
        """安排下一次运行"""
        self.timer = threading.Timer(self.clean_check_interval, self.run_clean_task)
        self.timer.start()

    def run_clean_task(self):
        """运行清理任务并安排下一次运行"""
        self.clean_old_images()
        self.schedule_next_run()

    def on_handle_context(self, e_context: EventContext):
        if e_context["context"].type != ContextType.TEXT:
            return

        content = e_context["context"].content
        if not content.startswith(tuple(self.drawing_prefixes)):
            return

        logger.debug(f"[Jimeng] 收到消息: {content}")

        try:
            # 移除前缀
            for prefix in self.drawing_prefixes:
                if content.startswith(prefix):
                    content = content[len(prefix):].strip()
                    break

            if content.lower() == "clean_all":
                reply = self.clean_all_images()
            else:
                image_urls = self.generate_image(content)
                logger.debug(f"[Jimeng] 生成的图片URLs: {image_urls}")

                if image_urls:
                    replies = []
                    for url in image_urls:
                        image_path = self.download_and_save_image(url)
                        logger.debug(f"[Jimeng] 图片已保存到: {image_path}")

                        with open(image_path, 'rb') as f:
                            image_storage = BytesIO(f.read())
                        replies.append(Reply(ReplyType.IMAGE, image_storage))

                    if len(replies) == 1:
                        reply = replies[0]
                    else:
                        reply = Reply(ReplyType.TEXT, f"已生成 {len(replies)} 张图片：")
                        reply.replies = replies
                else:
                    logger.error("[Jimeng] 生成图片失败")
                    reply = Reply(ReplyType.ERROR, "生成图片失败。")

            e_context["reply"] = reply
            e_context.action = EventAction.BREAK_PASS
        except Exception as e:
            logger.error(f"[Jimeng] 发生错误: {e}")
            reply = Reply(ReplyType.ERROR, f"发生错误: {str(e)}")
            e_context["reply"] = reply
            e_context.action = EventAction.BREAK_PASS

    def generate_image(self, prompt: str) -> List[str]:
        try:
            payload = {
                "model": "jimeng-2.1",
                "prompt": prompt,
                "negativePrompt": "",
                "width": 1024,
                "height": 1024,
                "sample_strength": 0.5
            }

            headers = {
                'Authorization': f'Bearer {self.auth_token}',
                'Content-Type': 'application/json'
            }

            response = requests.post(self.api_url, headers=headers, json=payload)
            response.raise_for_status()
            json_response = response.json()

            if 'data' in json_response and len(json_response['data']) > 0:
                # 返回指定数量的图片URL
                return [item['url'] for item in json_response['data'][:self.max_images]]
            else:
                raise Exception("API返回数据格式错误")

        except requests.exceptions.RequestException as e:
            logger.error(f"[Jimeng] API请求失败: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"[Jimeng] API响应内容: {e.response.text}")
            raise Exception(f"API请求失败: {str(e)}")

    def download_and_save_image(self, image_url: str) -> str:
        try:
            response = requests.get(image_url)
            response.raise_for_status()

            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"jimeng_{timestamp}.jpg"
            safe_filename = sanitize_filename(filename)
            filepath = os.path.join(self.image_output_dir, safe_filename)

            # 保存图片
            with open(filepath, 'wb') as f:
                f.write(response.content)

            return filepath
        except Exception as e:
            logger.error(f"[Jimeng] 下载或保存图片失败: {e}")
            raise e

    def clean_all_images(self):
        """清理所有图片"""
        try:
            for filename in os.listdir(self.image_output_dir):
                filepath = os.path.join(self.image_output_dir, filename)
                if os.path.isfile(filepath):
                    os.remove(filepath)
            logger.info("[Jimeng] 已清理所有图片")
            return Reply(ReplyType.TEXT, "已清理所有图片。")
        except Exception as e:
            logger.error(f"[Jimeng] 清理图片失败: {e}")
            return Reply(ReplyType.ERROR, f"清理图片失败: {str(e)}")

    def clean_old_images(self):
        """清理旧图片"""
        try:
            now = datetime.now()
            for filename in os.listdir(self.image_output_dir):
                filepath = os.path.join(self.image_output_dir, filename)
                if os.path.isfile(filepath):
                    file_time = datetime.fromtimestamp(os.path.getctime(filepath))
                    if now - file_time > timedelta(days=self.clean_interval):
                        os.remove(filepath)
                        logger.debug(f"[Jimeng] 已删除旧图片: {filename}")
        except Exception as e:
            logger.error(f"[Jimeng] 清理旧图片失败: {e}")

    def get_help_text(self, verbose=False, **kwargs):
        help_text = "即梦AI绘图插件使用说明：\n"
        help_text += "1. 使用前缀触发：即梦 或 jimeng\n"
        help_text += "2. 直接输入描述文本即可生成图片\n"
        help_text += "3. 输入 clean_all 可以清理所有生成的图片\n"
        help_text += "4. 可在配置文件中设置 max_images 控制输出图片数量\n"
        help_text += "示例：\n"
        help_text += "即梦 可爱的熊猫漫画\n"
        return help_text