using System.Net;
using CrossSellIQ.Api.Repositories;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.AspNetCore.TestHost;
using Microsoft.Extensions.DependencyInjection;

namespace CrossSellIQ.Api.Tests;

/// <summary>Checks the static pages and the security headers of the web page.</summary>
public class WebPageTests
{
    private static HttpClient CreateClient(string environment)
    {
        var factory = new WebApplicationFactory<Program>().WithWebHostBuilder(builder =>
        {
            builder.UseEnvironment(environment);
            builder.ConfigureTestServices(services =>
                services.AddScoped<IRecommendationRepository, FakeRecommendationRepository>());
        });
        return factory.CreateClient();
    }

    [Theory]
    [InlineData("/privacy.html", "Privacy Policy")]
    [InlineData("/terms.html", "Terms and Conditions")]
    public async Task LegalPage_Returns200(string url, string title)
    {
        using var client = CreateClient("Production");

        var response = await client.GetAsync(url);

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Contains(title, await response.Content.ReadAsStringAsync());
    }

    [Fact]
    public async Task HomePage_LinksToLegalPages()
    {
        using var client = CreateClient("Production");

        var html = await client.GetStringAsync("/");

        Assert.Contains("href=\"privacy.html\"", html);
        Assert.Contains("href=\"terms.html\"", html);
    }

    [Fact]
    public async Task Production_SendsHstsHeader()
    {
        using var client = CreateClient("Production");

        var response = await client.GetAsync("/");

        Assert.True(response.Headers.TryGetValues("Strict-Transport-Security", out var values));
        Assert.Equal("max-age=31536000", Assert.Single(values));
    }

    [Fact]
    public async Task Development_DoesNotSendHstsHeader()
    {
        using var client = CreateClient("Development");

        var response = await client.GetAsync("/");

        Assert.False(response.Headers.Contains("Strict-Transport-Security"));
    }
}
