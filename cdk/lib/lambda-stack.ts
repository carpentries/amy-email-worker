import { Duration, Stack, StackProps } from 'aws-cdk-lib';
import { Construct } from 'constructs';
import { IVpc } from "aws-cdk-lib/aws-ec2";
import { Architecture, IFunction, Runtime } from "aws-cdk-lib/aws-lambda";
import { PythonFunction } from "@aws-cdk/aws-lambda-python-alpha";

interface AdditionalProps extends StackProps {
  vpc: IVpc;
  stage: string;
}

export class LambdaStack extends Stack {
  public readonly lambdaFunction: IFunction;

  constructor(scope: Construct, id: string, props: AdditionalProps) {
    super(scope, id, props);

    const {
      vpc,
      stage,
    } = props;

    const environment = {
      'OVERWRITE_OUTGOING_EMAILS': '',
      'STAGE': stage,
    };

    if (stage != 'production') {
      environment.OVERWRITE_OUTGOING_EMAILS = 'email-automation-staging@carpentries.org';
    }

    this.lambdaFunction = new PythonFunction(this, 'EmailWorker', {
      functionName: 'amy-email-worker',
      architecture: Architecture.ARM_64,  // cheaper than x84_64b
      runtime: Runtime.PYTHON_3_10,
      entry: '../worker',
      index: 'main.py',
      handler: 'handler',
      timeout: Duration.minutes(2),
      vpc: vpc,
      environment: environment,
    });
  }
}
