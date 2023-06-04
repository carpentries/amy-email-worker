import { Duration, Stack, StackProps } from 'aws-cdk-lib';
import { Construct } from 'constructs';
import { IFunction } from "aws-cdk-lib/aws-lambda";
import { LambdaFunction } from 'aws-cdk-lib/aws-events-targets';
import { Rule, Schedule } from 'aws-cdk-lib/aws-events';

interface AdditionalProps extends StackProps {
  lambdaFunction: IFunction;
}

export class CronStack extends Stack {
  constructor(scope: Construct, id: string, props: AdditionalProps) {
    super(scope, id, props);

    const {
      lambdaFunction,
    } = props;

    const schedule = Schedule.rate(Duration.minutes(5));
    const rule = new Rule(this, 'email-worker-cron-rule', {
      schedule: schedule,
    });
    const target = new LambdaFunction(lambdaFunction);
    rule.addTarget(target);
  }
}
