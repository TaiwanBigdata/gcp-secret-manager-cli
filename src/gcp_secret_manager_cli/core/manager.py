from typing import Dict, List, Tuple, Optional
from google.cloud import secretmanager
from google.api_core import exceptions
from ..utils import console, env
from .client import SecretManagerClient


class SecretManager:
    """Secret Manager class"""

    def __init__(self, client: SecretManagerClient):
        """
        Initialize Secret Manager

        Args:
            client (SecretManagerClient): Secret Manager client
        """
        self.client = client

    def create_or_update_from_env(
        self, env_file: str, prefix: str = ""
    ) -> Tuple[Dict[str, int], List[Dict[str, str]]]:
        """
        Create or update secrets from environment file

        Args:
            env_file (str): Path to environment file
            prefix (str, optional): Secret name prefix

        Returns:
            Tuple[Dict[str, int], List[Dict[str, str]]]:
                (Operation stats, Operation results)
        """
        # Read environment variables
        with console.create_progress() as progress:
            task = progress.add_task("[blue]Reading .env file...", total=None)
            try:
                env_content = env.read_env_file(env_file)
            except FileNotFoundError as e:
                console.print_error(str(e))
                return {"error": 1}, []
            progress.update(
                task, completed=True, description="[green]File read complete"
            )

        if not env_content:
            console.print_warning("No environment variables found in file.")
            return {"empty": 1}, []

        # Handle prefix
        if prefix and not prefix.endswith("_"):
            prefix = f"{prefix}_"

        # Create or update secrets
        results = []
        stats = {"created": 0, "updated": 0, "error": 0}

        with console.create_progress() as progress:
            task = progress.add_task(
                "[blue]Processing secrets...", total=len(env_content)
            )

            for key, value in env_content.items():
                secret_id = f"{prefix}{key}".lower()
                progress.update(task, description=f"[blue]Processing: {secret_id}")

                try:
                    # Try to create secret
                    try:
                        secret = self.client.create_secret(secret_id)
                        secret_path = secret.name
                        status = "✅ Created"
                        stats["created"] += 1
                    except exceptions.AlreadyExists:
                        secret_path = f"{self.client.project_path}/secrets/{secret_id}"
                        status = "🔄 Updated"
                        stats["updated"] += 1

                    # Add version
                    self.client.add_secret_version(secret_path, value)
                    results.append({"name": secret_id, "status": status})

                except Exception as e:
                    stats["error"] += 1
                    results.append({"name": secret_id, "status": f"❌ Error: {str(e)}"})

                progress.advance(task)

            progress.update(task, description="[green]Processing complete")

        return stats, results

    def create_or_update_single(self, key: str, value: str) -> Dict[str, str]:
        """
        Create or update a single secret

        Args:
            key (str): Secret key
            value (str): Secret value

        Returns:
            Dict[str, str]: Operation result
        """
        try:
            key = key.lower()
            # Try to create secret
            try:
                secret = self.client.create_secret(key)
                secret_path = secret.name
                status = "✅ Created"
            except exceptions.AlreadyExists:
                secret_path = f"{self.client.project_path}/secrets/{key}"
                status = "🔄 Updated"

            # Add version
            self.client.add_secret_version(secret_path, value)
            return {"name": key, "status": status}

        except Exception as e:
            return {"name": key, "status": f"❌ Error: {str(e)}"}

    def delete_single(self, key: str) -> Dict[str, str]:
        """
        Delete a single secret

        Args:
            key (str): Secret key

        Returns:
            Dict[str, str]: Operation result
        """
        try:
            key = key.lower()
            secret_path = f"{self.client.project_path}/secrets/{key}"
            self.client.delete_secret(secret_path)
            return {"name": key, "status": "✅ Deleted"}
        except Exception as e:
            return {"name": key, "status": f"❌ Error: {str(e)}"}

    def list_secrets(
        self, prefix: Optional[str] = None
    ) -> Tuple[List[Dict[str, str]], int]:
        """
        List secrets

        Args:
            prefix (str, optional): Secret name prefix

        Returns:
            Tuple[List[Dict[str, str]], int]:
                (Secrets list, Total count)
        """
        with console.create_spinner_progress() as progress:
            task = progress.add_task("[blue]Fetching secrets...", total=None)
            secrets = list(self.client.list_secrets(prefix))
            count = len(secrets)
            progress.update(task, completed=True, description="[green]Fetch complete")

        return secrets, count

    def get_secret(self, secret_id: str) -> Optional[secretmanager.Secret]:
        """
        Get a single secret information

        Args:
            secret_id (str): Secret identifier

        Returns:
            Optional[secretmanager.Secret]: Secret object, returns None if not found
        """
        try:
            # Filter secrets using list_secrets first
            secrets = list(self.client.list_secrets())
            # Find the secret that exactly matches the name
            matching_secret = next(
                (s for s in secrets if s.name.split("/")[-1] == secret_id.lower()), None
            )
            return matching_secret
        except Exception:
            return None

    def get_secret_value(self, secret_id: str) -> Optional[str]:
        """
        Get the value of a secret

        Args:
            secret_id (str): Secret identifier (case insensitive)

        Returns:
            Optional[str]: Secret value, returns None if not found
        """
        try:
            # Convert to lowercase for processing
            secret_id = secret_id.lower()
            secret = self.get_secret(secret_id)
            if not secret:
                return None

            version = self.client.get_secret_version(
                name=f"{secret.name}/versions/latest"
            )
            return version.payload.data.decode("utf-8")
        except Exception:
            return None

    def delete_secrets(
        self, prefix: Optional[str] = None, force: bool = False
    ) -> Tuple[Dict[str, int], List[Dict[str, str]]]:
        """
        Delete secrets

        Args:
            prefix (str, optional): Secret name prefix
            force (bool, optional): Skip confirmation prompt

        Returns:
            Tuple[Dict[str, int], List[Dict[str, str]]]:
                (Operation stats, Operation results)
        """
        # Get secrets to delete
        with console.create_spinner_progress() as progress:
            task = progress.add_task("[blue]Fetching secrets...", total=None)
            secrets = list(self.client.list_secrets(prefix))
            progress.update(task, completed=True, description="[green]Fetch complete")

        if not secrets:
            console.print_warning("No secrets found to delete.")
            return {"not_found": 1}, []

        # Show secrets to be deleted
        table = console.Table(title="Secrets to be Deleted")
        table.add_column("Secret Name", style="red")
        for secret in secrets:
            table.add_row(secret.name.split("/")[-1])
        console.console.print(table)

        # Confirm deletion
        if not force and not console.confirm(
            f"Are you sure you want to delete these {len(secrets)} secrets?"
        ):
            console.print_warning("Operation cancelled.")
            return {"cancelled": 1}, []

        # Execute deletion
        results = []
        stats = {"success": 0, "error": 0, "total": len(secrets)}

        with console.create_progress() as progress:
            task = progress.add_task("[blue]Deleting secrets...", total=len(secrets))

            for secret in secrets:
                secret_name = secret.name.split("/")[-1]
                progress.update(task, description=f"[blue]Deleting: {secret_name}")

                try:
                    self.client.delete_secret(secret.name)
                    results.append({"name": secret_name, "status": "✅ Deleted"})
                    stats["success"] += 1
                except Exception as e:
                    results.append(
                        {"name": secret_name, "status": f"❌ Error: {str(e)}"}
                    )
                    stats["error"] += 1

                progress.advance(task)

            progress.update(task, description="[green]Deletion complete")

        return stats, results
