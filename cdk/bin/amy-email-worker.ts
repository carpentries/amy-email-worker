#!/usr/bin/env node
import 'source-map-support/register';
import { App } from 'aws-cdk-lib';
import { VpcStack } from '../lib/vpc-stack';
import { LambdaStack } from '../lib/lambda-stack';
import { CronStack } from '../lib/cron-stack';
import { Settings, StandardTags } from '../lib/types';
import { applyStandardTags } from '../lib/utils';

const stagingSettings: Settings = {
  stage: 'staging',
  apiBaseUrl: 'https://test-amy2.carpentries.org/api',
};

const stagingTags: StandardTags = {
  applicationTag: 'amy-email-worker',
  billingServiceTag: 'AMY',
  stage: stagingSettings.stage,
};

const productionSettings: Settings = {
  stage: 'production',
  apiBaseUrl: 'https://amy.carpentries.org/api',
};

const productionTags: StandardTags = {
  applicationTag: 'amy-email-worker',
  billingServiceTag: 'AMY',
  stage: productionSettings.stage,
};

const env = {
  account: process.env.CDK_DEFAULT_ACCOUNT,
  region: process.env.CDK_DEFAULT_REGION,
};

const app = new App();

/*******************/
/** S T A G I N G **/
/*******************/
const vpcStackStaging = new VpcStack(app, 'EmailWorkerVpc', {
  env: env
});
applyStandardTags(vpcStackStaging, stagingTags);

const lambdaStackStaging = new LambdaStack(app, 'EmailWorkerLambda', {
  env: env,
  vpc: vpcStackStaging.vpc,
  stage: stagingSettings.stage,
  api_base_url: stagingSettings.apiBaseUrl,
});
applyStandardTags(lambdaStackStaging, stagingTags);

const cronStackStaging = new CronStack(app, 'EmailWorkerCron', {
  env: env,
  lambdaFunction: lambdaStackStaging.lambdaFunction,
});
applyStandardTags(cronStackStaging, stagingTags);


/*************************/
/** P R O D U C T I O N **/
/*************************/
const vpcStackProduction = new VpcStack(app, 'EmailWorkerVpcProd', {
  env: env
});
applyStandardTags(vpcStackProduction, productionTags);

const lambdaStackProduction = new LambdaStack(app, 'EmailWorkerLambdaProd', {
  env: env,
  vpc: vpcStackProduction.vpc,
  stage: productionSettings.stage,
  api_base_url: productionSettings.apiBaseUrl,
});
applyStandardTags(lambdaStackProduction, productionTags);

const cronStackProduction = new CronStack(app, 'EmailWorkerCronProd', {
  env: env,
  lambdaFunction: lambdaStackProduction.lambdaFunction,
});
applyStandardTags(cronStackProduction, productionTags);
