import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import { Vpc, IVpc } from "aws-cdk-lib/aws-ec2";


export class VpcStack extends cdk.Stack {
  public readonly vpc: IVpc;

  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // Reuse existing AMY VPC cluster
    this.vpc = Vpc.fromLookup(this, 'AmyVPC', {
      vpcId: 'vpc-0b8953dafe58d7db6',  // Should be updated if changed upstream
    });
  }
}
