# amy-email-worker
A lambda worker for sending queued emails at scheduled times.

## Repository structure

This repository doesn't follow typical project structure, so a word of explanation is
required.

* `cdk` directory contains TypeScript code to deploy the worker to AWS Cloud.
* `worker` directory contains Python code (project).
* root directory contains main `.gitignore`, `.pre-commit-config.yaml`, license and readme
* `.github` contains CI/CD pipelines.


## First steps (Python)

This project is for Python 3.10 version.

To work on Python code you should install [Poetry](https://python-poetry.org/docs/#installation).

Then you can create the Poetry environment:

```shell
$ cd worker/
$ poetry install
```

**Important!** Once Python dependencies are installed, you must install `pre-commit` configuration:

```shell
$ cd worker/
$ poetry shell
$ cd ..  # to root directory
$ pre-commit install
```

## First steps (CDK)

This project is for Node 18 LTS version.

To work on CDK (Cloud Development Kit) for AWS Cloud you should install:

1. node JS (a suggested method is to use [nvm](https://github.com/nvm-sh/nvm))
2. cdk:
    ```shell
    $ cd cdk/
    $ npm install
    ```

Additionally you will probably want to set up your [AWS CLI](https://aws.amazon.com/cli/) and credentials.


## Python paths and modules

AWS lambda environment is specific when it comes to Python path management. For example,
despite the code being in `worker` directory, lambda Python environment doesn't
recognize `worker` module.

Therefore it's important to avoid using `from worker.xyz import asd` or
`import worker.utils`, because this will not work. Instead, assume that the environment
is stored in unnamed directory somewhere on a virtual machine, and you only have access
to `worker`'s submodules, like `utils`. Thus `from utils.typing import Settings` will
work.

## Testing lambda

Apart from unit tests, you can deploy the lambda to the staging environment and test it
in [AWS web console](https://us-east-1.console.aws.amazon.com/lambda/home?region=us-east-1#/functions/amy-email-worker?tab=testing).

To deploy lambda use CDK:

```shell
$ cd cdk/
$ cdk deploy EmailWorkerLambda
```

**Warning:** this circumvents the CI/CD pipeline.
