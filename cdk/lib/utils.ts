import { Tags } from 'aws-cdk-lib';
import { IConstruct } from 'constructs';
import type { StandardTags } from './types';

function applyStandardTags(scope: IConstruct, tags: StandardTags): void {
  Tags.of(scope).add('ApplicationID', tags.applicationTag);
  Tags.of(scope).add('Billing-Service', tags.billingServiceTag);
  Tags.of(scope).add('Service-Type', tags.stage);
  Tags.of(scope).add('Environment', tags.stage);
}

export { applyStandardTags };
