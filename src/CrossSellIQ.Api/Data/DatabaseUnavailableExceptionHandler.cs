using System.Data.Common;
using Microsoft.AspNetCore.Diagnostics;
using Microsoft.AspNetCore.Mvc;

namespace CrossSellIQ.Api.Data;

/// <summary>
/// Turns database errors into a 503 response. DbException is the common base class of
/// ADO.NET providers, so this also works if another database replaces DuckDB.
/// </summary>
public sealed class DatabaseUnavailableExceptionHandler(
    IProblemDetailsService problemDetailsService,
    ILogger<DatabaseUnavailableExceptionHandler> logger) : IExceptionHandler
{
    public async ValueTask<bool> TryHandleAsync(HttpContext httpContext, Exception exception, CancellationToken cancellationToken)
    {
        if (exception is not DbException)
        {
            return false;
        }

        // Details stay in the server log; the client only learns that the data is temporarily unavailable.
        logger.LogError(exception, "Database request failed.");
        httpContext.Response.StatusCode = StatusCodes.Status503ServiceUnavailable;

        return await problemDetailsService.TryWriteAsync(new ProblemDetailsContext
        {
            HttpContext = httpContext,
            Exception = exception,
            ProblemDetails = new ProblemDetails
            {
                Status = StatusCodes.Status503ServiceUnavailable,
                Title = "Database unavailable",
                Detail = "The recommendation data is temporarily unavailable. Please try again later.",
            },
        });
    }
}
