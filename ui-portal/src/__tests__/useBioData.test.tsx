import { renderHook, waitFor } from "@testing-library/react";
import { useBioData } from "@/hooks/useBioData";
import { bioService } from "@/services/bioService";

jest.mock("@/services/bioService", () => ({
  bioService: {
    fetchTriplets: jest.fn(),
  },
}));

const mockedBioService = bioService as jest.Mocked<typeof bioService>;

describe("useBioData hook", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("fetches the selected organ graph and exposes loaded state", async () => {
    mockedBioService.fetchTriplets.mockResolvedValue({
      edges: [],
      nodes: [{ id: "gene-cyp3a4", label: "CYP3A4", type: "Gene" }],
    });

    const { result } = renderHook(() => useBioData("liver"));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.isError).toBe(false);
    expect(result.current.data?.nodes).toHaveLength(1);
    expect(mockedBioService.fetchTriplets).toHaveBeenCalledWith(
      "liver",
      expect.objectContaining({ signal: expect.any(AbortSignal) })
    );
  });

  it("exposes error state when fetch fails", async () => {
    mockedBioService.fetchTriplets.mockRejectedValue(new Error("Gateway unavailable"));

    const { result } = renderHook(() => useBioData("liver"));

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error?.message).toBe("Gateway unavailable");
  });
});
