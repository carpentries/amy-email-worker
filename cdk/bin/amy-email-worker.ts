#!/usr/bin/env node
import 'source-map-support/register';
import { App, Tags } from 'aws-cdk-lib';
import { VpcStack } from '../lib/vpc-stack';
import { LambdaStack } from '../lib/lambda-stack';
import { CronStack } from '../lib/cron-stack';

const env = { account: process.env.CDK_DEFAULT_ACCOUNT, region: process.env.CDK_DEFAULT_REGION };

const APPLICATION = 'amy-email-worker';
const STAGE = 'staging';
const app = new App();

const vpcStack = new VpcStack(app, 'EmailWorkerVpc', {
  env: env
});
Tags.of(vpcStack).add('ApplicationID', APPLICATION);
Tags.of(vpcStack).add('Environment', STAGE);

const lambdaStack = new LambdaStack(app, 'EmailWorkerLambda', {
  env: env,
  vpc: vpcStack.vpc,
  stage: STAGE,
});
Tags.of(lambdaStack).add('ApplicationID', APPLICATION);
Tags.of(lambdaStack).add('Environment', STAGE);

const cronStack = new CronStack(app, 'EmailWorkerCron', {
  env: env,
  lambdaFunction: lambdaStack.lambdaFunction,
});
Tags.of(cronStack).add('ApplicationID', APPLICATION);
Tags.of(cronStack).add('Environment', STAGE);
