"""Veda-backend database construct configuration."""

from aws_cdk import aws_ec2, aws_rds
from pydantic import Field, validator
from pydantic_settings import BaseSettings


class FeaturesDBSettings(BaseSettings):
    """Application settings."""

    dbname: str = Field(
        "postgis-features",
        description="Name of postgres database",
    )
    admin_user: str = Field(
        "postgres",
        description="Name of admin role for postgres database",
    )
    user: str = Field(
        "veda",
        description="Name of pgstac role for postgres database",
    )
    schema_version: str = Field(
        ...,
        description=("The version of the custom veda-features-api schema, i.e. 0.1.1",),
    )
    snapshot_id: str | None = Field(
        None,
        description=(
            "RDS snapshot identifier to initialize RDS from a snapshot. "
            "**Once used always REQUIRED**"
        ),
    )
    publicly_accessible: bool | None = Field(
        True, description="Boolean if the RDS should be publicly accessible"
    )
    # RDS custom postgres parameters
    max_locks_per_transaction: str | None = Field(
        "64",
        description="Number of database objects that can be locked simultaneously",
        pattern=r"^[1-9]\d*$",
    )
    work_mem: str | None = Field(
        "8192",
        description=(
            "Maximum amount of memory to be used by a query operation "
            "before writing to temporary disk files"
        ),
        pattern=r"^[1-9]\d*$",
    )
    max_connections: str | None = Field(
        "475",
        description="Maximum number of connections allowed",
        pattern=r"^[1-9]\d*$",
    )
    temp_buffers: str | None = Field(
        "32000",
        description="maximum number of temporary buffers used by each session",
        pattern=r"^[1-9]\d*$",
    )
    use_rds_proxy: bool | None = Field(
        False,
        description="Boolean if the RDS should be accessed through a proxy",
    )
    random_page_cost: str | None = Field(
        "1.1",
        description=(
            "Sets the estimate of the cost of a non-sequentially fetched disk page. "
            "This parameter has no value unless query plan management (QPM) is on. "
            "When QPM is on, the default value for this parameter is 4."
        ),
        pattern=r"^[1-9]\d*.[1-9]",
    )
    rds_instance_class: str | None = Field(
        aws_ec2.InstanceClass.BURSTABLE3.value,
        description=(
            "The instance class of the RDS instance "
            "https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_ec2/InstanceClass.html"
        ),
    )
    rds_instance_size: str | None = Field(
        aws_ec2.InstanceSize.LARGE.value,
        description=(
            "The size of the RDS instance "
            "https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_ec2/InstanceSize.html"
        ),
    )
    rds_engine_full_version: str | None = Field(
        aws_rds.PostgresEngineVersion.VER_14.postgres_full_version,
        description=(
            "The version of the RDS Postgres engine "
            "https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_rds/PostgresEngineVersion.html"
        ),
    )
    rds_engine_major_version: str | None = Field(
        aws_rds.PostgresEngineVersion.VER_14.postgres_major_version,
        description=(
            "The version of the RDS Postgres engine "
            "https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_rds/PostgresEngineVersion.html"
        ),
    )
    rds_encryption: bool | None = Field(
        False,
        description="Boolean if the RDS should be encrypted",
    )
    max_allocated_storage: int | None = Field(
        500,
        description="Upper limit to which RDS can scale the storage in GiB(Gibibyte)",
    )
    airflow_worker_security_groups: list[str] | None = Field(
        [],
        description="Security group IDs for airflow workers to access RDS",
    )

    @validator("rds_instance_class", pre=True, always=True)
    def convert_rds_class_to_uppercase(cls, value):
        """Convert to uppercase."""
        if isinstance(value, str):
            return value.upper()
        return value

    @validator("rds_instance_size", pre=True, always=True)
    def convert_rds_size_to_uppercase(cls, value):
        """Convert to uppercase."""
        if isinstance(value, str):
            return value.upper()
        return value

    class Config:
        """model config."""

        env_file = ".env"
        env_prefix = "VEDA_FEATURES_DB_"
        extra = "allow"


features_db_settings = FeaturesDBSettings()
