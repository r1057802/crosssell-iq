using System.Text.RegularExpressions;
using CrossSellIQ.Api.Models;
using CrossSellIQ.Api.Repositories;

namespace CrossSellIQ.Api.Services;

public enum RecommendationStatus
{
    Success,
    InvalidCustomerId,
    InvalidLimit,
    CustomerNotFound,
}

public sealed record RecommendationResult(RecommendationStatus Status, RecommendationResponse? Response = null);

/// <summary>
/// Baseline recommender: the most popular categories the customer has not bought yet,
/// ranked by normalized popularity. The score is not a purchase probability.
/// </summary>
public sealed partial class RecommendationService(IRecommendationRepository repository)
{
    public const int DefaultLimit = 5;
    public const int MaxLimit = 20;

    public const string BaselineReason = "Popular category this customer has not bought before";
    public const string NoRecommendableHistoryMessage =
        "This customer has no purchases in a recommendable category yet, so all popular categories are new.";
    public const string NoNewCategoriesMessage = "This customer has already bought every recommendable category.";

    [GeneratedRegex("^[0-9a-f]{64}$")]
    private static partial Regex CustomerIdPattern();

    /// <summary>Trims and lowercases the ID; returns null when it is not a 64-character hexadecimal hash.</summary>
    public static string? NormalizeCustomerId(string? customerId)
    {
        var normalized = customerId?.Trim().ToLowerInvariant();
        return normalized is not null && CustomerIdPattern().IsMatch(normalized) ? normalized : null;
    }

    public async Task<RecommendationResult> GetRecommendationsAsync(
        string? customerId, int limit = DefaultLimit, CancellationToken cancellationToken = default)
    {
        var normalizedId = NormalizeCustomerId(customerId);
        if (normalizedId is null)
        {
            return new RecommendationResult(RecommendationStatus.InvalidCustomerId);
        }
        if (limit is < 1 or > MaxLimit)
        {
            return new RecommendationResult(RecommendationStatus.InvalidLimit);
        }
        if (!await repository.CustomerExistsAsync(normalizedId, cancellationToken))
        {
            return new RecommendationResult(RecommendationStatus.CustomerNotFound);
        }

        var purchased = await repository.GetPurchasedCategoriesAsync(normalizedId, cancellationToken);
        var popularity = await repository.GetCategoryPopularityAsync(cancellationToken);

        var purchasedSet = purchased.ToHashSet(StringComparer.Ordinal);
        var recommendations = popularity
            .Where(category => !purchasedSet.Contains(category.Category))
            .OrderByDescending(category => category.PopularityScore)
            .ThenBy(category => category.Category, StringComparer.Ordinal)
            .Take(limit)
            .Select(category => new Recommendation(category.Category, Math.Round(category.PopularityScore, 4), BaselineReason))
            .ToList();

        string? message = null;
        if (purchased.Count == 0)
        {
            message = NoRecommendableHistoryMessage;
        }
        else if (recommendations.Count == 0)
        {
            message = NoNewCategoriesMessage;
        }

        return new RecommendationResult(
            RecommendationStatus.Success,
            new RecommendationResponse(normalizedId, recommendations, purchased, message));
    }

    public Task<IReadOnlyList<ExampleCustomer>> GetExampleCustomersAsync(CancellationToken cancellationToken = default)
        => repository.GetExampleCustomersAsync(cancellationToken);
}
