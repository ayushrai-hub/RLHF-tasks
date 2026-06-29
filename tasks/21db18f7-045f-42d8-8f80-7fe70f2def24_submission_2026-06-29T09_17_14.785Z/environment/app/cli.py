"""CLI entry point for Prefect block sealed export tooling."""

import json
import sys

import click

from block_parser import extract_public_fields, extract_secret_fields, load_block


@click.group()
def cli() -> None:
    """Classify and seal Prefect block configuration exports."""


@cli.command()
@click.argument("block_file")
def inspect(block_file: str) -> None:
    """Print public vs secret field classification for a block YAML file."""
    block = load_block(block_file)
    public = extract_public_fields(block)
    secrets = extract_secret_fields(block)
    click.echo(
        json.dumps(
            {
                "public_paths": sorted(public.keys()),
                "secret_paths": sorted(secrets.keys()),
            },
            indent=2,
        )
    )


@cli.command()
@click.argument("block_file")
@click.argument("output_file")
@click.argument("key_hex")
def encrypt(block_file: str, output_file: str, key_hex: str) -> None:
    """Encrypt secrets in a Prefect block YAML and write a sealed export."""
    from block_stager import stage_block_from_path
    from export_builder import build_encrypted_export

    key = bytes.fromhex(key_hex)
    staging_path = stage_block_from_path(block_file)
    count = build_encrypted_export(staging_path, key, output_file)
    click.echo(f"Encrypted {count} secret field(s) to {output_file}")


if __name__ == "__main__":
    try:
        cli()
    except click.ClickException as exc:
        click.echo(str(exc), err=True)
        sys.exit(1)
