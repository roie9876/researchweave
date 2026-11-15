@description('Location for all ResearchWeave AKS, PostgreSQL, Foundry, and Storage resources.')
param location string = resourceGroup().location

@description('Base prefix for resource names (lowercase alphanumeric).')
@minLength(3)
@maxLength(12)
param appPrefix string = 'rweave'

@description('Enable SecurityControl=Ignore tag when required by subscription policy.')
param allowPublicEndpointTag bool = true

@description('Kubernetes version for the AKS cluster.')
param kubernetesVersion string = '1.36'

var uniqueSuffix = substring(uniqueString(resourceGroup().id, appPrefix), 0, 6)
var aksClusterName = '${appPrefix}-${uniqueSuffix}-aks'
var postgresServerName = '${appPrefix}-${uniqueSuffix}-pg'
var storageAccountName = take('${replace(toLower(appPrefix), '-', '')}${uniqueSuffix}st', 24)
var aiServicesName = '${appPrefix}-${uniqueSuffix}-foundry'
var logAnalyticsName = '${appPrefix}-${uniqueSuffix}-logs'
var appInsightsName = '${appPrefix}-${uniqueSuffix}-ai'
var managedIdentityName = '${appPrefix}-${uniqueSuffix}-id'

var commonTags = union(
  {
    application: 'ResearchWeave'
    architecture: 'AKS-OpenScientist-AgentScope-TrustGraph'
  },
  allowPublicEndpointTag ? {
    SecurityControl: 'Ignore'
  } : {}
)

// 1. User-Assigned Managed Identity (AKS Workload Identity for Foundry, Content Understanding & Blob Storage)
resource managedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: managedIdentityName
  location: location
  tags: commonTags
}

// 2. Log Analytics & Application Insights
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

// 3. Azure Blob Storage (Per-Investigation Containers rw-inv-*)
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

// 4. Microsoft Foundry / Azure AI Services (gpt-6.1-sol, gpt-6-astra & Content Understanding)
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

var modelDeployments = [
  {
    name: 'gpt-6.1-sol'
    modelName: 'gpt-6.1-sol'
    modelVersion: '2026-09-29'
    skuName: 'GlobalStandard'
    capacity: 100
  }
  {
    name: 'gpt-6-astra'
    modelName: 'gpt-6-astra'
    modelVersion: '2026-09-03'
    skuName: 'GlobalStandard'
    capacity: 100
  }
]

@batchSize(1)
resource aiModelDeployments 'Microsoft.CognitiveServices/accounts/deployments@2023-05-01' = [for m in modelDeployments: {
  parent: aiServices
  name: m.name
  sku: {
    name: m.skuName
    capacity: m.capacity
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: m.modelName
      version: m.modelVersion
    }
  }
}]

// Cognitive Services OpenAI User + Cognitive Services User (for Content Understanding / Document Intelligence)
var cognitiveServicesOpenAIUserRoleId = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'
)
var cognitiveServicesUserRoleId = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  'a97b65f3-24c7-4388-baec-2e87135dc908'
)

resource aiOpenAIRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aiServices.id, managedIdentity.id, cognitiveServicesOpenAIUserRoleId)
  scope: aiServices
  properties: {
    roleDefinitionId: cognitiveServicesOpenAIUserRoleId
    principalId: managedIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

resource aiCognitiveUserRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aiServices.id, managedIdentity.id, cognitiveServicesUserRoleId)
  scope: aiServices
  properties: {
    roleDefinitionId: cognitiveServicesUserRoleId
    principalId: managedIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

// 5. Azure Database for PostgreSQL Flexible Server (OpenScientist & Temporal Canonical State + pgvector + AGE)
resource postgresServer 'Microsoft.DBforPostgreSQL/flexibleServers@2023-06-01-preview' = {
  name: postgresServerName
  location: location
  tags: commonTags
  sku: {
    name: 'Standard_D2ds_v5'
    tier: 'GeneralPurpose'
  }
  properties: {
    version: '16'
    authConfig: {
      activeDirectoryAuth: 'Enabled'
      passwordAuth: 'Disabled'
    }
    storage: {
      storageSizeGB: 64
      autoGrow: 'Enabled'
    }
    highAvailability: {
      mode: 'Disabled'
    }
    backup: {
      backupRetentionDays: 7
      geoRedundantBackup: 'Disabled'
    }
  }
}

resource postgresDatabase 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2023-06-01-preview' = {
  parent: postgresServer
  name: 'researchweave_openscientist'
  properties: {
    charset: 'UTF8'
    collation: 'en_US.utf8'
  }
}

// 6. Azure Kubernetes Service (AKS) with 4 Specialized Node Pools:
//    - apppool: OpenScientist UI, FastAPI, AgentScope 2.0 Workers & Temporal
//    - brainpool: TrustGraph StatefulSets (Cassandra, Qdrant, Pulsar)
//    - sandboxpool: Kata Containers microVM Pod Sandboxing for untrusted scientific code execution
//    - gpupool: Scale-to-zero (0..4) GPU node pool for heavy scientific simulations
resource aksCluster 'Microsoft.ContainerService/managedClusters@2024-02-01' = {
  name: aksClusterName
  location: location
  tags: commonTags
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    kubernetesVersion: kubernetesVersion
    dnsPrefix: '${appPrefix}-${uniqueSuffix}'
    oidcIssuerProfile: {
      enabled: true
    }
    securityProfile: {
      workloadIdentity: {
        enabled: true
      }
    }
    networkProfile: {
      networkPlugin: 'azure'
      networkPluginMode: 'overlay'
      networkPolicy: 'cilium'
      networkDataplane: 'cilium'
    }
    addonProfiles: {
      omsagent: {
        enabled: true
        config: {
          logAnalyticsWorkspaceResourceID: logAnalytics.id
        }
      }
    }
    agentPoolProfiles: [
      {
        name: 'apppool'
        mode: 'System'
        count: 2
        minCount: 1
        maxCount: 5
        enableAutoScaling: true
        vmSize: 'Standard_D4s_v5'
        osType: 'Linux'
        osSKU: 'AzureLinux'
        nodeLabels: {
          'researchweave.io/pool': 'app'
        }
      }
      {
        name: 'brainpool'
        mode: 'User'
        count: 2
        minCount: 2
        maxCount: 6
        enableAutoScaling: true
        vmSize: 'Standard_E8s_v5'
        osType: 'Linux'
        osSKU: 'AzureLinux'
        nodeLabels: {
          'researchweave.io/pool': 'brain'
        }
      }
      {
        name: 'sandboxpool'
        mode: 'User'
        count: 1
        minCount: 1
        maxCount: 8
        enableAutoScaling: true
        vmSize: 'Standard_D4s_v5'
        osType: 'Linux'
        osSKU: 'AzureLinux'
        workloadRuntime: 'KataMshvVmIsolation'
        nodeLabels: {
          'researchweave.io/pool': 'sandbox'
        }
      }
      {
        name: 'gpupool'
        mode: 'User'
        count: 0
        minCount: 0
        maxCount: 4
        enableAutoScaling: true
        vmSize: 'Standard_NC4as_T4_v3'
        osType: 'Linux'
        osSKU: 'Ubuntu'
        nodeLabels: {
          'researchweave.io/pool': 'gpu'
        }
        nodeTaints: [
          'nvidia.com/gpu=true:NoSchedule'
        ]
      }
    ]
  }
}

resource federatedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities/federatedIdentityCredentials@2023-01-31' = {
  parent: managedIdentity
  name: 'researchweave-aks-wi'
  properties: {
    issuer: aksCluster.properties.oidcIssuerProfile.issuerURL
    subject: 'system:serviceaccount:researchweave:researchweave-sa'
    audiences: [
      'api://AzureADTokenExchange'
    ]
  }
}

output aksClusterName string = aksCluster.name
output postgresFqdn string = postgresServer.properties.fullyQualifiedDomainName
output foundryEndpoint string = aiServices.properties.endpoint
output foundryDeployedModels array = [for m in modelDeployments: m.name]
output storageBlobEndpoint string = storageAccount.properties.primaryEndpoints.blob
output workloadIdentityClientId string = managedIdentity.properties.clientId
