FROM mcr.microsoft.com/dotnet/sdk:10.0 AS build
WORKDIR /source

COPY src/CrossSellIQ.Api/CrossSellIQ.Api.csproj src/CrossSellIQ.Api/
RUN dotnet restore src/CrossSellIQ.Api/CrossSellIQ.Api.csproj

COPY src/CrossSellIQ.Api/ src/CrossSellIQ.Api/
RUN dotnet publish src/CrossSellIQ.Api/CrossSellIQ.Api.csproj \
    --configuration Release --no-restore --output /app/publish

FROM mcr.microsoft.com/dotnet/aspnet:10.0
WORKDIR /app
COPY --from=build /app/publish .

ENV ASPNETCORE_HTTP_PORTS=8080 \
    Database__Path=/data/crossselliq.duckdb
USER $APP_UID
EXPOSE 8080

ENTRYPOINT ["dotnet", "CrossSellIQ.Api.dll"]
