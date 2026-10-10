using CrossSellIQ.Api.Data;
using CrossSellIQ.Api.Models;
using DuckDB.NET.Data;

namespace CrossSellIQ.Api.Repositories;

public sealed class DuckDbRecommendationRepository(DuckDbConnectionFactory connectionFactory) : IRecommendationRepository
{
    public async Task<bool> CustomerExistsAsync(string customerId, CancellationToken cancellationToken = default)
    {
        await using var connection = await connectionFactory.OpenConnectionAsync(cancellationToken);
        await using var command = connection.CreateCommand();
        command.CommandText = "SELECT count(*) FROM gold.customers WHERE customer_id = $customer_id";
        command.Parameters.Add(new DuckDBParameter("customer_id", customerId));

        return Convert.ToInt64(await command.ExecuteScalarAsync(cancellationToken)) > 0;
    }

    public async Task<IReadOnlyList<CategoryPopularity>> GetCategoryPopularityAsync(CancellationToken cancellationToken = default)
    {
        await using var connection = await connectionFactory.OpenConnectionAsync(cancellationToken);
        await using var command = connection.CreateCommand();
        command.CommandText = """
            SELECT category, popularity_score
            FROM gold.category_popularity
            ORDER BY popularity_score DESC, category
            """;

        var categories = new List<CategoryPopularity>();
        await using var reader = await command.ExecuteReaderAsync(cancellationToken);
        while (await reader.ReadAsync(cancellationToken))
        {
            categories.Add(new CategoryPopularity(reader.GetString(0), reader.GetDouble(1)));
        }
        return categories;
    }

    public async Task<IReadOnlyList<string>> GetPurchasedCategoriesAsync(string customerId, CancellationToken cancellationToken = default)
    {
        await using var connection = await connectionFactory.OpenConnectionAsync(cancellationToken);
        await using var command = connection.CreateCommand();
        command.CommandText = """
            SELECT category
            FROM gold.customer_categories
            WHERE customer_id = $customer_id
            ORDER BY category
            """;
        command.Parameters.Add(new DuckDBParameter("customer_id", customerId));

        var categories = new List<string>();
        await using var reader = await command.ExecuteReaderAsync(cancellationToken);
        while (await reader.ReadAsync(cancellationToken))
        {
            categories.Add(reader.GetString(0));
        }
        return categories;
    }

    public async Task<IReadOnlyList<ExampleCustomer>> GetExampleCustomersAsync(CancellationToken cancellationToken = default)
    {
        await using var connection = await connectionFactory.OpenConnectionAsync(cancellationToken);
        await using var command = connection.CreateCommand();
        command.CommandText = """
            SELECT customer_id, purchased_category_count
            FROM gold.example_customers
            ORDER BY purchased_category_count, customer_id
            """;

        var customers = new List<ExampleCustomer>();
        await using var reader = await command.ExecuteReaderAsync(cancellationToken);
        while (await reader.ReadAsync(cancellationToken))
        {
            customers.Add(new ExampleCustomer(reader.GetString(0), reader.GetInt64(1)));
        }
        return customers;
    }
}
