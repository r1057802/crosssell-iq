namespace CrossSellIQ.Api.Models;

/// <summary>Step 2 of a recommendation: one of the most bought products inside a recommended category.</summary>
public sealed record ProductRecommendation(string ProductCode, string Name, string Type, double Score);

public sealed record Recommendation(string Category, double Score, string Reason, IReadOnlyList<ProductRecommendation> Products);

/// <summary>
/// Response of GET /api/recommendations/{customerId}. Message is only set for special cases,
/// such as a customer without purchases in a recommendable category.
/// </summary>
public sealed record RecommendationResponse(
    string CustomerId,
    IReadOnlyList<Recommendation> Recommendations,
    IReadOnlyList<string> PurchasedCategories,
    string? Message);
