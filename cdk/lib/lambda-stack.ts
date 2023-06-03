import { Stack, StackProps } from 'aws-cdk-lib';
import { Construct } from 'constructs';
import { IVpc } from "aws-cdk-lib/aws-ec2";
import { Runtime } from "aws-cdk-lib/aws-lambda";
import { PythonFunction } from "@aws-cdk/aws-lambda-python-alpha";

interface AdditionalProps extends StackProps {
  vpc: IVpc;
}

export class LambdaStack extends Stack {
  constructor(scope: Construct, id: string, props: AdditionalProps) {
    super(scope, id, props);

    const {
      vpc,
    } = props;

    const function_handler = new PythonFunction(this, 'EmailWorker', {
      runtime: Runtime.PYTHON_3_10,
      entry: '../worker',
      index: 'main.py',
      handler: 'handler',
      vpc: vpc,
    });
  }
}
