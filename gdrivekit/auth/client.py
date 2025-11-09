"""OAuth2 client using Google's official libraries."""

import json
from pathlib import Path
import threading

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from .storage import TokenStorage


class OAuth2Client:
    """
    OAuth2 client using Google's official auth libraries.
    
    Tokens are stored securely in the system keychain and automatically refreshed.
    """

    def __init__(
        self,
        client_name: str,
        scopes: list[str],
        client_id: str,
        client_secret: str,
        redirect_uri: str | None = None
    ):
        """
        Initialize OAuth2 client.

        Args:
            client_name: Unique identifier (keychain entry name)
            scopes: List of Google API scopes
            client_id: OAuth2 client ID
            client_secret: OAuth2 client secret
            redirect_uri: Callback URI (default: http://localhost:8080)
        """
        if not all([client_name, scopes, client_id, client_secret]):
            raise ValueError('client_name, scopes, client_id, and client_secret required')

        self.client_name = client_name
        self.scopes = scopes
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri or 'http://localhost:8080'
        self.storage = TokenStorage(client_name)
        self._refresh_lock = threading.Lock()  # Thread-safe credential refresh

    def get_credentials(self) -> Credentials:
        """
        Get valid credentials (refreshes or re-authenticates if needed).

        Returns:
            Valid Google OAuth2 credentials
        """
        token_data = self.storage.get()
        creds = None

        # Try to load existing credentials
        if token_data:
            creds = Credentials(
                token=token_data.get('access_token'),
                refresh_token=token_data.get('refresh_token'),
                token_uri='https://oauth2.googleapis.com/token',
                client_id=self.client_id,
                client_secret=self.client_secret,
                scopes=self.scopes
            )

        # Refresh if expired (with thread-safe locking)
        if creds and creds.expired and creds.refresh_token:
            with self._refresh_lock:
                # Double-check after acquiring lock (another thread may have refreshed)
                if creds.expired:
                    creds.refresh(Request())
                    self._save_credentials(creds)
            return creds

        # Return if valid
        if creds and creds.valid:
            return creds

        # New authorization flow
        print(f'Authenticating: {self.client_name}')
        
        # Create client config from credentials
        client_config = {
            'installed': {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'auth_uri': 'https://accounts.google.com/o/oauth2/v2/auth',
                'token_uri': 'https://oauth2.googleapis.com/token',
                'redirect_uris': [self.redirect_uri]
            }
        }

        flow = InstalledAppFlow.from_client_config(client_config, self.scopes)
        
        # Run local server or console flow based on redirect_uri
        if self.redirect_uri == 'urn:ietf:wg:oauth:2.0:oob':
            creds = flow.run_console()
        else:
            # Parse port from redirect_uri
            port = 8080
            if ':' in self.redirect_uri:
                try:
                    port = int(self.redirect_uri.split(':')[-1].split('/')[0])
                except ValueError:
                    pass
            creds = flow.run_local_server(port=port, open_browser=True)

        self._save_credentials(creds)
        print(f'Authenticated: {self.client_name}')
        return creds

    def get_access_token(self) -> str:
        """
        Get valid access token.

        Returns:
            Valid access token string
        """
        return self.get_credentials().token

    def _save_credentials(self, creds: Credentials) -> None:
        """Save credentials to storage."""
        token_data = {
            'access_token': creds.token,
            'refresh_token': creds.refresh_token,
            'scopes': creds.scopes
        }
        self.storage.save(token_data)

    def delete(self) -> None:
        """Delete client and revoke tokens."""
        creds = self.get_credentials()
        if creds:
            creds.revoke(Request())
            print(f'Revoked: {self.client_name}')
        self.storage.delete()
        print(f'Deleted: {self.client_name}')


def create_client(
    client_name: str,
    scopes: list[str],
    client_id: str,
    client_secret: str,
    redirect_uri: str | None = None
) -> OAuth2Client:
    """
    Create OAuth2 client.

    Args:
        client_name: Unique identifier
        scopes: Google API scopes
        client_id: OAuth2 client ID
        client_secret: OAuth2 client secret
        redirect_uri: Callback URI (default: http://localhost:8080)
                     Also supports: urn:ietf:wg:oauth:2.0:oob

    Returns:
        OAuth2Client instance
    """
    return OAuth2Client(client_name, scopes, client_id, client_secret, redirect_uri)


def delete_client(client_name: str) -> None:
    """Delete client and revoke tokens."""
    storage = TokenStorage(client_name)
    token_data = storage.get()
    
    if token_data:
        # Reconstruct credentials to revoke
        try:
            creds = Credentials(
                token=token_data.get('access_token'),
                refresh_token=token_data.get('refresh_token'),
                token_uri='https://oauth2.googleapis.com/token'
            )
            creds.revoke(Request())
            print(f'Revoked: {client_name}')
        except Exception as e:
            print(f'Revoke failed: {e}')
    
    storage.delete()
    print(f'Deleted: {client_name}')
