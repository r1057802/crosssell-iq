using System.Net;
using System.Net.Http.Json;
using CrossSellIQ.Api.Models;
using CrossSellIQ.Api.Repositories;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.AspNetCore.TestHost;
using Microsoft.Extensions.DependencyInjection;

namespace CrossSellIQ.Api.Tests;

/// <summary>Runs the real HTTP pipeline (routing, controller, error handling) with a fake repository.</summary>
public class RecommendationsApiTests
{
    private static HttpClient CreateClient<TRepository>() where TRepository : class, IRecommendationRepository
    {
        var factory = new WebApplicationFactory<Program>().WithWebHostBuilder(builder =>
            builder.ConfigureTestServices(services =>
                services.AddScoped<IRecommendationRepository, TRepository>()));
        return factory.CreateClient();
    }

    [Fact]
    public async Task ValidCustomer_Returns200WithRecommendations()
    {
        using var client = CreateClient<FakeRecommendationRepository>();

        var response = await client.GetAsync($"/api/recommendations/{FakeRecommendationRepository.CustomerWithHistory}");

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        var body = await response.Content.ReadFromJsonAsync<RecommendationResponse>();
        Assert.NotNull(body);
        Assert.Equal(FakeRecommendationRepository.CustomerWithHistory, body.CustomerId);
        Assert.NotEmpty(body.Recommendations);
    }

    [Fact]
    public async Task UnknownCustomer_Returns404()
    {
        using var client = CreateClient<FakeRecommendationRepository>();

        var response = await client.GetAsync($"/api/recommendations/{FakeRecommendationRepository.UnknownCustomer}");

        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
    }

    [Theory]
    [InlineData("/api/recommendations/abc")]
    [InlineData("/api/recommendations/%20")]
    [InlineData($"/api/recommendations/{FakeRecommendationRepository.CustomerWithHistory}?limit=0")]
    [InlineData($"/api/recommendations/{FakeRecommendationRepository.CustomerWithHistory}?limit=abc")]
    public async Task InvalidInput_Returns400(string url)
    {
        using var client = CreateClient<FakeRecommendationRepository>();

        var response = await client.GetAsync(url);

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
    }

    [Fact]
    public async Task UnavailableDatabase_Returns503WithoutInternalDetails()
    {
        using var client = CreateClient<UnavailableRecommendationRepository>();

        var response = await client.GetAsync($"/api/recommendations/{FakeRecommendationRepository.CustomerWithHistory}");

        Assert.Equal(HttpStatusCode.ServiceUnavailable, response.StatusCode);
        var body = await response.Content.ReadAsStringAsync();
        Assert.DoesNotContain("locked", body, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public async Task ExampleCustomers_Returns200()
    {
        using var client = CreateClient<FakeRecommendationRepository>();

        var customers = await client.GetFromJsonAsync<List<ExampleCustomer>>("/api/example-customers");

        Assert.NotNull(customers);
        Assert.Equal(2, customers.Count);
    }
}
