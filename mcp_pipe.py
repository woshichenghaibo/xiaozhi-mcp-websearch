# mcp_pipe.py - 硬编码版MCP连接器
import asyncio
import websockets
import subprocess
import logging
import signal
import sys
import random

# 硬编码配置（直接修改这里！）
MCP_ENDPOINT = "wss://api.xiaozhi.me/mcp/?token=eyJhbGciOiJFUzI1N89sInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOjI5NzMzNywiYWdlbnRJZCI6MjkwOTgyLCJlbmRwb2ludElkIjoiYWdlbnRfMjkwOTgyIiwicHVycG9zZSI6Im1jcC1lbmRwb2ludCIsImlhdCI6MTc0OTM3ODY3N30.Gdrb75cZrDN4mmYdJSjSzH37Q32EoXavclGMrW4EQ0keIsShUZViz493FSZSwqG5FkiJeJtcrF8PkrTqDrz1lQ"  # 替换为你的真实token

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('MCP_PIPE')

async def pipe_websocket_to_process(websocket, process):
    """WebSocket → 子进程"""
    try:
        while True:
            message = await websocket.recv()
            if isinstance(message, bytes):
                message = message.decode('utf-8')
            process.stdin.write(message + '\n')
            process.stdin.flush()
    except Exception as e:
        logger.error(f"WebSocket读取失败: {e}")
        raise

async def pipe_process_to_websocket(process, websocket):
    """子进程 → WebSocket"""
    try:
        while True:
            line = await asyncio.get_event_loop().run_in_executor(
                None, process.stdout.readline
            )
            if not line:
                break
            await websocket.send(line)
    except Exception as e:
        logger.error(f"进程输出转发失败: {e}")
        raise

async def run_service():
    """主服务循环"""
    while True:
        try:
            async with websockets.connect(MCP_ENDPOINT) as ws:
                proc = subprocess.Popen(
                    ['python', 'websitesearch.py'],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=sys.stderr,
                    encoding='utf-8'
                )
                await asyncio.gather(
                    pipe_websocket_to_process(ws, proc),
                    pipe_process_to_websocket(proc, ws)
                )
        except Exception as e:
            wait = min(random.uniform(1, 10), 60)
            logger.warning(f"连接中断，{wait:.1f}秒后重试... 错误: {e}")
            await asyncio.sleep(wait)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda *_: sys.exit(0))
    
    if len(sys.argv) < 2:
        logger.error("用法: python mcp_pipe.py websitesearch.py")
        sys.exit(1)

    try:
        asyncio.run(run_service())
    except KeyboardInterrupt:
        logger.info("服务已停止")