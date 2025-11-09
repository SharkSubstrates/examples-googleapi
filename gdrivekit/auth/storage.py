"""Secure token storage using system keychain."""

import json
import keyring


class TokenStorage:
    """Secure keychain storage for OAuth tokens."""

    def __init__(self, client_name: str):
        self.service_name = f'gcloud_oauth.{client_name}'

    def get(self) -> dict | None:
        """Retrieve stored tokens."""
        token_json = keyring.get_password(self.service_name, 'token_data')
        return json.loads(token_json) if token_json else None

    def save(self, token_data: dict) -> None:
        """Store tokens securely."""
        keyring.set_password(
            self.service_name,
            'token_data',
            json.dumps(token_data)
        )

    def delete(self) -> None:
        """Remove stored tokens."""
        try:
            keyring.delete_password(self.service_name, 'token_data')
        except keyring.errors.PasswordDeleteError:
            pass
