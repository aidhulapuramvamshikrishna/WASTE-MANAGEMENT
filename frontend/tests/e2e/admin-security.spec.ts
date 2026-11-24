import { test, expect } from "@playwright/test";

test.describe("SECURITY.md T7: Admin Endpoints Blocked in Production Proxy", () => {
  test("GET /api/v1/admin/feedback.csv returns 404 in production", async ({
    request,
  }) => {
    const res = await request.get("/api/v1/admin/feedback.csv");
    expect(res.status()).toBe(404);
  });

  test("GET /api/v1/%61dmin/feedback.csv (percent-encoded 'a') returns 404 in production", async ({
    request,
  }) => {
    const res = await request.get("/api/v1/%61dmin/feedback.csv");
    expect(res.status()).toBe(404);
  });

  test("GET /API/v1/admin/feedback.csv (uppercase API) returns 404 in production", async ({
    request,
  }) => {
    const res = await request.get("/API/v1/admin/feedback.csv");
    expect(res.status()).toBe(404);
  });

  test("GET /Api/V1/Admin/feedback.csv (mixed-case) returns 404 in production", async ({
    request,
  }) => {
    const res = await request.get("/Api/V1/Admin/feedback.csv");
    expect(res.status()).toBe(404);
  });

  test("GET /api/v1//admin/feedback.csv (double slashes) returns 404 in production", async ({
    request,
  }) => {
    const res = await request.get("/api/v1//admin/feedback.csv");
    expect(res.status()).toBe(404);
  });

  test("GET /api/v1/admin%2Ffeedback.csv (encoded slash) returns 404 in production", async ({
    request,
  }) => {
    const res = await request.get("/api/v1/admin%2Ffeedback.csv");
    expect(res.status()).toBe(404);
  });

  test("GET /api/v1/predictions/../admin/feedback.csv (dot segment traversal) returns 404 in production", async ({
    request,
  }) => {
    const res = await request.get("/api/v1/predictions/../admin/feedback.csv");
    expect(res.status()).toBe(404);
  });

  test("DELETE /api/v1/admin/predictions/<id> returns 404 in production", async ({
    request,
  }) => {
    const res = await request.delete(
      "/api/v1/admin/predictions/00000000000000000000000000000000"
    );
    expect(res.status()).toBe(404);
  });

  test("GET /api/admin/feedback.csv alternative path returns 404 in production", async ({
    request,
  }) => {
    const res = await request.get("/api/admin/feedback.csv");
    expect(res.status()).toBe(404);
  });
});
