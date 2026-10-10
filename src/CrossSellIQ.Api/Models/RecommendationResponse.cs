namespace CrossSellIQ.Api.Models;

public sealed record Recommendation(string Category, double Score, string Reason);

/// <summary>
/// Response of GET /api/recommendations/{customerId}. Message is only set for special cases,
/// such as a customer without purchases in a recommendable category.
/// </summary>
public sealed record RecommendationResponse(
    string CustomerId,
    IReadOnlyList<Recommendation> Recommendations,
    IReadOnlyList<string> PurchasedCategories,
    string? Message);
