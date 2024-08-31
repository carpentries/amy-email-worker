# Welcome to your CDK TypeScript project

This is a CDK project with TypeScript for AMY Email Worker.

The `cdk.json` file tells the CDK Toolkit how to execute your app.

## Useful commands

* `npm run build`   compile typescript to js
* `npm run watch`   watch for changes and compile
* `npm run test`    perform the jest unit tests
* `cdk deploy`      deploy this stack to your default AWS account/region
* `cdk diff`        compare deployed stack with current state
* `cdk synth`       emits the synthesized CloudFormation template


## Deploying the stack

### Staging environment

```bash
$ npx cdk deploy EmailWorkerVpc EmailWorkerLambda EmailWorkerCron --profile carpentries
```
`--profile` can be a default profile or a named profile in `~/.aws/credentials` file.

### Production environment

In this case, the stage is changed to `production`, and the stacks have slightly different names:

```bash
$ npx cdk deploy EmailWorkerVpcProd EmailWorkerLambdaProd EmailWorkerCronProd --profile carpentries
```
`--profile` can be a default profile or a named profile in `~/.aws/credentials` file.
