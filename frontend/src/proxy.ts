import { NextResponse, type NextRequest } from "next/server";

export function proxy(request: NextRequest) {
  // 1. Strict path normalization for security verification (SECURITY.md T7)
  const rawPath = request.nextUrl.pathname;
  let decodedPath = rawPath;

  try {
    // Decode percent-encoded characters (%61 -> a, %2F -> /, etc.)
    // Recursively decode to eliminate nested/double percent-encoding bypasses
    let prev = "";
    while (decodedPath !== prev) {
      prev = decodedPath;
      decodedPath = decodeURIComponent(decodedPath);
    }
  } catch {
    // Malformed URI encoding (e.g. invalid % sequence) -> reject with 400 Bad Request
    return new NextResponse(null, {
      status: 400,
      headers: {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "strict-origin-when-cross-origin",
      },
    });
  }

  // Lowercase
  let cleanPath = decodedPath.toLowerCase();

  // Collapse consecutive slashes: /api/v1//admin -> /api/v1/admin
  cleanPath = cleanPath.replace(/\/+/g, "/");

  // Resolve relative segments (./ and ../)
  const segments: string[] = [];
  for (const seg of cleanPath.split("/")) {
    if (seg === "" || seg === ".") continue;
    if (seg === "..") {
      segments.pop();
    } else {
      segments.push(seg);
    }
  }
  const normalizedPath = "/" + segments.join("/");

  // SECURITY.md T7: Block admin endpoints in production builds (return 404)
  if (
    normalizedPath.startsWith("/api/v1/admin") ||
    normalizedPath.startsWith("/api/admin")
  ) {
    if (process.env.NODE_ENV === "production") {
      return new NextResponse(null, {
        status: 404,
        headers: {
          "X-Content-Type-Options": "nosniff",
          "X-Frame-Options": "DENY",
          "Referrer-Policy": "strict-origin-when-cross-origin",
        },
      });
    }
  }

  // 2. Security Headers & Nonce Generation for Application Pages
  const nonce = Buffer.from(crypto.randomUUID()).toString("base64");
  const isDev = process.env.NODE_ENV === "development";

  const scriptSrc = isDev
    ? `'self' 'nonce-${nonce}' 'strict-dynamic' 'unsafe-eval'`
    : `'self' 'nonce-${nonce}' 'strict-dynamic'`;

  const cspHeader = `default-src 'self'; script-src ${scriptSrc}; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; media-src 'self' blob:; font-src 'self'; connect-src 'self'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'; object-src 'none';`;

  const requestHeaders = new Headers(request.headers);
  requestHeaders.set("x-nonce", nonce);
  requestHeaders.set("Content-Security-Policy", cspHeader);

  // Forward client identity headers to backend (defense in depth for verify_localhost_admin)
  const clientIp =
    request.headers.get("x-forwarded-for") ||
    request.headers.get("x-real-ip") ||
    request.headers.get("cf-connecting-ip") ||
    "127.0.0.1";
  requestHeaders.set("x-forwarded-for", clientIp);
  requestHeaders.set("x-forwarded-host", request.headers.get("host") || "localhost");

  const response = NextResponse.next({
    request: {
      headers: requestHeaders,
    },
  });

  response.headers.set("Content-Security-Policy", cspHeader);
  response.headers.set("X-Content-Type-Options", "nosniff");
  response.headers.set("X-Frame-Options", "DENY");
  response.headers.set("Referrer-Policy", "strict-origin-when-cross-origin");
  response.headers.set(
    "Permissions-Policy",
    "camera=(self), microphone=(), geolocation=(), interest-cohort=()"
  );
  response.headers.set("Cross-Origin-Opener-Policy", "same-origin");

  return response;
}

export const config = {
  matcher: [
    /*
     * Match all request paths including /api routes, excluding only:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico, sitemap.xml, robots.txt
     */
    {
      source:
        "/((?!_next/static|_next/image|favicon.ico|sitemap.xml|robots.txt).*)",
      missing: [
        { type: "header", key: "next-router-prefetch" },
        { type: "header", key: "purpose", value: "prefetch" },
      ],
    },
  ],
};
