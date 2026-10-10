using System.ComponentModel.DataAnnotations;

namespace CrossSellIQ.Api.Data;

public sealed class DuckDbOptions
{
    public const string SectionName = "Database";

    // A relative path is resolved against the API's content root, so it works from any working directory.
    // Override with the environment variable Database__Path, for example in Docker.
    [Required(AllowEmptyStrings = false)]
    public string Path { get; set; } = string.Empty;
}
