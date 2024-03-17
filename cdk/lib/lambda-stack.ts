import { Duration, Stack, StackProps } from 'aws-cdk-lib';
import { Construct } from 'constructs';
import { IVpc } from "aws-cdk-lib/aws-ec2";
import { Architecture, IFunction, Runtime } from "aws-cdk-lib/aws-lambda";
import { PythonFunction } from "@aws-cdk/aws-lambda-python-alpha";
import { ManagedPolicy, PolicyStatement, Role, ServicePrincipal } from 'aws-cdk-lib/aws-iam';

interface AdditionalProps extends StackProps {
  vpc: IVpc;
  stage: string;
  api_base_url: string;
}

export class LambdaStack extends Stack {
  public readonly lambdaFunction: IFunction;

  constructor(scope: Construct, id: string, props: AdditionalProps) {
    super(scope, id, props);

    const {
      vpc,
      stage,
      api_base_url,
    } = props;

    const environment = {
      'OVERWRITE_OUTGOING_EMAILS': '',
      'STAGE': stage,
      'API_BASE_URL': api_base_url,
    };

    if (stage != 'production') {
      environment.OVERWRITE_OUTGOING_EMAILS = 'amy-tests@carpentries.org';
    }

    const exeuctionRole = new Role(this, 'EmailWorkerExecutionRole', {
      assumedBy: new ServicePrincipal('lambda.amazonaws.com'),
    });

    this.lambdaFunction = new PythonFunction(this, 'EmailWorker', {
      functionName: 'amy-email-worker',
      architecture: Architecture.X86_64,  // more expensive than ARM
      runtime: Runtime.PYTHON_3_10,
      entry: '../worker',
      index: 'main.py',
      handler: 'handler',
      timeout: Duration.minutes(2),
      vpc: vpc,
      environment: environment,
      role: exeuctionRole,
    });

    exeuctionRole.addManagedPolicy(
      ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaVPCAccessExecutionRole')
    );
    exeuctionRole.addToPolicy(new PolicyStatement({
      resources: ['*'],
      actions: ['ssm:GetParameter'],
    }));
  }
}
