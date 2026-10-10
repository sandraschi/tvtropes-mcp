# Per-repo fleet start config for tvtropes-mcp
# Edit ports/backend target here - start.ps1 is fleet-standard.
@{
    Name         = 'tvtropes-mcp'
    BackendPort  = 10964
    FrontendPort = 10965
    HealthPath   = '/api/health'
    WebRoot      = 'web_sota'
    Backend = @{
        Kind          = 'nssm'
        UvicornTarget = 'tvtropes_mcp.app:app'
        SyncExtras    = @('dev')
        SyncOnStart  = $true
        Env           = @{ WEB_PORT = '10964' }
    }
    Frontend = @{
        Kind           = 'vite-npm'
        PackageManager = 'npm'
        PortEnvVar     = 'VITE_PORT'
        ApiTargetEnv   = 'VITE_API_TARGET'
    }
}
