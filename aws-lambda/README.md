# Fast API AWS Lambda

## Setup

- **Build Image**:

```sh
IMAGE=fast-api-aws-lambda
docker build --platform linux/amd64 -t $IMAGE:latest .
```

- **Login into AWS ECR**:

```sh
# Get AWS_ACCOUNT and AWS_REGION. Both will be used in future commands
AWS_ACCOUNT=$(aws sts get-caller-identity --query 'Account' --output text)
AWS_REGION=$(aws ec2 describe-availability-zones --query 'AvailabilityZones[0].RegionName' --output text)

# login AWS ECR
echo $(aws ecr get-login-password --region $AWS_REGION) | docker login --username AWS --password-stdin $AWS_ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com
```

- **Create a repository**:

```sh
aws ecr create-repository --repository-name $IMAGE --image-scanning-configuration scanOnPush=true --image-tag-mutability MUTABLE
```

- **Tag image so it reflect changes in it**:

```sh
# Create a timestamp tag
TAG=$(date +%Y%m%d_%H%M%S)

# Tag the image
docker tag $IMAGE:latest $AWS_ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com/$IMAGE:$TAG
```

- **Push the image to ECR**:

```sh
docker push $AWS_ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com/$IMAGE:$TAG
```

- **Create a lambda execution role**:

```sh
# Give the Lambda execution role a name in AWS_LAMBDA_ROLE_NAME
AWS_LAMBDA_ROLE_NAME="$IMAGE-role"

aws iam create-role --role-name $AWS_LAMBDA_ROLE_NAME --assume-role-policy-document '{"Version": "2012-10-17","Statement": [{ "Effect": "Allow", "Principal": {"Service": "lambda.amazonaws.com"}, "Action": "sts:AssumeRole"}]}'
aws iam attach-role-policy --role-name $AWS_LAMBDA_ROLE_NAME --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
aws iam attach-role-policy --role-name $AWS_LAMBDA_ROLE_NAME --policy-arn arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess
```

- **Create a Lambda Function**:

```sh
ENV=stage # dev, stage, prod
AWS_LAMBDA_FUNC_NAME="$IMAGE-$ENV"

aws lambda create-function \
    --function-name $AWS_LAMBDA_FUNC_NAME \
    --package-type Image \
    --code ImageUri=$AWS_ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com/$IMAGE:$TAG \
    --role $(aws iam get-role --role-name $AWS_LAMBDA_ROLE_NAME --query 'Role.Arn' --output text)
```

- **Add environment variable to Lambda runtime**:

```sh
# Upload the current ENV to Lambda
aws lambda update-function-configuration \
    --function-name $AWS_LAMBDA_FUNC_NAME \
    --environment "Variables={ENV=$ENV}"
```

- **Create an API Gateway**:

```sh
API_GATEWAY_NAME=$IMAGE

# Create API Gateway
aws apigateway create-rest-api --name $API_GATEWAY_NAME --region $AWS_REGION

# Get the API Gateway ID.
# API_GATEWAY_ID might not be available immediately after the creation of the
# new API Gateway. You might have to wait.
API_GATEWAY_ID=$(aws apigateway get-rest-apis --query "items[?name=='$API_GATEWAY_NAME'].id" --output text)
```

- **Create a Proxy Resource**:

Instead of a resource with a predefined route, allows network traffic of any route to be accepted by the API Gateway.

```sh
# First obtain the parent ID of the newly created API Gateway
PARENT_ID=$(aws apigateway get-resources --rest-api-id $API_GATEWAY_ID --region $AWS_REGION --query 'items[0].id' --output text)

# Then create a proxy resource under the parent ID.
# PARENT_ID might not be available immediately after the creation of the
# new API Gateway. You might have to wait.
aws apigateway create-resource --rest-api-id $API_GATEWAY_ID --region $AWS_REGION --parent-id $PARENT_ID --path-part {proxy+}
```

- **Add a ANY method so the API Gateway delegates the methods handling to FASTAPI**:

The ANY method, instead of a predefined method like GET, POST, etc., tells the proxy resource that it can accepts any REST methods. Similar to the proxy resource, the ANY method delegates the method handling to the FastAPI.

```sh
# First obtain the ID of the proxy resource just created
RESOURCE_ID=$(aws apigateway get-resources --rest-api-id $API_GATEWAY_ID --query "items[?parentId=='$PARENT_ID'].id" --output text)

# Then add "ANY" method to the resource
# RESOURCE_ID might not be available immediately after the creation of the
# proxy resource. You might have to wait.
aws apigateway put-method --rest-api-id $API_GATEWAY_ID --region $AWS_REGION --resource-id $RESOURCE_ID --http-method ANY --authorization-type "NONE"
```

- **Tell the API Gateway which Lambda to use for the ANY method**:

```sh
# get the ARN of the Lambda function we created earlier
LAMBDA_ARN=$(aws lambda get-function --function-name $AWS_LAMBDA_FUNC_NAME --query 'Configuration.FunctionArn' --output text)

URI=arn:aws:apigateway:${AWS_REGION}:lambda:path/2015-03-31/functions/arn:aws:lambda:${AWS_REGION}:${AWS_ACCOUNT}:function:${IMAGE}-\${stageVariables.env}/invocations

aws apigateway put-integration \
    --region $AWS_REGION \
    --rest-api-id $API_GATEWAY_ID \
    --resource-id $RESOURCE_ID \
    --http-method ANY \
    --type AWS_PROXY \
    --integration-http-method POST \
    --uri $URI
```

- **Grant permissions to API Gateway invoke the lambda**:

```sh
aws lambda add-permission --function-name $LAMBDA_ARN --source-arn "arn:aws:execute-api:$AWS_REGION:$AWS_ACCOUNT:$API_GATEWAY_ID/*/*/{proxy+}" --principal apigateway.amazonaws.com --statement-id apigateway-access --action lambda:InvokeFunction
```

- **Deploy the api gateway**:

```sh
aws apigateway create-deployment --rest-api-id $API_GATEWAY_ID --stage-name $ENV --variables env=$ENV
```

- **Api Gateway Address**:

```sh
GO_TO=https://$API_GATEWAY_ID.execute-api.$AWS_REGION.amazonaws.com/$ENV/docs
echo $GO_TO
```

## Update Lambda container image

- **Build Image**:

```sh
IMAGE=fast-api-aws-lambda
docker build --platform linux/amd64 -t $IMAGE:latest .
```

- **Login into AWS ECR**:

```sh
# Get AWS_ACCOUNT and AWS_REGION. Both will be used in future commands
AWS_ACCOUNT=$(aws sts get-caller-identity --query 'Account' --output text)
AWS_REGION=$(aws ec2 describe-availability-zones --query 'AvailabilityZones[0].RegionName' --output text)

# login AWS ECR
echo $(aws ecr get-login-password --region $AWS_REGION) | docker login --username AWS --password-stdin $AWS_ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com
```

- **Tag image so it reflect changes in it**:

```sh
# Create a timestamp tag
IMAGE=fast-api-aws-lambda
ENV=stage # dev, stage, prod
TAG=$(date +%Y%m%d_%H%M%S)

# Tag the image
docker tag $IMAGE:latest $AWS_ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com/$IMAGE:$TAG
```

- **Push the image to ECR**:

```sh
docker push $AWS_ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com/$IMAGE:$TAG
```

- **Update Lambda Function**:

```sh
AWS_LAMBDA_FUNC_NAME="$IMAGE-$ENV"

aws lambda update-function-code \
    --function-name $AWS_LAMBDA_FUNC_NAME \
    --image-uri $AWS_ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com/$IMAGE:$TAG
```

- **Api Gateway Address**:

```sh
GO_TO=https://$API_GATEWAY_ID.execute-api.$AWS_REGION.amazonaws.com/$ENV/docs
echo $GO_TO
```

## Deploy to PROD

This deploy will be made on the same account, but a good practice is to have a different account for each environment.

- **Gather variables**:

```sh
AWS_ACCOUNT=$(aws sts get-caller-identity --query 'Account' --output text)
AWS_REGION=$(aws ec2 describe-availability-zones --query 'AvailabilityZones[0].RegionName' --output text)

ENV=prod # dev, stage, prod
AWS_LAMBDA_FUNC_NAME="$IMAGE-$ENV"
AWS_LAMBDA_ROLE_NAME="$IMAGE-role"
TAG=$(aws ecr describe-images --repository-name $IMAGE --query 'sort_by(imageDetails, &imagePushedAt)[*].imageTags' --output json | grep -oP '"\K[^"]+' | tail -1)

API_GATEWAY_NAME=$IMAGE
API_GATEWAY_ID=$(aws apigateway get-rest-apis --query "items[?name=='$API_GATEWAY_NAME'].id" --output text)
```

- **Create a Lambda Function**:

```sh
aws lambda create-function \
    --function-name $AWS_LAMBDA_FUNC_NAME \
    --package-type Image \
    --code ImageUri=$AWS_ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com/$IMAGE:$TAG \
    --role $(aws iam get-role --role-name $AWS_LAMBDA_ROLE_NAME --query 'Role.Arn' --output text)
```

- **Grant permissions to API Gateway invoke the lambda**:

```sh
LAMBDA_ARN=$(aws lambda get-function --function-name $AWS_LAMBDA_FUNC_NAME --query 'Configuration.FunctionArn' --output text)

aws lambda add-permission --function-name $LAMBDA_ARN --source-arn "arn:aws:execute-api:$AWS_REGION:$AWS_ACCOUNT:$API_GATEWAY_ID/*/*/{proxy+}" --principal apigateway.amazonaws.com --statement-id apigateway-access --action lambda:InvokeFunction
```

- **Add environment variable to Lambda runtime**:

```sh
# Upload the current ENV to Lambda
aws lambda update-function-configuration \
    --function-name $AWS_LAMBDA_FUNC_NAME \
    --environment "Variables={ENV=$ENV}"
```

- **Deploy the api gateway**:

```sh
aws apigateway create-deployment --rest-api-id $API_GATEWAY_ID --stage-name $ENV --variables env=$ENV
```

- **Api Gateway Address**:

```sh
GO_TO=https://$API_GATEWAY_ID.execute-api.$AWS_REGION.amazonaws.com/$ENV/docs
echo $GO_TO
```

## Tear Down

- **Gather variables**:

```sh
AWS_ACCOUNT=$(aws sts get-caller-identity --query 'Account' --output text)
AWS_REGION=$(aws ec2 describe-availability-zones --output text --query 'AvailabilityZones[0].[RegionName]')
AWS_LAMBDA_ROLE_NAME="$IMAGE-role"
AWS_LAMBDA_FUNC_NAME="$IMAGE-$ENV"
API_GATEWAY_NAME=$IMAGE
```

- **Delete API Gateway**:

```sh
API_GATEWAY_ID=$(aws apigateway get-rest-apis --query "items[?name=='$API_GATEWAY_NAME'].id" --output text)
aws apigateway delete-rest-api --rest-api-id $API_GATEWAY_ID
```

- **Delete Lambda Function**:

```sh
aws lambda delete-function --function-name $AWS_LAMBDA_FUNC_NAME
```

- **Delete Lambda Execution Role**:

```sh
for POLICY_ARN in $(aws iam list-attached-role-policies --role-name $AWS_LAMBDA_ROLE_NAME --query 'AttachedPolicies[*].PolicyArn' --output text)
do
    aws iam detach-role-policy --role-name $AWS_LAMBDA_ROLE_NAME --policy-arn $POLICY_ARN
done
aws iam delete-role --role-name $AWS_LAMBDA_ROLE_NAME
```

- **Delete ECR Repository**:

```sh
aws ecr delete-repository --repository-name $IMAGE --force --profile $PROFILE
```

## Resources

- [Medium](https://fanchenbao.medium.com/api-service-with-fastapi-aws-lambda-api-gateway-and-make-it-work-c20edcf77bff)
