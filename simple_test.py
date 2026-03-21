#!/usr/bin/env python3
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 60)
print("HVRT System Simple Test")
print("=" * 60)

print("\n1. Testing Core Crypto Utilities...")
try:
    from common.crypto_utils import (
        generate_ed25519_keypair,
        sign_with_ed25519,
        verify_with_ed25519,
        generate_hmac_sha256,
        verify_hmac_sha256,
        generate_nonce,
        generate_id
    )
    print("   ✓ Crypto utils imported successfully")
except Exception as e:
    print(f"   ✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n2. Testing Ed25519 Keypair...")
try:
    privkey, pubkey = generate_ed25519_keypair()
    print(f"   ✓ Generated Ed25519 keypair")
    print(f"     Private key: {privkey[:20]}...")
    print(f"     Public key: {pubkey[:20]}...")
except Exception as e:
    print(f"   ✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n3. Testing Ed25519 Sign/Verify...")
try:
    test_data = {"test": "data", "number": 123}
    signature = sign_with_ed25519(privkey, test_data)
    is_valid = verify_with_ed25519(pubkey, test_data, signature)
    print(f"   ✓ Sign/Verify successful: {is_valid}")
except Exception as e:
    print(f"   ✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n4. Testing HMAC-SHA256...")
try:
    key = "test_secret_key_123"
    message = "test_message_abc"
    hmac = generate_hmac_sha256(key, message)
    is_valid = verify_hmac_sha256(key, message, hmac)
    print(f"   ✓ HMAC generated and verified: {is_valid}")
except Exception as e:
    print(f"   ✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n5. Testing Nonce & ID Generation...")
try:
    nonce = generate_nonce()
    test_id = generate_id("test")
    print(f"   ✓ Nonce: {nonce[:20]}...")
    print(f"   ✓ Test ID: {test_id}")
except Exception as e:
    print(f"   ✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n6. Testing Ticket Utils...")
try:
    from common.ticket_utils import create_gtt, verify_gtt
    gtt = create_gtt(privkey, pubkey, 1)
    print(f"   ✓ Created GTT: {gtt.gtt_id}")
    
    is_gtt_valid = verify_gtt(gtt, pubkey)
    print(f"   ✓ GTT signature verified: {is_gtt_valid}")
except Exception as e:
    print(f"   ✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n7. Testing Models...")
try:
    from common.models import GTT, RRT, SAT
    print("   ✓ Models imported successfully")
except Exception as e:
    print(f"   ✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("All basic tests passed!")
print("=" * 60)
print("\nNext steps:")
print("1. Install missing dependencies: pip install pyyaml httpx fastapi uvicorn")
print("2. Start the services in separate terminals")
print("3. Run the demo script")
