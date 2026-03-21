import asyncio
import argparse
from .storage import TDStorage
from .client import TDClient
from common import Config


async def main():
    parser = argparse.ArgumentParser(description="HVRT TD Client")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    init_parser = subparsers.add_parser("init", help="Initialize device")
    init_parser.add_argument("--device-id", required=True, help="Device ID")
    
    enroll_parser = subparsers.add_parser("enroll", help="Enroll with AG")
    enroll_parser.add_argument("--device-id", required=True, help="Device ID")
    enroll_parser.add_argument("--ag", default="http://127.0.0.1:8100", help="AG URL")
    enroll_parser.add_argument("--region", default="regionA", help="Region ID")
    
    access_parser = subparsers.add_parser("access", help="Access AG")
    access_parser.add_argument("--device-id", required=True, help="Device ID")
    access_parser.add_argument("--ag", default="http://127.0.0.1:8100", help="AG URL")
    
    roam_parser = subparsers.add_parser("roam", help="Roam to another AG")
    roam_parser.add_argument("--device-id", required=True, help="Device ID")
    roam_parser.add_argument("--ag", default="http://127.0.0.1:8200", help="Target AG URL")
    roam_parser.add_argument("--region", default="regionA", help="Region ID")
    
    args = parser.parse_args()
    
    storage = TDStorage()
    
    if args.command == "init":
        device_secret = f"secret_{args.device_id}"
        storage.save_device(args.device_id, device_secret)
        print(f"Device initialized: {args.device_id}")
        print(f"Device secret: {device_secret}")
    
    elif args.command == "enroll":
        client = TDClient(args.device_id, storage)
        result = await client.enroll(args.ag, args.region)
        print("Enrolled successfully!")
        print(f"RRT ID: {result['rrt']['rrt_id']}")
        print(f"SAT ID: {result['sat']['sat_id']}")
    
    elif args.command == "access":
        client = TDClient(args.device_id, storage)
        result = await client.access(args.ag)
        print(f"Result: {result['result']}")
        print(f"Reason: {result['reason']}")
        if 'session_id' in result:
            print(f"Session ID: {result['session_id']}")
    
    elif args.command == "roam":
        client = TDClient(args.device_id, storage)
        result = await client.roam(args.ag, args.region)
        print(f"Roam Result: {result['result']}")
        print(f"Reason: {result['reason']}")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())
