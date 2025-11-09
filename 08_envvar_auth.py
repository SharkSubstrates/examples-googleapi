"""
Example: Environment Variable Token Storage

This example demonstrates how to:
- Use EnvVarStorage for token storage (headless systems)
- Store tokens as individual env vars (GOOGLEAPI_ACCESS_TOKEN, GOOGLEAPI_REFRESH_TOKEN)
- Skip keyring dependency for containerized environments
- Perfect for Docker, Kubernetes, CI/CD pipelines

Best for:
- Docker containers
- Kubernetes deployments
- CI/CD pipelines
- Headless servers without keychain support

How it works:
- EnvVarStorage stores OAuth tokens as individual environment variables
- With prefix 'GOOGLEAPI', you only need: GOOGLEAPI_ACCESS_TOKEN and GOOGLEAPI_REFRESH_TOKEN
- Works for ANY Google API (Drive, Docs, Sheets, Slides, etc.)
- CLIENT_ID, CLIENT_SECRET, SCOPES are defined separately (no need to duplicate)
- TOKEN_URI is hardcoded in Google's OAuth library
"""
import os
from pathlib import Path
from dotenv import load_dotenv

from googleapi_oauth import OAuth2Client
from secretstore import EnvVarStorage
from googleapi_drive import DriveClient


def example_envvar_storage():
    """
    Use EnvVarStorage for authentication.
    
    EnvVarStorage stores tokens in environment variables with a prefix.
    Perfect for containerized deployments where keyring is not available.
    """
    print("\n=== ENVIRONMENT VARIABLE STORAGE ===")
    print("Using EnvVarStorage for token management...")
    print()
    
    client_id = os.getenv('CLIENT_ID')
    client_secret = os.getenv('CLIENT_SECRET')
    scopes = os.getenv('CLIENT_SCOPES', '').split(',')
    
    if not all([client_id, client_secret]):
        print("✗ Missing CLIENT_ID or CLIENT_SECRET environment variables")
        return
    
    try:
        # Use EnvVarStorage with a prefix
        # This will store tokens as individual env vars:
        #   GOOGLEAPI_ACCESS_TOKEN, GOOGLEAPI_REFRESH_TOKEN
        auth = OAuth2Client(
            client_id=client_id,
            client_secret=client_secret,
            scopes=scopes,
            storage=EnvVarStorage(prefix='GOOGLEAPI')
        )
        
        # Create Drive client
        drive = DriveClient(auth)
        
        print("✓ Authenticated successfully with EnvVarStorage!")
        print(f"  User: {drive.get_user_info()['name']}")
        print(f"  Drives: {len(drive.drives)}")
        
        # After authentication, tokens are stored in individual env vars
        print("\n✓ Tokens stored in environment variables:")
        token = os.getenv('GOOGLEAPI_ACCESS_TOKEN', 'not set')
        refresh = os.getenv('GOOGLEAPI_REFRESH_TOKEN', 'not set')
        print(f"  GOOGLEAPI_ACCESS_TOKEN: {token[:40] if token != 'not set' else 'not set'}...")
        print(f"  GOOGLEAPI_REFRESH_TOKEN: {refresh[:40] if refresh != 'not set' else 'not set'}...")
        
        print("\n💡 To persist for future runs, add these to your .env file:")
        print("  GOOGLEAPI_ACCESS_TOKEN=ya29.a0...")
        print("  GOOGLEAPI_REFRESH_TOKEN=1//0g...")
        print("\n  That's it! You don't need CLIENT_ID, CLIENT_SECRET, or SCOPES in env vars.")
        print("  Those are already in your .env file and used during OAuth setup.")
        
    except Exception as e:
        print(f"✗ Error: {e}")


def example_multiple_instances():
    """
    Use different prefixes for multiple Google accounts.
    """
    print("\n=== MULTIPLE INSTANCES ===")
    print("Using different prefixes for multiple accounts...")
    print()
    
    # Instance 1: Main account (GOOGLEAPI_ prefix)
    print("Instance 1: Main account (GOOGLEAPI_*)")
    print("  Looks for: GOOGLEAPI_ACCESS_TOKEN, GOOGLEAPI_REFRESH_TOKEN")
    
    # Instance 2: Secondary account (GOOGLEAPI2_ prefix)
    print("Instance 2: Secondary account (GOOGLEAPI2_*)")
    print("  Looks for: GOOGLEAPI2_ACCESS_TOKEN, GOOGLEAPI2_REFRESH_TOKEN")
    
    print("\nThis allows you to manage multiple Google accounts in the same environment.")
    print("Just use different prefixes when creating OAuth2Client instances.")


def check_env_vars():
    """Check if required environment variables are set."""
    print("\n=== CHECKING ENVIRONMENT VARIABLES ===")
    
    required_vars = ['CLIENT_ID', 'CLIENT_SECRET', 'CLIENT_SCOPES']
    optional_vars = ['GOOGLEAPI_ACCESS_TOKEN', 'GOOGLEAPI_REFRESH_TOKEN']
    
    print("Required:")
    for var in required_vars:
        value = os.getenv(var)
        if value:
            display_value = value[:15] + '...' if len(value) > 15 else value
            print(f"  ✓ {var}: {display_value}")
        else:
            print(f"  ✗ {var}: NOT SET")
    
    print("\nOptional (persist tokens after first OAuth flow):")
    for var in optional_vars:
        value = os.getenv(var)
        if value:
            display_value = value[:30] + '...' if len(value) > 30 else value
            print(f"  ✓ {var}: {display_value}")
        else:
            print(f"  ⊙ {var}: not set (will trigger OAuth flow)")
    
    print("\n💡 TIPS:")
    print("  • On first run, EnvVarStorage will authenticate via OAuth flow")
    print("  • Only 2 env vars needed: GOOGLEAPI_ACCESS_TOKEN and GOOGLEAPI_REFRESH_TOKEN")
    print("  • Add them to .env or export to persist across sessions")
    print("  • Perfect for Docker/K8s - just inject these 2 environment variables")


if __name__ == "__main__":
    # Load environment variables from .env file
    load_dotenv()
    
    print("="*80)
    print("ENVIRONMENT VARIABLE TOKEN STORAGE EXAMPLE")
    print("="*80)
    print()
    print("This example shows how to use EnvVarStorage for auth,")
    print("perfect for containerized/headless environments.")
    print()
    print("Key benefits:")
    print("  • No keyring/keychain dependency")
    print("  • Works in Docker, K8s, CI/CD")
    print("  • Simple token management")
    print("  • Multiple account support via prefixes")
    
    # Check env vars
    check_env_vars()
    
    # Run examples
    print("\n" + "="*80)
    print("RUNNING EXAMPLES")
    print("="*80)
    
    example_envvar_storage()
    example_multiple_instances()
    
    print("\n" + "="*80)
    print("CONTAINERIZED DEPLOYMENT")
    print("="*80)
    print()
    print("For Docker/K8s deployments:")
    print("  1. Set CLIENT_ID, CLIENT_SECRET, CLIENT_SCOPES as env vars")
    print("  2. On first run, complete OAuth flow (or inject pre-authed tokens)")
    print("  3. Extract GOOGLEAPI_ACCESS_TOKEN and GOOGLEAPI_REFRESH_TOKEN")
    print("  4. Inject these as secrets/env vars in your deployment")
    print()
    print("Example Dockerfile:")
    print("  ENV CLIENT_ID=your_client_id")
    print("  ENV CLIENT_SECRET=your_client_secret")
    print("  ENV CLIENT_SCOPES=https://www.googleapis.com/auth/drive")
    print("  ENV GOOGLEAPI_ACCESS_TOKEN=ya29.a0...")
    print("  ENV GOOGLEAPI_REFRESH_TOKEN=1//0g...")
    
    print("\n" + "="*80)
    print("EXAMPLE COMPLETE")
    print("="*80)
