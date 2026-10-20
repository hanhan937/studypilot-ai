
const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

type CsrfResponse = {
  csrfToken: string;
};

let csrfTokenPromise: Promise<string> | null = null;

async function getCsrfToken(): Promise<string> {
  if (!csrfTokenPromise) {
    csrfTokenPromise = fetch(`${API_BASE_URL}/api/csrf/`, {
      credentials: "include",
    })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error("Failed to initialize CSRF protection.");
        }

        const data = (await response.json()) as CsrfResponse;
        if (!data.csrfToken) {
          throw new Error("CSRF token was not returned.");
        }

        return data.csrfToken;
      })
      .catch((error: unknown) => {
        csrfTokenPromise = null;
        throw error;
      });
  }

  return csrfTokenPromise;
}

export async function apiRequest(
  url: string,
  options: RequestInit = {},
) {
  const method = (options.method ?? "GET").toUpperCase();
  const headers = new Headers(options.headers);

  if (!["GET", "HEAD", "OPTIONS"].includes(method)) {
    const csrfToken = await getCsrfToken();
    headers.set("X-CSRFToken", csrfToken);
  }

  const response = await fetch(`${API_BASE_URL}${url}`, {
    ...options,
    method,
    headers,
    credentials: "include",
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.error ?? `Request failed (${response.status}).`);
  }

  return data;
}

