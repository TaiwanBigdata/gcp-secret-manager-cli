from google.cloud import secretmanager
from google.api_core import exceptions


class SecretManagerClient:
    """Secret Manager client class"""

    def __init__(self, project_id: str):
        """
        Initialize Secret Manager client

        Args:
            project_id (str): GCP project ID
        """
        self.project_id = project_id
        self.client = secretmanager.SecretManagerServiceClient()
        self.project_path = f"projects/{project_id}"

    def create_secret(self, secret_id: str) -> secretmanager.Secret:
        """
        Create a new secret

        Args:
            secret_id (str): Secret identifier (will be converted to lowercase)

        Returns:
            Secret: Created Secret object

        Raises:
            exceptions.AlreadyExists: Secret already exists
        """
        return self.client.create_secret(
            request={
                "parent": self.project_path,
                "secret_id": secret_id.lower(),
                "secret": {"replication": {"automatic": {}}},
            }
        )

    def add_secret_version(
        self, secret_path: str, payload: str
    ) -> secretmanager.SecretVersion:
        """
        Add a new secret version

        Args:
            secret_path (str): Secret path
            payload (str): Secret content

        Returns:
            SecretVersion: Newly created Secret version
        """
        return self.client.add_secret_version(
            request={
                "parent": secret_path,
                "payload": {"data": payload.encode()},
            }
        )

    def get_secret_version(
        self, name: str
    ) -> secretmanager.AccessSecretVersionResponse:
        """
        Access a specific secret version

        Args:
            name (str): Full path of the secret version

        Returns:
            secretmanager.AccessSecretVersionResponse: Response containing the secret version

        Raises:
            exceptions.NotFound: Secret not found
            exceptions.PermissionDenied: Permission denied
        """
        return self.client.access_secret_version(request={"name": name})

    def list_secrets(self, prefix: str = None):
        """
        List all secrets

        Args:
            prefix (str, optional): Secret name prefix (will be converted to lowercase)

        Returns:
            Iterator: Secret objects iterator
        """
        secrets = self.client.list_secrets(request={"parent": self.project_path})
        if prefix:
            prefix = prefix.lower()
            return filter(lambda x: x.name.split("/")[-1].startswith(prefix), secrets)
        return secrets

    def delete_secret(self, secret_path: str):
        """
        Delete a secret

        Args:
            secret_path (str): Secret path

        Raises:
            exceptions.NotFound: Secret not found
        """
        self.client.delete_secret(request={"name": secret_path})
