#!/usr/bin/env python3
"""
HVRT 真实网络服务 - 仅启动所有服务
"""
import subprocess
import sys
import os
import time
import signal

print("=" * 80)
print("  HVRT 真实网络服务 - 启动所有服务")
print("=" * 80)

processes = []

def cleanup():
    print("\n正在停止所有服务...")
    for p in processes:
        try:
            p.terminate()
            p.wait(timeout=5)
        except Exception as e:
            print(f"  停止进程失败: {e}")
            try:
                p.kill()
            except:
                pass
    print("所有服务已停止")

def main():
    try:
        base_path = os.path.dirname(os.path.abspath(__file__))
        venv_python = os.path.join(base_path, ".venv", "Scripts", "python.exe")
        
        print("\n正在启动 CTA (端口 8000)...")
        cta_proc = subprocess.Popen(
            [venv_python, "-m", "cta.main"],
            cwd=base_path
        )
        processes.append(cta_proc)
        
        print("正在启动 EC (端口 8050)...")
        ec_proc = subprocess.Popen(
            [venv_python, "-m", "ec.main"],
            cwd=base_path
        )
        processes.append(ec_proc)
        
        print("正在启动 AG1 (端口 8100)...")
        ag1_proc = subprocess.Popen(
            [venv_python, "-m", "ag.main", "--port", "8100"],
            cwd=base_path
        )
        processes.append(ag1_proc)
        
        print("\n服务已启动！")
        print("=" * 80)
        print("  服务地址：")
        print("  - CTA: http://127.0.0.1:8000")
        print("  - EC:  http://127.0.0.1:8050")
        print("  - AG1: http://127.0.0.1:8100")
        print("=" * 80)
        print("按 Ctrl+C 停止所有服务\n")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
            
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cleanup()

if __name__ == "__main__":
    main()
