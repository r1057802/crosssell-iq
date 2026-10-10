using Microsoft.Extensions.Diagnostics.HealthChecks;

namespace CrossSellIQ.Api.Data;

public sealed class DuckDbHealthCheck(DuckDbConnectionFactory connectionFactory, ILogger<DuckDbHealthCheck> logger) : IHealthCheck
{
    public async Task<HealthCheckResult> CheckHealthAsync(HealthCheckContext context, CancellationToken cancellationToken = default)
    {
        if (!File.Exists(connectionFactory.DatabasePath))
        {
            logger.LogError("Database file not found at {DatabasePath}. Run the pipeline first.", connectionFactory.DatabasePath);
            return HealthCheckResult.Unhealthy("Database not available.");
        }

        try
        {
            await using var connection = await connectionFactory.OpenConnectionAsync(cancellationToken);
            await using var command = connection.CreateCommand();
            command.CommandText = "SELECT count(*) FROM gold.category_popularity";
            var categoryCount = Convert.ToInt64(await command.ExecuteScalarAsync(cancellationToken));

            return categoryCount > 0
                ? HealthCheckResult.Healthy()
                : HealthCheckResult.Unhealthy("Gold tables are empty.");
        }
        catch (Exception exception)
        {
            // Details stay in the server log; the response only shows the health status.
            logger.LogError(exception, "Database health check failed for {DatabasePath}.", connectionFactory.DatabasePath);
            return HealthCheckResult.Unhealthy("Database not available.");
        }
    }
}
