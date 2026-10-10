using CrossSellIQ.Api.Models;

namespace CrossSellIQ.Api.Repositories;

/// <summary>
/// Read access to the Gold tables. Services depend on this interface, so another database
/// (for example PostgreSQL) or a fake for tests can replace the DuckDB implementation.
/// </summary>
public interface IRecommendationRepository
{
    Task<bool> CustomerExistsAsync(string customerId, CancellationToken cancellationToken = default);

    Task<IReadOnlyList<CategoryPopularity>> GetCategoryPopularityAsync(CancellationToken cancellationToken = default);

    Task<IReadOnlyList<string>> GetPurchasedCategoriesAsync(string customerId, CancellationToken cancellationToken = default);

    Task<IReadOnlyList<ExampleCustomer>> GetExampleCustomersAsync(CancellationToken cancellationToken = default);
}
