/* eslint-disable react-hooks/set-state-in-effect */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { bioService, type TripletData } from "@/services/bioService";

export interface UseBioNexusResult {
  data: TripletData | undefined;
  error: Error | null;
  isError: boolean;
  isFetching: boolean;
  isLoading: boolean;
  refetch: () => Promise<void>;
}

function toError(value: unknown): Error {
  if (value instanceof Error) {
    return value;
  }

  return new Error("Unknown API error");
}

export function useBioNexus(organType: string): UseBioNexusResult {
  const [data, setData] = useState<TripletData | undefined>();
  const [error, setError] = useState<Error | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isFetching, setIsFetching] = useState<boolean>(false);
  const [isError, setIsError] = useState<boolean>(false);
  const refreshCounterRef = useRef<number>(0);
  const hasDataRef = useRef<boolean>(false);
  const previousOrganRef = useRef<string>("");
  const [refreshCounter, setRefreshCounter] = useState<number>(0);

  useEffect(() => {
    hasDataRef.current = Boolean(data);
  }, [data]);

  useEffect(() => {
    const normalizedOrgan = organType.trim();
    if (!normalizedOrgan) {
      return;
    }

    const organChanged = previousOrganRef.current !== normalizedOrgan;
    if (organChanged) {
      previousOrganRef.current = normalizedOrgan;
      hasDataRef.current = false;
      setData(undefined);
    }

    const abortController = new AbortController();
    let isStale = false;

    setIsFetching(true);
    setIsLoading(!hasDataRef.current);
    setError(null);
    setIsError(false);

    void bioService
      .fetchTriplets(normalizedOrgan, { signal: abortController.signal })
      .then((nextData) => {
        if (isStale) {
          return;
        }
        setData(nextData);
        setIsError(false);
      })
      .catch((fetchError: unknown) => {
        if (isStale || abortController.signal.aborted) {
          return;
        }
        setError(toError(fetchError));
        setIsError(true);
      })
      .finally(() => {
        if (isStale) {
          return;
        }
        setIsFetching(false);
        setIsLoading(false);
      });

    return () => {
      isStale = true;
      abortController.abort();
    };
  }, [organType, refreshCounter]);

  const refetch = useCallback(async (): Promise<void> => {
    refreshCounterRef.current += 1;
    setRefreshCounter(refreshCounterRef.current);
  }, []);

  return useMemo(
    () => ({
      data,
      error,
      isError,
      isFetching,
      isLoading,
      refetch,
    }),
    [data, error, isError, isFetching, isLoading, refetch]
  );
}
