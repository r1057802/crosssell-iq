using System.Data.Common;
using CrossSellIQ.Api.Models;
using CrossSellIQ.Api.Repositories;

namespace CrossSellIQ.Api.Tests;

/// <summary>In-memory Gold data, so the tests run without the DuckDB file (for example in GitHub Actions).</summary>
public sealed class FakeRecommendationRepository : IRecommendationRepository
{
    public const string CustomerWithHistory = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
    public const string CustomerWithoutHistory = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb";
    public const string CustomerWithEverything = "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc";
    public const string UnknownCustomer = "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd";

    // Deliberately not sorted by score, so the tests prove that the service sorts.
    public static readonly IReadOnlyList<CategoryPopularity> Categories =
    [
        new("Shoes", 0.25),
        new("Garment Upper body", 1.0),
        new("Accessories", 0.45),
        new("Bags", 0.01),
        new("Garment Lower body", 0.85),
        new("Swimwear", 0.45),
    ];

    // Deliberately not sorted by rank, so the tests prove that the service sorts. Product codes keep their leading zero.
    public static readonly IReadOnlyList<TopProduct> TopProducts =
    [
        new("Shoes", "0901330", "Zola boot", "Boots", 1.0, 1),
        new("Shoes", "0898886", "Joyce high shaft", "Boots", 0.8, 3),
        new("Shoes", "0916256", "Patsy Platform", "Boots", 0.9, 2),
        new("Garment Lower body", "0706016", "Jade HW Skinny", "Trousers", 1.0, 1),
        new("Garment Upper body", "0372860", "7p Basic Shaftless", "Sweater", 1.0, 1),
    ];

    private static readonly Dictionary<string, string[]> PurchasedByCustomer = new()
    {
        [CustomerWithHistory] = ["Garment Upper body", "Accessories"],
        [CustomerWithoutHistory] = [],
        [CustomerWithEverything] = Categories.Select(category => category.Category).ToArray(),
    };

    public Task<bool> CustomerExistsAsync(string customerId, CancellationToken cancellationToken = default)
        => Task.FromResult(PurchasedByCustomer.ContainsKey(customerId));

    public Task<IReadOnlyList<CategoryPopularity>> GetCategoryPopularityAsync(CancellationToken cancellationToken = default)
        => Task.FromResult(Categories);

    public Task<IReadOnlyList<string>> GetPurchasedCategoriesAsync(string customerId, CancellationToken cancellationToken = default)
        => Task.FromResult<IReadOnlyList<string>>(PurchasedByCustomer.GetValueOrDefault(customerId, []));

    public Task<IReadOnlyList<TopProduct>> GetTopProductsAsync(CancellationToken cancellationToken = default)
        => Task.FromResult(TopProducts);

    public Task<IReadOnlyList<ExampleCustomer>> GetExampleCustomersAsync(CancellationToken cancellationToken = default)
        => Task.FromResult<IReadOnlyList<ExampleCustomer>>(
        [
            new(CustomerWithoutHistory, 0),
            new(CustomerWithHistory, 2),
        ]);
}

/// <summary>Simulates an unreachable database.</summary>
public sealed class UnavailableRecommendationRepository : IRecommendationRepository
{
    private sealed class FakeDatabaseException() : DbException("Database file is locked.");

    public Task<bool> CustomerExistsAsync(string customerId, CancellationToken cancellationToken = default)
        => throw new FakeDatabaseException();

    public Task<IReadOnlyList<CategoryPopularity>> GetCategoryPopularityAsync(CancellationToken cancellationToken = default)
        => throw new FakeDatabaseException();

    public Task<IReadOnlyList<string>> GetPurchasedCategoriesAsync(string customerId, CancellationToken cancellationToken = default)
        => throw new FakeDatabaseException();

    public Task<IReadOnlyList<TopProduct>> GetTopProductsAsync(CancellationToken cancellationToken = default)
        => throw new FakeDatabaseException();

    public Task<IReadOnlyList<ExampleCustomer>> GetExampleCustomersAsync(CancellationToken cancellationToken = default)
        => throw new FakeDatabaseException();
}
