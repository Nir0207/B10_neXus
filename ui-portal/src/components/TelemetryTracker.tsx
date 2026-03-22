"use client";

import { useEffect, useRef } from "react";
import { usePathname } from "next/navigation";
import { useAuth } from "@/components/AuthProvider";
import { buildClientTelemetryProfile, getOrCreateTelemetrySessionId } from "@/lib/telemetry";
import { recordTelemetryEvent } from "@/services/telemetryService";

function sanitizeLabel(value: string | null | undefined): string | null {
  if (!value) {
    return null;
  }

  const trimmedValue = value.trim().replace(/\s+/g, " ");
  return trimmedValue ? trimmedValue.slice(0, 120) : null;
}

export default function TelemetryTracker(): null {
  const pathname = usePathname();
  const { isAuthenticated, isReady, session } = useAuth();
  const lastTrackedPathRef = useRef<string>("");

  useEffect(() => {
    if (!isReady || !isAuthenticated || !session?.token || !pathname) {
      return;
    }

    if (lastTrackedPathRef.current === pathname) {
      return;
    }

    lastTrackedPathRef.current = pathname;
    const sessionId = getOrCreateTelemetrySessionId();
    const profile = buildClientTelemetryProfile();

    void recordTelemetryEvent(
      {
        eventType: "page_view",
        route: pathname,
        sessionId,
        label: pathname,
        browserName: profile.browserName,
        osName: profile.osName,
        deviceType: profile.deviceType,
        language: profile.language,
        timezone: profile.timezone,
        referrer: profile.referrer,
        screenWidth: profile.screenWidth,
        screenHeight: profile.screenHeight,
        metadata: {
          source: "ui-portal",
        },
      },
      session.token,
    ).catch(() => undefined);
  }, [isAuthenticated, isReady, pathname, session?.token]);

  useEffect(() => {
    if (!isReady || !isAuthenticated || !session?.token) {
      return;
    }

    const handleClick = (event: MouseEvent): void => {
      const target = event.target;
      if (!(target instanceof Element)) {
        return;
      }

      const interactiveElement = target.closest("button, a, [data-telemetry-label]");
      if (!(interactiveElement instanceof HTMLElement)) {
        return;
      }

      const label =
        sanitizeLabel(interactiveElement.dataset.telemetryLabel) ??
        sanitizeLabel(interactiveElement.getAttribute("aria-label")) ??
        sanitizeLabel(interactiveElement.textContent) ??
        sanitizeLabel(interactiveElement.getAttribute("href")) ??
        interactiveElement.tagName.toLowerCase();

      const hrefValue =
        interactiveElement instanceof HTMLAnchorElement
          ? interactiveElement.getAttribute("href")
          : null;
      const profile = buildClientTelemetryProfile();

      void recordTelemetryEvent(
        {
          eventType: "click",
          route: pathname,
          sessionId: getOrCreateTelemetrySessionId(),
          label,
          browserName: profile.browserName,
          osName: profile.osName,
          deviceType: profile.deviceType,
          language: profile.language,
          timezone: profile.timezone,
          referrer: profile.referrer,
          screenWidth: profile.screenWidth,
          screenHeight: profile.screenHeight,
          metadata: {
            href: hrefValue,
            tagName: interactiveElement.tagName.toLowerCase(),
          },
        },
        session.token,
      ).catch(() => undefined);
    };

    document.addEventListener("click", handleClick, true);
    return () => {
      document.removeEventListener("click", handleClick, true);
    };
  }, [isAuthenticated, isReady, pathname, session?.token]);

  return null;
}
