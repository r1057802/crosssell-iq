namespace CrossSellIQ.Api.Models;

/// <summary>A row of gold.category_top_products.</summary>
public sealed record TopProduct(string Category, string ProductCode, string Name, string Type, double Score, long Rank);
