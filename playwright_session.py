import sys
import asyncio
import json
from TikTokApi import TikTokApi

import traceback

async def get_user_info(api, username):
    """获取用户信息。"""
    user = api.user(username=username)
    user_info = await user.info()
    return user_info

async def get_user_videos(api, username):
    """获取用户视频。"""
    videos = []
    async for video in api.user(username=username).videos():
        video_info = video.as_dict
        videos.append(video_info)
    return videos

async def handle_commands():
    """处理来自父进程的命令。"""
    api = None

    try:
        # 使用上下文管理器管理 TikTokApi 实例
        async with TikTokApi() as api:
            await api.create_sessions(num_sessions=1, headless=True, sleep_after=5)

            while True:
                # 读取命令
                line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
                if not line:
                    print("EOF received. Exiting.", file=sys.stdout, flush=True)
                    break  # EOF

                line = line.strip()

                if not line:
                    continue

                try:
                    command = json.loads(line)
                    action = command.get("action")
                    username = command.get("username")

                    if action == "get_user_info":
                        user_info = await get_user_info(api, username)
                        response = {"status": "success", "data": user_info}
                    elif action == "get_user_videos":
                        user_videos = await get_user_videos(api, username)
                        response = {"status": "success", "data": user_videos}
                    else:
                        response = {"status": "error", "message": "Unknown action"}
                except json.JSONDecodeError as e:
                    response = {"status": "error", "message": "Invalid JSON format"}
                except Exception as e:
                    response = {"status": "error", "message": str(e)}

                # 发送响应
                response_str = json.dumps(response)
                sys.stdout.write(response_str + "\n")
                sys.stdout.flush()
    except Exception as e:
        print(f"Unhandled exception in handle_commands: {e}", file=sys.stderr, flush=True)
    finally:
        # 确保在任何情况下都关闭 TikTokApi
        if api:
            await api.close_sessions()

if __name__ == "__main__":
    try:
        asyncio.run(handle_commands())
    except Exception as e:
        print(f"Unhandled exception in main: {e}", file=sys.stdout, flush=True)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)