import {
  buildConversionFilterQuery,
  buildConversionFilterSummaryViewModel,
  DEFAULT_CONVERSION_FILTER_INPUT,
  DEFAULT_CONVERSION_FILTER_LIMIT,
  GLOBAL_CONVERSION_FILTER_SUPPORT,
  normalizeConversionFilterInput,
} from "./conversionFilters";

describe("conversion filter helpers", () => {
  it("normalizes date ranges and clamps limit values", () => {
    expect(
      normalizeConversionFilterInput({
        ...DEFAULT_CONVERSION_FILTER_INPUT,
        dateFrom: "2026-04-20",
        dateTo: "2026-04-10",
        limit: 999,
      }),
    ).toEqual({
      ...DEFAULT_CONVERSION_FILTER_INPUT,
      dateFrom: "2026-04-10",
      dateTo: "2026-04-20",
      limit: 100,
    });
  });

  it("builds deterministic UTC filter queries", () => {
    expect(
      buildConversionFilterQuery(
        {
          dateFrom: "2026-04-01",
          dateTo: "2026-04-17",
          shareKind: "workspace_board",
          accessMode: "alias",
          eventType: "content_view",
          outcome: "resolved",
          limit: 50,
        },
        {
          includeDimensions: true,
          includeOutcome: true,
          includeLimit: true,
        },
      ).toString(),
    ).toBe(
      "date_from=2026-04-01T00%3A00%3A00.000Z&date_to=2026-04-17T23%3A59%3A59.999Z&share_kind=workspace_board&access_mode=alias&event_type=content_view&outcome=resolved&limit=50",
    );
  });

  it("builds active filter summary chips and scope notes", () => {
    expect(
      buildConversionFilterSummaryViewModel(
        {
          ...DEFAULT_CONVERSION_FILTER_INPUT,
          dateFrom: "2026-04-01",
          shareKind: "paper_snapshot",
          outcome: "rejected",
          limit: 10,
        },
        GLOBAL_CONVERSION_FILTER_SUPPORT,
      ),
    ).toMatchObject({
      hasActiveFilters: true,
      windowLabel: "2026-04-01 → now",
      chips: expect.arrayContaining([
        expect.objectContaining({ label: "Date from", value: "2026-04-01" }),
        expect.objectContaining({ label: "Share kind", value: "Paper snapshot" }),
        expect.objectContaining({ label: "Outcome", value: "Rejected" }),
        expect.objectContaining({ label: "Recent rows", value: "10" }),
      ]),
      scopeNotes: expect.arrayContaining([
        "Date window applies to overview and drilldown.",
        "Outcome applies to overview and drilldown.",
        "Recent rows limit applies to drilldown recent and top sections.",
      ]),
    });
  });

  it("keeps default filter summaries compact", () => {
    expect(
      buildConversionFilterSummaryViewModel(
        DEFAULT_CONVERSION_FILTER_INPUT,
        GLOBAL_CONVERSION_FILTER_SUPPORT,
      ),
    ).toEqual({
      windowLabel: "Default analytics window",
      chips: [],
      scopeNotes: [
        "Date window applies to overview and drilldown.",
        "Share kind, access mode, and event type apply to overview and drilldown.",
        "Outcome applies to overview and drilldown.",
        "Recent rows limit applies to drilldown recent and top sections.",
      ],
      hasActiveFilters: false,
    });
    expect(DEFAULT_CONVERSION_FILTER_LIMIT).toBe(20);
  });
});
