namespace CrossSellIQ.Api.Models;

/// <summary>A recommendable category with its normalized popularity score from gold.category_popularity.</summary>
public sealed record CategoryPopularity(string Category, double PopularityScore);
