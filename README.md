# 即梦AI绘图插件

这是一个基于即梦AI的绘图插件，可以通过简单的文本描述生成图片。

## 功能特点

- 支持通过文本描述生成图片
- 自动保存生成的图片
- 定期清理旧图片
- 支持清理所有图片

## 安装方法

1. 将插件文件夹复制到 dify-on-wechat 的 plugins 目录下
2. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```
3. 配置 config.json 文件：
   ```json
   {
       "auth_token": "<session-id>",
       "api_url": "http://<jimeng-free-api-ip>:8000/v1/images/generations",
       "drawing_prefixes": ["即梦", "jimeng"],
       "image_output_dir": "./plugins/jimeng/images",
       "clean_interval": 3,
       "clean_check_interval": 3600
   }
   ```

## 使用方法

1. 在聊天中使用以下前缀触发插件：
   - 即梦
   - jimeng

2. 直接输入描述文本即可生成图片，例如：
   ```
   即梦 可爱的熊猫漫画
   ```

3. 清理所有图片：
   ```
   即梦 clean_all
   ```

## 配置说明

- `auth_token`: 即梦AI的认证令牌
- `api_url`: API接口地址
- `drawing_prefixes`: 触发插件的前缀列表
- `image_output_dir`: 图片保存目录
- `clean_interval`: 图片清理间隔（天）
- `clean_check_interval`: 清理检查间隔（秒）

## 注意事项

1. 请确保有足够的磁盘空间存储生成的图片
2. 建议定期清理图片以节省空间
3. 请妥善保管认证令牌

## 更新日志

### v1.0.0
- 初始版本发布
- 支持基本的图片生成功能
- 支持图片自动清理 