type Stage = 'production' | 'staging';

type Settings = {
  stage: Stage;
  apiBaseUrl: string;
}

type StandardTags = {
  applicationTag: string;
  billingServiceTag: string;
  stage: Stage;
}

export { Stage, Settings, StandardTags };
