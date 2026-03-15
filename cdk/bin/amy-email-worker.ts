#!/usr/bin/env node
import 'source-map-support/register';
import { App } from 'aws-cdk-lib';
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
const lambdaStackStaging = new LambdaStack(app, 'EmailWorkerLambdaStaging', {
  env: env,
  stage: stagingSettings.stage,
  api_base_url: stagingSettings.apiBaseUrl,
});
applyStandardTags(lambdaStackStaging, stagingTags);

const cronStackStaging = new CronStack(app, 'EmailWorkerCronStaging', {
  env: env,
  lambdaFunction: lambdaStackStaging.lambdaFunction,
});
applyStandardTags(cronStackStaging, stagingTags);


/*************************/
/** P R O D U C T I O N **/
/*************************/
const lambdaStackProduction = new LambdaStack(app, 'EmailWorkerLambdaProduction', {
  env: env,
  stage: productionSettings.stage,
  api_base_url: productionSettings.apiBaseUrl,
});
applyStandardTags(lambdaStackProduction, productionTags);

const cronStackProduction = new CronStack(app, 'EmailWorkerCronProduction', {
  env: env,
  lambdaFunction: lambdaStackProduction.lambdaFunction,
});
applyStandardTags(cronStackProduction, productionTags);
