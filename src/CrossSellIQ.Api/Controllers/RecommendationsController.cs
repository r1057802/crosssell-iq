using CrossSellIQ.Api.Models;
using CrossSellIQ.Api.Services;
using Microsoft.AspNetCore.Mvc;

namespace CrossSellIQ.Api.Controllers;

[ApiController]
[Route("api")]
[Produces("application/json")]
public sealed class RecommendationsController(RecommendationService service) : ControllerBase
{
    /// <summary>Baseline recommendations: popular categories the customer has never bought.</summary>
    [HttpGet("recommendations/{customerId}")]
    [ProducesResponseType<RecommendationResponse>(StatusCodes.Status200OK)]
    [ProducesResponseType<ProblemDetails>(StatusCodes.Status400BadRequest)]
    [ProducesResponseType<ProblemDetails>(StatusCodes.Status404NotFound)]
    [ProducesResponseType<ProblemDetails>(StatusCodes.Status503ServiceUnavailable)]
    public async Task<IActionResult> GetRecommendations(
        string customerId,
        [FromQuery] int limit = RecommendationService.DefaultLimit,
        CancellationToken cancellationToken = default)
    {
        var result = await service.GetRecommendationsAsync(customerId, limit, cancellationToken);

        return result.Status switch
        {
            RecommendationStatus.Success => Ok(result.Response),
            RecommendationStatus.InvalidCustomerId => Problem(
                statusCode: StatusCodes.Status400BadRequest,
                title: "Invalid customer ID",
                detail: "The customer ID must be a 64-character hexadecimal hash."),
            RecommendationStatus.InvalidLimit => Problem(
                statusCode: StatusCodes.Status400BadRequest,
                title: "Invalid limit",
                detail: $"The limit must be between 1 and {RecommendationService.MaxLimit}."),
            RecommendationStatus.CustomerNotFound => Problem(
                statusCode: StatusCodes.Status404NotFound,
                title: "Customer not found",
                detail: "No customer with this ID exists in the dataset."),
            _ => throw new InvalidOperationException($"Unhandled recommendation status {result.Status}."),
        };
    }

    /// <summary>Real customers with varied purchase histories, for the demo page.</summary>
    [HttpGet("example-customers")]
    [ProducesResponseType<IReadOnlyList<ExampleCustomer>>(StatusCodes.Status200OK)]
    [ProducesResponseType<ProblemDetails>(StatusCodes.Status503ServiceUnavailable)]
    public async Task<IActionResult> GetExampleCustomers(CancellationToken cancellationToken = default)
        => Ok(await service.GetExampleCustomersAsync(cancellationToken));
}
