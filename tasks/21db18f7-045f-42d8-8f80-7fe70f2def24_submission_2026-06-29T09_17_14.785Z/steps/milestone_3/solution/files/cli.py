"""CLI entry point for the Prefect block secret encryption tool."""

import json

import click

from aes_crypto import decrypt_secrets, generate_key
from block_stager import stage_block_from_path
from export_builder import build_encrypted_export
from export_validator import validate_export
from exceptions import IntegrityError
from integrity_seal import verify_integrity_seal
from rotator import rotate_keys as _rotate_keys


@click.group()
def cli() -> None:
    """Secure Prefect block configuration exports with AES-GCM encryption."""


@cli.command()
@click.argument("block_file")
@click.argument("output_file")
@click.argument("key_hex")
def encrypt(block_file: str, output_file: str, key_hex: str) -> None:
    key = bytes.fromhex(key_hex)
    staging_path = stage_block_from_path(block_file)
    count = build_encrypted_export(staging_path, key, output_file)
    click.echo(f"Encrypted {count} secret field(s) to {output_file}")


@cli.command()
@click.argument("export_file")
@click.argument("key_hex")
def decrypt(export_file: str, key_hex: str) -> None:
    try:
        key = bytes.fromhex(key_hex)
        with open(export_file) as f:
            export = json.load(f)
        validate_export(export)
        if not verify_integrity_seal(export, key):
            raise IntegrityError("Export integrity seal verification failed")
        block_type = export["metadata"]["block_type"]
        key_version = int(export["metadata"]["key_version"])
        decrypted = decrypt_secrets(export["secrets"], key, block_type, key_version)
        result = {**export["public"], **decrypted}
        click.echo(json.dumps(result, indent=2))
    except Exception as exc:
        raise click.ClickException(str(exc))


@cli.command()
@click.argument("export_file")
@click.argument("old_key_hex")
@click.argument("new_key_hex")
def rotate(export_file: str, old_key_hex: str, new_key_hex: str) -> None:
    try:
        old_key = bytes.fromhex(old_key_hex)
        new_key = bytes.fromhex(new_key_hex)
        _rotate_keys(export_file, old_key, new_key)
        click.echo(f"Key rotation complete for {export_file}")
    except Exception as exc:
        raise click.ClickException(str(exc))


@cli.command()
def keygen() -> None:
    key = generate_key()
    click.echo(key.hex())


if __name__ == "__main__":
    cli()
