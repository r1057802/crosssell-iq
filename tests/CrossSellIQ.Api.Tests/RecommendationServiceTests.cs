using CrossSellIQ.Api.Services;

namespace CrossSellIQ.Api.Tests;

public class RecommendationServiceTests
{
    private readonly RecommendationService _service = new(new FakeRecommendationRepository());

    [Fact]
    public async Task ValidCustomer_ReturnsRecommendations()
    {
        var result = await _service.GetRecommendationsAsync(FakeRecommendationRepository.CustomerWithHistory);

        Assert.Equal(RecommendationStatus.Success, result.Status);
        Assert.NotNull(result.Response);
        Assert.NotEmpty(result.Response.Recommendations);
        Assert.All(result.Response.Recommendations, r => Assert.Equal(RecommendationService.BaselineReason, r.Reason));
        Assert.Null(result.Response.Message);
    }

    [Fact]
    public async Task AlreadyPurchasedCategories_AreNeverRecommended()
    {
        var result = await _service.GetRecommendationsAsync(
            FakeRecommendationRepository.CustomerWithHistory, RecommendationService.MaxLimit);

        var recommended = result.Response!.Recommendations.Select(r => r.Category).ToList();
        Assert.DoesNotContain("Garment Upper body", recommended);
        Assert.DoesNotContain("Accessories", recommended);
        Assert.Equal(FakeRecommendationRepository.Categories.Count - 2, recommended.Count);
    }

    [Fact]
    public async Task Recommendations_AreSortedByScoreThenCategory()
    {
        var result = await _service.GetRecommendationsAsync(
            FakeRecommendationRepository.CustomerWithoutHistory, RecommendationService.MaxLimit);

        Assert.Equal(
            ["Garment Upper body", "Garment Lower body", "Accessories", "Swimwear", "Shoes", "Bags"],
            result.Response!.Recommendations.Select(r => r.Category));
    }

    [Fact]
    public async Task Limit_CapsTheNumberOfRecommendations()
    {
        var result = await _service.GetRecommendationsAsync(FakeRecommendationRepository.CustomerWithoutHistory, limit: 2);

        Assert.Equal(2, result.Response!.Recommendations.Count);
    }

    [Theory]
    [InlineData(0)]
    [InlineData(RecommendationService.MaxLimit + 1)]
    public async Task LimitOutsideRange_IsInvalid(int limit)
    {
        var result = await _service.GetRecommendationsAsync(FakeRecommendationRepository.CustomerWithHistory, limit);

        Assert.Equal(RecommendationStatus.InvalidLimit, result.Status);
    }

    [Fact]
    public async Task UnknownCustomer_IsNotFound()
    {
        var result = await _service.GetRecommendationsAsync(FakeRecommendationRepository.UnknownCustomer);

        Assert.Equal(RecommendationStatus.CustomerNotFound, result.Status);
        Assert.Null(result.Response);
    }

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("   ")]
    [InlineData("abc")]
    [InlineData("gggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggg")]
    [InlineData("' OR 1=1 --")]
    public async Task InvalidCustomerId_IsRejectedBeforeQueryingData(string? customerId)
    {
        var result = await _service.GetRecommendationsAsync(customerId);

        Assert.Equal(RecommendationStatus.InvalidCustomerId, result.Status);
    }

    [Fact]
    public async Task CustomerId_IsTrimmedAndLowercased()
    {
        var result = await _service.GetRecommendationsAsync($"  {FakeRecommendationRepository.CustomerWithHistory.ToUpperInvariant()} ");

        Assert.Equal(RecommendationStatus.Success, result.Status);
        Assert.Equal(FakeRecommendationRepository.CustomerWithHistory, result.Response!.CustomerId);
    }

    [Fact]
    public async Task CustomerWithoutRecommendableHistory_GetsPopularCategoriesAndMessage()
    {
        var result = await _service.GetRecommendationsAsync(FakeRecommendationRepository.CustomerWithoutHistory);

        Assert.Equal(RecommendationStatus.Success, result.Status);
        Assert.Equal("Garment Upper body", result.Response!.Recommendations[0].Category);
        Assert.Empty(result.Response.PurchasedCategories);
        Assert.Equal(RecommendationService.NoRecommendableHistoryMessage, result.Response.Message);
    }

    [Fact]
    public async Task CustomerWhoBoughtEverything_GetsEmptyListAndMessage()
    {
        var result = await _service.GetRecommendationsAsync(FakeRecommendationRepository.CustomerWithEverything);

        Assert.Equal(RecommendationStatus.Success, result.Status);
        Assert.Empty(result.Response!.Recommendations);
        Assert.Equal(RecommendationService.NoNewCategoriesMessage, result.Response.Message);
    }
}
