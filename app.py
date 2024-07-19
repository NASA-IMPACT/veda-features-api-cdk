from aws_cdk import (
    App, 
    Stack,
    Aspects,
    aws_iam
)
from constructs import Construct 

from config import veda_app_settings
from features_api.infrastructure.construct import FeaturesAPILambdaConstruct
from features_api_database.infrastructure.construct import FeaturesRdsConstruct
from permissions_boundary.infrastructure.construct import PermissionsBoundaryAspect
from network.infrastructure.construct import VpcConstruct
from domain.infrastructure.construct import DomainConstruct

app = App()

class VedaStack(Stack):
    """CDK stack for the veda-backend stack."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        """."""
        super().__init__(scope, construct_id, **kwargs)

        if veda_app_settings.permissions_boundary_policy_name:
            permissions_boundary_policy = (
                aws_iam.ManagedPolicy.from_managed_policy_name(
                    self,
                    "permissions-boundary",
                    veda_app_settings.permissions_boundary_policy_name,
                )
            )
            aws_iam.PermissionsBoundary.of(self).apply(permissions_boundary_policy)
            Aspects.of(self).add(PermissionsBoundaryAspect(permissions_boundary_policy))


veda_stack = VedaStack(
    app,
    f"{veda_app_settings.app_name}-{veda_app_settings.stage_name()}",
    env=veda_app_settings.cdk_env(),
)

if veda_app_settings.vpc_id:
    vpc = VpcConstruct(
        veda_stack,
        "network",
        vpc_id=veda_app_settings.vpc_id,
        stage=veda_app_settings.stage_name(),
    )
else:
    vpc = VpcConstruct(veda_stack, "network", stage=veda_app_settings.stage_name())



features_database = FeaturesRdsConstruct(
    app,
    "features-database",
    vpc=vpc.vpc,
    subnet_ids=veda_app_settings.subnet_ids,
    stage=veda_app_settings.stage_name(),
)

domain = DomainConstruct(veda_stack, "domain", stage=veda_app_settings.stage_name())


features_api = FeaturesAPILambdaConstruct(
    app,
    "features-api",
    stage=veda_app_settings.stage_name(),
    vpc=vpc.vpc,
    database=features_database,
    domain=domain,
)

app.synth()
