using DuckDB.NET.Data;
using Microsoft.Extensions.Options;

namespace CrossSellIQ.Api.Data;

public sealed class DuckDbConnectionFactory
{
    private readonly string _connectionString;

    public DuckDbConnectionFactory(IOptions<DuckDbOptions> options, IHostEnvironment environment)
    {
        DatabasePath = System.IO.Path.GetFullPath(options.Value.Path, environment.ContentRootPath);

        // The API only reads Gold. Read-only mode guarantees it can never change the database,
        // and lets it open the file while no pipeline is writing.
        var builder = new DuckDBConnectionStringBuilder { DataSource = DatabasePath };
        builder["access_mode"] = "READ_ONLY";
        _connectionString = builder.ConnectionString;
    }

    public string DatabasePath { get; }

    public async Task<DuckDBConnection> OpenConnectionAsync(CancellationToken cancellationToken = default)
    {
        var connection = new DuckDBConnection(_connectionString);
        try
        {
            await connection.OpenAsync(cancellationToken);
            return connection;
        }
        catch
        {
            await connection.DisposeAsync();
            throw;
        }
    }
}
