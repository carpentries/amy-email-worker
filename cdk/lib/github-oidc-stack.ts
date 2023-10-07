import { Stack, StackProps } from 'aws-cdk-lib';
import { Construct } from 'constructs';
import {
  OpenIdConnectProvider,
  PolicyStatement,
  Role,
  WebIdentityPrincipal,
} from 'aws-cdk-lib/aws-iam';

interface AdditionalProps extends StackProps {
  organization: string;
  repository: string;
}


export class GithubOidcAmyWorkerStack extends Stack {
  constructor(
    scope: Construct,
    id: string,
    props: AdditionalProps,
  ) {
    super(scope, id, props);

    const {
      organization,
      repository,
    } = props;

    // To be used in cases when the same provider has already been set up.
    const provider = OpenIdConnectProvider.fromOpenIdConnectProviderArn(
      this,
      'AmyGithubOidcProvider',
      'arn:aws:iam::860325783027:oidc-provider/token.actions.githubusercontent.com',
    );

    const cdkRole = new Role(this, 'AmyWorkerGithubOidcCdkRole', {
      roleName: 'AmyWorkerGithubOidcCdkRole',
      assumedBy: new WebIdentityPrincipal(provider.openIdConnectProviderArn, {
        StringLike: {
          ['token.actions.githubusercontent.com:sub']: `repo:${organization}/${repository}:*`,
        },
      })
    });
    cdkRole.addToPolicy(new PolicyStatement({
      actions: [
        "cloudformation:CreateChangeSet",
        "cloudformation:DeleteChangeSet",
        "cloudformation:DescribeChangeSet",
        "cloudformation:DescribeStacks",
        "cloudformation:ExecuteChangeSet",
        "cloudformation:CreateStack",
        "cloudformation:UpdateStack"
      ],
      resources: ["*"],
    }));
    this.exportValue(cdkRole.roleArn);
  }
}
