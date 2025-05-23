"""Stack Configs."""

import base64
import json
from functools import lru_cache
from typing import Optional

import boto3
from pydantic_settings import BaseSettings


@lru_cache()
def get_secret_dict(secret_name: str):
    """Retrieve secrets from AWS Secrets Manager

    Args:
        secret_name (str): name of aws secrets manager secret containing database connection secrets
        profile_name (str, optional): optional name of aws profile for use in debugger only

    Returns:
        secrets (dict): decrypted secrets in dict
    """

    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(service_name="secretsmanager")

    get_secret_value_response = client.get_secret_value(SecretId=secret_name)

    if "SecretString" in get_secret_value_response:
        return json.loads(get_secret_value_response["SecretString"])
    else:
        return json.loads(base64.b64decode(get_secret_value_response["SecretBinary"]))


class FeaturesAPISettings(BaseSettings):
    """Application settings"""

    name: str = "veda-features-api"
    cors_origins: str = "*"
    cachecontrol: str = "public, max-age=3600"
    debug: bool = False
    # TODO: .env os env vars should be setting this correctly but currently are not
    root_path: Optional[str] = ""
    add_tiles_viewer: bool = True
    stage: str = ""

    catalog_ttl: int = 300  # seconds

    postgis_secret_arn: Optional[str] = None

    def load_postgres_settings(self):
        """Load Settings from Secret"""
        from tipg.settings import PostgresSettings  # noqa: F821

        if self.postgis_secret_arn:
            secret = get_secret_dict(self.postgis_secret_arn)
            return PostgresSettings(
                postgres_user=secret["username"],
                postgres_pass=secret["password"],
                postgres_host=secret["host"],
                postgres_port=int(secret["port"]),
                postgres_dbname=secret["dbname"],
            )
        else:
            return PostgresSettings()

    class Config:
        """model config"""

        env_file = ".env"
        env_prefix = "VEDA_FEATURES_"
