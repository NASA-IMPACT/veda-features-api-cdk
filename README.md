# veda-features-api-cdk

This repo hosts both runtime and infrastructure for veda-features-api.

## Local Development

Run the docker-compose:

```
docker-compose up --build 
```

## Deployment

AWS CDK is used to deploy this API to AWS. You can use `cdk deploy --profile <aws_profile>` to deploy this to desired environment.
