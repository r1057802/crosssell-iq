using CrossSellIQ.Api.Data;
using CrossSellIQ.Api.Repositories;
using CrossSellIQ.Api.Services;

var builder = WebApplication.CreateBuilder(args);

// Stop at startup with a clear error when the database path is missing from the configuration.
builder.Services.AddOptions<DuckDbOptions>()
    .Bind(builder.Configuration.GetSection(DuckDbOptions.SectionName))
    .ValidateDataAnnotations()
    .ValidateOnStart();
builder.Services.AddSingleton<DuckDbConnectionFactory>();
builder.Services.AddScoped<IRecommendationRepository, DuckDbRecommendationRepository>();
builder.Services.AddScoped<RecommendationService>();

builder.Services.AddControllers();
builder.Services.AddProblemDetails();
builder.Services.AddExceptionHandler<DatabaseUnavailableExceptionHandler>();

builder.Services.AddHealthChecks()
    .AddCheck<DuckDbHealthCheck>("database");

var app = builder.Build();

// Unexpected errors return a generic problem response without stack traces, also in Development.
app.UseExceptionHandler();
app.UseStatusCodePages();

app.Use(async (context, next) =>
{
    var headers = context.Response.Headers;
    headers["X-Content-Type-Options"] = "nosniff";
    headers["Referrer-Policy"] = "no-referrer";
    headers["Content-Security-Policy"] =
        "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; connect-src 'self'; " +
        "object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'";
    // Tells browsers to use HTTPS only. Azure terminates TLS before the request reaches the app, so the
    // header is set directly instead of with UseHsts(), which only adds it to requests the app sees as HTTPS.
    // Browsers ignore it over plain HTTP, so local Docker runs are not affected.
    if (!app.Environment.IsDevelopment())
    {
        headers["Strict-Transport-Security"] = "max-age=31536000";
    }
    await next();
});

app.UseDefaultFiles();
app.UseStaticFiles();

app.MapControllers();
app.MapHealthChecks("/health");

app.Run();

// Makes Program visible to the integration tests (WebApplicationFactory).
public partial class Program;
