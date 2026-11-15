@description('Location for all ResearchWeave Azure resources.')
param location string = resourceGroup().location

@description('Base prefix for resource names (lowercase alphanumeric).')
@minLength(3)
@maxLength(14)
param appPrefix string = 'rweave'

@description('Container image for the ResearchWeave application.')
param containerImage string = 'ghcr.io/researchweave/researchweave:latest'

@description('Enable public network access tag (SecurityControl=Ignore) when required by subscription policy.')
param allowPublicEndpointTag bool = true

var uniqueSuffix = substring(uniqueString(resourceGroup().id, appPrefix), 0, 6)
var storageAccountName = take('${replace(toLower(appPrefix), '-', '')}${uniqueSuffix}st', 24)
var logAnalyticsName = '${appPrefix}-${uniqueSuffix}-logs'
var appInsightsName = '${appPrefix}-${uniqueSuffix}-ai'
var managedIdentityName = '${appPrefix}-${uniqueSuffix}-id'
var containerEnvName = '${appPrefix}-${uniqueSuffix}-env'
var containerAppName = '${appPrefix}-${uniqueSuffix}-app'
var aiServicesName = '${appPrefix}-${uniqueSuffix}-foundry'

var commonTags = union(
  {
    application: 'ResearchWeave'
    managedBy: 'Bicep-ARM-DeployToAzure'
  },
  allowPublicEndpointTag ? {
    SecurityControl: 'Ignore'
  } : {}
)

resource managedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: managedIdentityName
  location: location
  tags: commonTags
}

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: logAnalyticsName
  location: location
  tags: commonTags
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: appInsightsName
  location: location
  kind: 'web'
  tags: commonTags
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
  }
}

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageAccountName
  location: location
  tags: commonTags
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
    supportsHttpsTrafficOnly: true
  }
}

// Storage Blob Data Contributor role for User-Assigned Managed Identity (no account keys in code)
var storageBlobDataContributorRoleId = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  'ba92f5b4-2d11-453d-a403-e96b0029c9fe'
)

resource blobRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccount.id, managedIdentity.id, storageBlobDataContributorRoleId)
  scope: storageAccount
  properties: {
    roleDefinitionId: storageBlobDataContributorRoleId
    principalId: managedIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

resource aiServices 'Microsoft.CognitiveServices/accounts@2023-05-01' = {
  name: aiServicesName
  location: location
  tags: commonTags
  kind: 'AIServices'
  sku: {
    name: 'S0'
  }
  properties: {
    customSubDomainName: aiServicesName
    publicNetworkAccess: 'Enabled'
    disableLocalAuth: true
  }
}

var cognitiveServicesOpenAIUserRoleId = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'
)

resource aiRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aiServices.id, managedIdentity.id, cognitiveServicesOpenAIUserRoleId)
  scope: aiServices
  properties: {
    roleDefinitionId: cognitiveServicesOpenAIUserRoleId
    principalId: managedIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

resource containerAppEnv 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: containerEnvName
  location: location
  tags: commonTags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
  }
}

resource containerApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: containerAppName
  location: location
  tags: commonTags
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${managedIdentity.id}': {}
    }
  }
  properties: {
    managedEnvironmentId: containerAppEnv.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8080
        transport: 'auto'
      }
    }
    template: {
      containers: [
        {
          name: 'researchweave'
          image: containerImage
          resources: {
            cpu: json('1.0')
            memory: '2Gi'
          }
          env: [
            {
              name: 'PORT'
              value: '8080'
            }
            {
              name: 'AZURE_CLIENT_ID'
              value: managedIdentity.properties.clientId
            }
            {
              name: 'AZURE_STORAGE_ACCOUNT_URL'
              value: storageAccount.properties.primaryEndpoints.blob
            }
            {
              name: 'AZURE_OPENAI_ENDPOINT'
              value: aiServices.properties.endpoint
            }
            {
              name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
              value: appInsights.properties.ConnectionString
            }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 5
      }
    }
  }
}

output webWorkspaceUrl string = 'https://${containerApp.properties.configuration.ingress.fqdn}'
output storageBlobEndpoint string = storageAccount.properties.primaryEndpoints.blob
output foundryEndpoint string = aiServices.properties.endpoint
output managedIdentityClientId string = managedIdentity.properties.clientId
