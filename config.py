from typing_extensions import Annotated
from pydantic import Field, StringConstraints
from pydantic_settings import BaseSettings

from typing import Optional, List 

AwsSubnetId=Annotated[str, StringConstraints(pattern=r"^subnet-[a-z0-9]{17}$")]

class vedaAppSettings(BaseSettings):
    """Application settings."""

    # App name and deployment stage
    app_name: Optional[str] = Field(
        "veda-features-api",
        description="Optional app name used to name stack and resources",
    )
    
    stage: str = Field(
        ...,
        description=(
            "Deployment stage used to name stack and resources, "
            "i.e. `dev`, `staging`, `prod`"
        ),
    )
    
    cdk_default_account: Optional[str] = Field(
        None,
        description="When deploying from a local machine the AWS account id is required to deploy to an exiting VPC",
    )
    cdk_default_region: Optional[str] = Field(
        None,
        description="When deploying from a local machine the AWS region id is required to deploy to an exiting VPC",
    )
    
    vpc_id: Optional[str] = Field(
        None,
        description=(
            "Resource identifier of VPC, if none a new VPC with public and private "
            "subnets will be provisioned."
        ),
    )
    
    permissions_boundary_policy_name: Optional[str] = Field(
        None,
        description="Name of IAM policy to define stack permissions boundary",
    )
    
    subnet_ids: Optional[List[AwsSubnetId]] = Field(  # type: ignore
        [],
        description="The subnet ids of subnets associated with the VPC to be used for the database and lambda function.",
    )
    
    def cdk_env(self) -> dict:
        """Load a cdk environment dict for stack"""

        if self.vpc_id:
            return {
                "account": self.cdk_default_account,
                "region": self.cdk_default_region,
            }
        else:
            return {}
        
    def stage_name(self) -> str:
        """Force lowercase stage name"""
        return self.stage.lower()
        
    class Config:
        """model config."""

        env_file = ".env"
        extra = "allow"
        
veda_app_settings = vedaAppSettings()
    
    
    
    