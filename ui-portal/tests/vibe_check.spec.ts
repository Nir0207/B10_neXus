import { expect, test } from "@playwright/test";

const MOCK_GRAPH_RESPONSE = {
  nodes: [
    { id: "gene-cyp3a4", label: "CYP3A4", type: "Gene" },
    { id: "disease-thrombosis", label: "Thrombosis", type: "Disease" },
  ],
  edges: [
    {
      source: "gene-cyp3a4",
      target: "disease-thrombosis",
      relationship: "ASSOCIATED_WITH",
    },
  ],
};

test("dashboard keeps Stitch branding and liver click hits the gateway", async ({ page }) => {
  let liverRequestCount = 0;
  let latestLiverRequestUrl = "";

  await page.route("**/api/triplets**", async (route) => {
    const requestUrl = new URL(route.request().url());

    if (requestUrl.searchParams.get("organ") === "liver") {
      liverRequestCount += 1;
      latestLiverRequestUrl = requestUrl.toString();
    }

    await route.fulfill({
      body: JSON.stringify(MOCK_GRAPH_RESPONSE),
      contentType: "application/json",
      status: 200,
    });
  });

  await page.goto("/");
  await expect(page.getByTestId("dashboard-root")).toBeVisible();

  const designPrimaryHex = await page.evaluate(() =>
    getComputedStyle(document.documentElement)
      .getPropertyValue("--color-primary")
      .trim()
      .toLowerCase()
  );
  expect(designPrimaryHex).toBe("#81cfff");

  const computedBrandColor = await page.getByTestId("brand-primary").evaluate((el) => {
    return getComputedStyle(el).color.replace(/\s+/g, "");
  });
  expect(computedBrandColor).toBe("rgb(129,207,255)");

  await page.getByRole("button", { name: "Heart" }).click();
  await expect.poll(() => latestLiverRequestUrl.length).toBeGreaterThan(0);

  const requestsBeforeClick = liverRequestCount;
  await page.getByRole("button", { name: "Liver" }).click();
  await expect.poll(() => liverRequestCount).toBeGreaterThan(requestsBeforeClick);

  const gatewayUrl = new URL(latestLiverRequestUrl);
  expect(gatewayUrl.origin).toBe("http://localhost:8000");
  expect(gatewayUrl.pathname).toBe("/api/triplets");
});
