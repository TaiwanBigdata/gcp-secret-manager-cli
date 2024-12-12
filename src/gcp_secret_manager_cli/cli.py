import click
from click import Context
from typing import Optional
from google.api_core import exceptions
from .core.client import SecretManagerClient
from .core.manager import SecretManager
from .utils import console, env


class CustomGroup(click.Group):
    """Custom Click Group class"""

    def format_help(self, ctx, formatter):
        """Display custom help format"""
        console.console.print(
            f"\n🔐 [bold cyan]Secret Manager CLI Tool[/bold cyan]"
        )
        # Command examples with their descriptions
        EXAMPLES = [
            ("# If the .env file does not have PROJECT_ID configured.", ""),
            ("$ sm list -P PROJECT_ID", "Specify PROJECT_ID"),
            ("", ""),
            ("# Add secrets from file", ""),
            ("$ sm add -e", "Add from default .env file"),
            ("$ sm add -e .env.dev", "Add from specific env file"),
            (
                "$ sm add -e .env.dev -p DEV_",
                "Add from specific env file with prefix",
            ),
            ("", ""),
            ("# Add single secret", ""),
            ('$ sm add DB_URL "mysql://localhost"', "Add single secret"),
            ("", ""),
            ("# Remove secrets", ""),
            ("$ sm remove -e", "Remove from default .env file"),
            ("$ sm remove -e .env.dev", "Remove from specific env file"),
            ("$ sm remove -p DEV_", "Remove by prefix"),
            ("$ sm remove DB_URL", "Remove single secret"),
            (
                "$ sm rm -f -p TEST_",
                "Force remove by prefix without confirmation",
            ),
            ("", ""),
            ("# List secrets", ""),
            ("$ sm list", "List all secrets"),
            ("$ sm list -p DEV_", "List secrets with prefix"),
            ("$ sm ls -p TEST_", "List secrets with prefix (alias)"),
            (
                "$ sm rm -f -p TEST_",
                "Force remove by prefix without confirmation",
            ),
            ("", ""),
            ("# Get single secret", ""),
            ("$ sm get DB_URL", "Get value of specific secret"),
        ]

        # Show project info
        config = env.get_project_config()
        project_info = (
            f"🗂️  Project: {config.project_id} (from {config.source_path})\n"
            if config.project_id
            else (
                "⚠️  Project ID not set (requires PROJECT_ID in env)\n"
                f"   Required in: {config.source_path or '.env'}\n"
            )
        )
        console.console.print(project_info)

        # Show environment settings
        env_table = console.Table(show_header=False, box=None)
        env_table.add_column("Setting", style="cyan", no_wrap=True, width=20)
        env_table.add_column("Description", style="white", width=50)

        env_table.add_row(
            "PROJECT_ID", "GCP Project ID for Secret Manager operations"
        )
        env_table.add_row(
            "TZ", "Timezone for displaying timestamps (default: UTC)"
        )

        console.console.print("[bold]Environment Settings:[/bold]")
        console.console.print(env_table)

        # Command description
        command_table = console.Table(show_header=False, box=None)
        command_table.add_column(
            "Command", style="cyan", no_wrap=True, width=20
        )
        command_table.add_column("Description", style="white", width=50)

        command_table.add_row("add", "Add secrets from file or command line")
        command_table.add_row("remove (rm)", "Remove secrets by prefix or key")
        command_table.add_row("list (ls)", "List all secrets")
        command_table.add_row("get", "Get the value of a specific secret")

        console.console.print("[bold]Available Commands:[/bold]")
        console.console.print(command_table)

        # Usage examples
        example_table = console.Table(show_header=False, box=None)
        example_table.add_column(style="blue", no_wrap=True)

        for cmd, desc in EXAMPLES:
            if not cmd and not desc:
                example_table.add_row("")
            elif not desc:
                example_table.add_row(cmd)
            else:
                formatted_row = f"[grey50]{cmd:<40}# {desc}[/grey50]"
                example_table.add_row(formatted_row)

        console.console.print("\n[bold]Usage Examples:[/bold]")
        console.console.print(example_table)
        console.console.print()


@click.group(cls=CustomGroup)
@click.version_option(message="%(prog)s version %(version)s")
@click.option(
    "-P",
    "--project-id",
    help="GCP Project ID (reads from PROJECT_ID env if not provided)",
)
@click.pass_context
def cli(ctx: Context, project_id: Optional[str]):
    """Secret Manager CLI tool"""
    config = env.get_project_config()
    project_id = project_id or config.project_id
    if not project_id:
        console.print_error(
            "No project-id provided and PROJECT_ID not found in env!"
        )
        ctx.exit(1)

    client = SecretManagerClient(project_id)
    ctx.obj = SecretManager(client)


@cli.command()
@click.pass_obj
@click.pass_context
@click.option(
    "-e",
    "--env-file",
    type=click.STRING,
    is_flag=False,
    flag_value=".env",
    default=None,
    help="Use environment file (default: .env, or specify custom file path)",
)
@click.option(
    "-p",
    "--prefix",
    default="",
    help="Environment variable prefix (e.g., dev, prod)",
)
@click.argument("key", required=False)
@click.argument("value", required=False)
def add(
    ctx: Context,
    manager: SecretManager,
    env_file: Optional[str],
    prefix: str,
    key: Optional[str],
    value: Optional[str],
):
    """Add secrets from file or command line"""
    # Check parameter validity
    if not any([env_file, key]):
        console.print_error("Please specify one of the following methods:")
        console.console.print("  -e         : Use default .env file")
        console.console.print("  -e FILE    : Use specified environment file")
        console.console.print("  KEY VALUE  : Add single secret")
        ctx.exit(1)

    if key and not value:
        console.print_error(
            "Both KEY and VALUE are required when adding a single secret"
        )
        ctx.exit(1)

    try:
        if key and value:
            # Single secret mode
            console.console.print(
                f"\n[bold]Adding/Updating Single Secret:[/bold] {key}"
            )
            result = manager.create_or_update_single(key, value)
            console.show_operation_table([result])
        else:
            # Batch mode
            console.console.print(
                f"\n[bold]Batch Adding Secrets from File:[/bold] {env_file}"
            )
            if prefix:
                console.console.print(f"[bold]Using Prefix:[/bold] {prefix}")

            stats, results = manager.create_or_update_from_env(env_file, prefix)

            if results:
                console.console.print("\n[bold]Add/Update Results:[/bold]")
                console.show_operation_table(results)
                console.show_summary(
                    {
                        "✅ Successfully Added": stats.get("created", 0),
                        "🔄 Successfully Updated": stats.get("updated", 0),
                        "❌ Failed": stats.get("error", 0),
                    }
                )
            else:
                console.print_warning("No secrets found to add")

    except FileNotFoundError:
        console.print_error(f"Environment file not found: {env_file}")
        ctx.exit(1)
    except Exception as e:
        console.print_error(f"Error occurred during execution: {str(e)}")
        ctx.exit(1)


@cli.command()
@click.pass_obj
@click.pass_context
@click.option(
    "-e",
    "--env-file",
    type=click.STRING,
    is_flag=False,
    flag_value=".env",
    default=None,
    help="Remove secrets from environment file (default: .env, or specify custom file path)",
)
@click.option(
    "-p",
    "--prefix",
    type=click.STRING,
    is_flag=False,
    flag_value="",
    default=None,
    help="Remove secrets with specific prefix",
)
@click.option("-f", "--force", is_flag=True, help="Skip confirmation prompt")
@click.argument("key", required=False)
def remove(
    ctx: Context,
    manager: SecretManager,
    env_file: Optional[str],
    prefix: Optional[str],
    force: bool,
    key: Optional[str],
):
    """Remove secrets by prefix or key"""
    # Check parameter validity
    if not any([env_file, prefix is not None, key]):
        console.print_error("Please specify one of the following methods:")
        console.console.print(
            "  -e          : Remove secrets from default .env file"
        )
        console.console.print(
            "  -e FILE     : Remove secrets from specified environment file"
        )
        console.console.print(
            "  -p [PREFIX] : Remove secrets with specified prefix"
        )
        console.console.print("  -f          : Force remove, skip confirmation")
        console.console.print("  KEY         : Remove single secret")
        ctx.exit(1)

    try:
        if env_file:
            # Environment file removal mode
            console.console.print(
                f"\n[bold]Removing Secrets from File:[/bold] {env_file}"
            )

            try:
                # Read keys from environment file
                env_vars = env.read_env_file(env_file)
                if not env_vars:
                    console.print_warning(
                        f"No keys found in environment file {env_file}"
                    )
                    ctx.exit(0)

                # Get existing data for these keys in Secret Manager
                existing_secrets = []
                for key in env_vars.keys():
                    secret = manager.get_secret(key)
                    if secret:
                        existing_secrets.append(secret)

                if not existing_secrets:
                    console.print_warning(
                        "No keys from environment file exist in Secret Manager"
                    )
                    ctx.exit(0)

                # Display secrets to be deleted
                timezone = env.get_timezone()
                console.console.print(
                    "\n[bold]The following secrets will be deleted:[/bold]"
                )
                table = console.Table(title="Secrets to be Deleted")
                table.add_column("Secret Name", style="red")
                for secret in existing_secrets:
                    table.add_row(secret.name.split("/")[-1])
                console.console.print(table)

                # Confirm deletion
                if not force:
                    if not click.confirm(
                        "\nAre you sure you want to delete these secrets?"
                    ):
                        console.print_warning("Operation cancelled")
                        ctx.exit(0)

                # Execute deletion
                results = []
                for key in env_vars.keys():
                    if manager.get_secret(key):
                        result = manager.delete_single(key)
                        results.append(result)

                # Show results
                console.console.print("\n[bold]Deletion Results:[/bold]")
                console.show_operation_table(results)
                success_count = len(
                    [r for r in results if r["status"] == "✅ Deleted"]
                )
                error_count = len(
                    [r for r in results if "❌ Error" in r["status"]]
                )
                console.show_summary(
                    {
                        "✅ Successfully Deleted": success_count,
                        "❌ Failed to Delete": error_count,
                    }
                )

            except FileNotFoundError:
                console.print_error(f"Environment file not found: {env_file}")
                ctx.exit(1)

        elif prefix is not None:
            # Prefix batch removal mode
            if prefix == "":
                console.console.print(
                    "\n[bold red]⚠️  Warning: Preparing to remove all secrets[/bold red]"
                )
            else:
                console.console.print(
                    f"\n[bold]Preparing to remove all secrets with prefix '{prefix}'[/bold]"
                )

            # List secrets to be deleted
            secrets, count = manager.list_secrets(prefix)
            if count == 0:
                console.print_warning(
                    f"No matching secrets found{f' (prefix: {prefix})' if prefix else ''}"
                )
                ctx.exit(0)

            # Display secrets to be deleted
            timezone = env.get_timezone()
            console.console.print(
                "\n[bold]The following secrets will be deleted:[/bold]"
            )
            table = console.Table(title="Secrets to be Deleted")
            table.add_column("Secret Name", style="red")
            for secret in secrets:
                table.add_row(secret.name.split("/")[-1])
            console.console.print(table)

            # Confirm deletion
            if not force:
                if not click.confirm(
                    "\nAre you sure you want to delete these secrets?"
                ):
                    console.print_warning("Operation cancelled")
                    ctx.exit(0)

            # Execute deletion
            stats, results = manager.delete_secrets(
                prefix, force=True
            )  # Force is True because we already confirmed
            if results:
                console.console.print("\n[bold]Deletion Results:[/bold]")
                console.show_operation_table(results)
                success_count = stats.get("success", 0)
                error_count = stats.get("error", 0)
                console.show_summary(
                    {
                        "✅ Successfully Deleted": success_count,
                        "❌ Failed to Delete": error_count,
                    }
                )
        else:
            # Single secret removal mode
            console.console.print(
                f"\n[bold]Removing Single Secret:[/bold] {key}"
            )

            # Check if secret exists
            secret = manager.get_secret(key)
            if not secret:
                console.print_error(f"Secret not found: {key}")
                ctx.exit(1)

            # Display secret information to be deleted
            timezone = env.get_timezone()
            console.console.print(
                "\n[bold]The following secret will be deleted:[/bold]"
            )
            table = console.Table(title="Secret to be Deleted")
            table.add_column("Secret Name", style="red")
            table.add_row(secret.name.split("/")[-1])
            console.console.print(table)

            # Confirm deletion
            if not force and not click.confirm(
                "\nAre you sure you want to delete this secret?"
            ):
                console.print_warning("Operation cancelled")
                ctx.exit(0)

            # Execute deletion
            result = manager.delete_single(key)
            console.show_operation_table([result])
            success_count = 1 if result["status"] == "✅ Deleted" else 0
            error_count = 1 if "❌ Error" in result["status"] else 0
            console.show_summary(
                {
                    "✅ Successfully Deleted": success_count,
                    "❌ Failed to Delete": error_count,
                }
            )

    except Exception as e:
        console.print_error(f"Error occurred during execution: {str(e)}")
        ctx.exit(1)


@cli.command()
@click.pass_obj
@click.option("-p", "--prefix", help="List secrets with specific prefix only")
def list(manager: SecretManager, prefix: Optional[str]):
    """List secrets"""
    secrets, count = manager.list_secrets(prefix)

    if count == 0:
        console.print_warning("No secrets found.")
    else:
        timezone = env.get_timezone()
        console.show_secrets_table(secrets, timezone)
        console.console.print(f"\nTotal secrets: {count}")


@cli.command()
@click.argument("key")
@click.option("-P", "--project-id", help="Override PROJECT_ID")
def get(key: str, project_id: Optional[str] = None):
    """Get the value of a specific secret"""
    try:
        # Get project_id
        config = env.get_project_config()
        project_id = project_id or config.project_id
        if not project_id:
            console.print_error("PROJECT_ID is required")
            return

        # Create client and manager
        client = SecretManagerClient(project_id)
        manager = SecretManager(client)

        # Get secret value
        with console.create_spinner_progress() as progress:
            task = progress.add_task(
                "[blue]Getting secret value...", total=None
            )
            result = manager.get_secret_value(key)
            progress.update(task, completed=True)

        if result:
            # Display result in table format
            table = console.Table(show_header=True)
            table.add_column("Key", style="cyan")
            table.add_column("Value", style="green")
            table.add_row(key, result)
            console.console.print(table)
        else:
            console.print_error(f"Secret not found: {key}")

    except exceptions.PermissionDenied:
        console.print_error("Permission denied to access this secret")
    except Exception as e:
        console.print_error(f"Error occurred: {str(e)}")


# Add command aliases
cli.add_command(list, name="ls")
cli.add_command(remove, name="rm")
