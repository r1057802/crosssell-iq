"use strict";

// All API data is written with textContent, never innerHTML, so it can never run as HTML.
const CUSTOMER_ID_PATTERN = /^[0-9a-f]{64}$/;

const form = document.getElementById("search-form");
const customerInput = document.getElementById("customer-id");
const customerError = document.getElementById("customer-id-error");
const limitSelect = document.getElementById("limit");
const submitButton = document.getElementById("submit-button");

const examplesStatus = document.getElementById("examples-status");
const examplesList = document.getElementById("examples-list");

const results = document.getElementById("results");
const resultsTitle = document.getElementById("results-title");
const resultsStatus = document.getElementById("results-status");
const resultsError = document.getElementById("results-error");
const resultsContent = document.getElementById("results-content");
const resultCustomer = document.getElementById("result-customer");
const resultPurchased = document.getElementById("result-purchased");
const resultMessage = document.getElementById("result-message");
const resultRows = document.getElementById("result-rows");

function show(element, visible) {
    element.hidden = !visible;
}

function setFieldError(message) {
    customerError.textContent = message;
    show(customerError, Boolean(message));
    customerInput.setAttribute("aria-invalid", message ? "true" : "false");
}

function shortId(customerId) {
    return `${customerId.slice(0, 12)}...${customerId.slice(-6)}`;
}

// Customers who only bought Unknown articles also have 0 recommendable categories,
// so the label must not claim they never bought anything.
function categoryCountLabel(count) {
    if (count === 0) {
        return "No recommendable purchases yet";
    }
    return count === 1 ? "1 category bought" : `${count} categories bought`;
}

async function readProblem(response) {
    try {
        const problem = await response.json();
        return { title: problem.title ?? "Request failed", detail: problem.detail ?? "" };
    } catch {
        return { title: "Request failed", detail: `The server answered with status ${response.status}.` };
    }
}

function showError(title, detail) {
    resultsError.replaceChildren();
    const heading = document.createElement("strong");
    heading.textContent = title;
    const text = document.createElement("span");
    text.textContent = detail;
    resultsError.append(heading, text);
    show(resultsError, true);
    show(resultsContent, false);
}

function renderRecommendations(data) {
    resultCustomer.textContent = data.customerId;

    resultPurchased.replaceChildren();
    if (data.purchasedCategories.length === 0) {
        const item = document.createElement("li");
        item.textContent = "No recommendable category yet";
        resultPurchased.append(item);
    } else {
        for (const category of data.purchasedCategories) {
            const item = document.createElement("li");
            item.textContent = category;
            resultPurchased.append(item);
        }
    }

    resultMessage.textContent = data.message ?? "";
    show(resultMessage, Boolean(data.message));

    resultRows.replaceChildren();
    data.recommendations.forEach((recommendation, index) => {
        const row = document.createElement("tr");

        const rank = document.createElement("td");
        rank.textContent = String(index + 1);

        const category = document.createElement("td");
        category.textContent = recommendation.category;

        const score = document.createElement("td");
        const scoreWrapper = document.createElement("div");
        scoreWrapper.className = "score";
        const value = document.createElement("span");
        value.textContent = recommendation.score.toFixed(4);
        const bar = document.createElement("div");
        bar.className = "score-bar";
        bar.setAttribute("aria-hidden", "true");
        const fill = document.createElement("div");
        fill.className = "score-fill";
        fill.style.width = `${Math.max(0, Math.min(1, recommendation.score)) * 100}%`;
        bar.append(fill);
        scoreWrapper.append(value, bar);
        score.append(scoreWrapper);

        const reason = document.createElement("td");
        reason.textContent = recommendation.reason;

        row.append(rank, category, score, reason);
        resultRows.append(row);
    });

    show(document.getElementById("result-table"), data.recommendations.length > 0);
    show(resultsError, false);
    show(resultsContent, true);
}

async function loadRecommendations(customerId) {
    show(results, true);
    show(resultsError, false);
    show(resultsContent, false);
    resultsStatus.textContent = "Loading recommendations...";
    show(resultsStatus, true);
    submitButton.disabled = true;
    results.setAttribute("aria-busy", "true");

    try {
        const url = `/api/recommendations/${encodeURIComponent(customerId)}?limit=${encodeURIComponent(limitSelect.value)}`;
        const response = await fetch(url, { headers: { Accept: "application/json" } });
        if (!response.ok) {
            const problem = await readProblem(response);
            showError(problem.title, problem.detail);
            return;
        }
        renderRecommendations(await response.json());
    } catch {
        showError("Connection problem", "The API could not be reached. Check that it is running and try again.");
    } finally {
        show(resultsStatus, false);
        submitButton.disabled = false;
        results.removeAttribute("aria-busy");
        // Show the whole result and move keyboard and screen reader focus to it.
        results.scrollIntoView({ block: "start" });
        resultsTitle.focus({ preventScroll: true });
    }
}

form.addEventListener("submit", (event) => {
    event.preventDefault();
    const customerId = customerInput.value.trim().toLowerCase();

    if (!customerId) {
        setFieldError("Enter a customer ID or select an example customer.");
        customerInput.focus();
        return;
    }
    if (!CUSTOMER_ID_PATTERN.test(customerId)) {
        setFieldError("A customer ID has exactly 64 characters: digits 0-9 and letters a-f.");
        customerInput.focus();
        return;
    }

    setFieldError("");
    customerInput.value = customerId;
    loadRecommendations(customerId);
});

async function loadExampleCustomers() {
    try {
        const response = await fetch("/api/example-customers", { headers: { Accept: "application/json" } });
        if (!response.ok) {
            const problem = await readProblem(response);
            examplesStatus.textContent = `${problem.title}. ${problem.detail}`;
            return;
        }

        const customers = await response.json();
        examplesList.replaceChildren();
        for (const customer of customers) {
            const item = document.createElement("li");
            const button = document.createElement("button");
            button.type = "button";
            button.className = "example-button";

            const id = document.createElement("span");
            id.className = "mono";
            id.textContent = shortId(customer.customerId);
            const count = document.createElement("span");
            count.className = "count";
            count.textContent = categoryCountLabel(customer.purchasedCategoryCount);
            button.append(id, count);
            button.setAttribute("aria-label", `Load recommendations for example customer with ${categoryCountLabel(customer.purchasedCategoryCount)}`);

            button.addEventListener("click", () => {
                customerInput.value = customer.customerId;
                setFieldError("");
                loadRecommendations(customer.customerId);
            });

            item.append(button);
            examplesList.append(item);
        }

        show(examplesStatus, customers.length === 0);
        examplesStatus.textContent = customers.length === 0 ? "No example customers available." : "";
        show(examplesList, customers.length > 0);
    } catch {
        examplesStatus.textContent = "Example customers could not be loaded. Check that the API is running.";
    }
}

loadExampleCustomers();
