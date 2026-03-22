"use client";

const TELEMETRY_SESSION_KEY = "bionexus.telemetry.session";

function canUseStorage(): boolean {
  return typeof window !== "undefined" && typeof window.localStorage !== "undefined";
}

function inferBrowserName(userAgent: string): string {
  if (/edg/i.test(userAgent)) {
    return "Edge";
  }
  if (/chrome|crios/i.test(userAgent)) {
    return "Chrome";
  }
  if (/safari/i.test(userAgent) && !/chrome|crios/i.test(userAgent)) {
    return "Safari";
  }
  if (/firefox|fxios/i.test(userAgent)) {
    return "Firefox";
  }
  return "Unknown";
}

function inferOsName(userAgent: string): string {
  if (/windows/i.test(userAgent)) {
    return "Windows";
  }
  if (/mac os|macintosh/i.test(userAgent)) {
    return "macOS";
  }
  if (/android/i.test(userAgent)) {
    return "Android";
  }
  if (/iphone|ipad|ios/i.test(userAgent)) {
    return "iOS";
  }
  if (/linux/i.test(userAgent)) {
    return "Linux";
  }
  return "Unknown";
}

function inferDeviceType(userAgent: string, width: number): string {
  if (/tablet|ipad/i.test(userAgent)) {
    return "tablet";
  }
  if (/mobile|iphone|android/i.test(userAgent) || width < 768) {
    return "mobile";
  }
  return "desktop";
}

export function getOrCreateTelemetrySessionId(): string {
  if (!canUseStorage()) {
    return "server-session";
  }

  const existingSessionId = window.localStorage.getItem(TELEMETRY_SESSION_KEY);
  if (existingSessionId) {
    return existingSessionId;
  }

  const nextSessionId =
    typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
      ? crypto.randomUUID()
      : `telemetry-${Date.now()}`;

  window.localStorage.setItem(TELEMETRY_SESSION_KEY, nextSessionId);
  return nextSessionId;
}

export function buildClientTelemetryProfile(): {
  browserName: string;
  osName: string;
  deviceType: string;
  language: string | null;
  timezone: string | null;
  referrer: string | null;
  screenWidth: number | null;
  screenHeight: number | null;
} {
  if (typeof window === "undefined" || typeof navigator === "undefined") {
    return {
      browserName: "Unknown",
      osName: "Unknown",
      deviceType: "desktop",
      language: null,
      timezone: null,
      referrer: null,
      screenWidth: null,
      screenHeight: null,
    };
  }

  const userAgent = navigator.userAgent ?? "";
  const width = window.innerWidth ?? null;
  const height = window.innerHeight ?? null;

  return {
    browserName: inferBrowserName(userAgent),
    osName: inferOsName(userAgent),
    deviceType: width ? inferDeviceType(userAgent, width) : "desktop",
    language: navigator.language ?? null,
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone ?? null,
    referrer: document.referrer || null,
    screenWidth: width,
    screenHeight: height,
  };
}
