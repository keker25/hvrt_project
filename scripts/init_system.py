import asyncio
import httpx
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def init_system():
    print("Initializing HVRT System...")
    
    print("\n1. Waiting for CTA to be ready...")
    try:
        async with httpx.AsyncClient() as client:
            for i in range(10):
                try:
                    response = await client.get("http://127.0.0.1:8000/")
                    if response.status_code == 200:
                        print("   ✓ CTA is ready")
                        break
                except:
                    await asyncio.sleep(1)
            else:
                print("   ✗ CTA is not responding")
                return
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return
    
    print("\n2. Waiting for EC to be ready...")
    try:
        async with httpx.AsyncClient() as client:
            for i in range(10):
                try:
                    response = await client.get("http://127.0.0.1:8050/")
                    if response.status_code == 200:
                        print("   ✓ EC is ready")
                        break
                except:
                    await asyncio.sleep(1)
            else:
                print("   ✗ EC is not responding")
                return
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return
    
    print("\n3. Waiting for AG1 to be ready...")
    try:
        async with httpx.AsyncClient() as client:
            for i in range(10):
                try:
                    response = await client.get("http://127.0.0.1:8100/")
                    if response.status_code == 200:
                        print("   ✓ AG1 is ready")
                        break
                except:
                    await asyncio.sleep(1)
            else:
                print("   ✗ AG1 is not responding")
                return
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return
    
    print("\n4. Waiting for AG2 to be ready...")
    try:
        async with httpx.AsyncClient() as client:
            for i in range(10):
                try:
                    response = await client.get("http://127.0.0.1:8200/")
                    if response.status_code == 200:
                        print("   ✓ AG2 is ready")
                        break
                except:
                    await asyncio.sleep(1)
            else:
                print("   ✗ AG2 is not responding")
                return
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return
    
    print("\n✓ System initialization complete!")


if __name__ == "__main__":
    asyncio.run(init_system())
