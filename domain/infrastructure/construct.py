"""CDK Construct for a custom API domain."""

from typing import Optional

from aws_cdk import (
    CfnOutput,
    aws_apigatewayv2_alpha,
    aws_certificatemanager,
    aws_route53,
    aws_route53_targets,
)
from constructs import Construct

from .config import veda_domain_settings


class DomainConstruct(Construct):
    """CDK Construct for a custom API domain."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        stage: str,
        alt_domain: Optional[bool] = False,
        **kwargs,
    ) -> None:
        """."""
        super().__init__(scope, construct_id, **kwargs)

        self.features_domain_name = None

        if veda_domain_settings.create_custom_subdomains:
            # If alternative custom domain provided, use it instead of the default
            if alt_domain is True:
                hosted_zone_name = veda_domain_settings.alt_hosted_zone_name
                hosted_zone_id = veda_domain_settings.alt_hosted_zone_id
            else:
                hosted_zone_name = veda_domain_settings.hosted_zone_name
                hosted_zone_id = veda_domain_settings.hosted_zone_id

            hosted_zone = aws_route53.HostedZone.from_hosted_zone_attributes(
                self,
                "hosted-zone",
                hosted_zone_id=hosted_zone_id,
                zone_name=hosted_zone_name,
            )
            certificate = aws_certificatemanager.Certificate(
                self,
                "certificate",
                domain_name=f"*.{hosted_zone_name}",
                validation=aws_certificatemanager.CertificateValidation.from_dns(
                    hosted_zone=hosted_zone
                ),
            )

            # Use custom api prefix if provided or deployment stage if not
            if veda_domain_settings.api_prefix:
                features_url_prefix = (
                    f"{veda_domain_settings.api_prefix.lower()}-features"
                )
            else:
                features_url_prefix = f"{stage.lower()}-features"

            features_domain_name = f"{features_url_prefix}.{hosted_zone_name}"

            self.features_domain_name = aws_apigatewayv2_alpha.DomainName(
                self,
                "featuresApiCustomDomain",
                domain_name=features_domain_name,
                certificate=certificate,
            )

            aws_route53.ARecord(
                self,
                "features-api-dns-record",
                zone=hosted_zone,
                target=aws_route53.RecordTarget.from_alias(
                    aws_route53_targets.ApiGatewayv2DomainProperties(
                        regional_domain_name=self.features_domain_name.regional_domain_name,
                        regional_hosted_zone_id=self.features_domain_name.regional_hosted_zone_id,
                    )
                ),
                # Note: CDK will append the hosted zone name (eg: `veda-backend.xyz` to this record name)
                record_name=features_url_prefix,
            )

            CfnOutput(
                self,
                "features-api",
                value=f"https://{features_url_prefix}.{hosted_zone_name}/",
            )
