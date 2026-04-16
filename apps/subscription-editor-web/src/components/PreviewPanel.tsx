import {
  buildPreviewDisplayModel,
  buildSaveDisplayModel,
} from "@research-pulse/subscription-editor-core";
import type {
  SubscriptionSettingsPreviewRead,
  SubscriptionSettingsSaveResultRead,
} from "@research-pulse/subscription-editor-core";

type PreviewPanelProps = {
  preview: SubscriptionSettingsPreviewRead | null;
  previewStale: boolean;
  saveResult: SubscriptionSettingsSaveResultRead | null;
  saveResultStale: boolean;
};

export function PreviewPanel({
  preview,
  previewStale,
  saveResult,
  saveResultStale,
}: PreviewPanelProps) {
  const previewModel = preview
    ? buildPreviewDisplayModel(preview.authoritative_preview)
    : null;
  const saveModel = saveResult ? buildSaveDisplayModel(saveResult) : null;

  return (
    <section className="editor-card">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Authoritative Preview</p>
          <h2>Preview & save feedback</h2>
        </div>
      </div>

      {preview === null ? (
        <div className="empty-state">
          Run “Preview changes” to inspect the current server-authoritative delivery decision.
        </div>
      ) : (
        <div className="preview-panel" data-testid="preview-panel">
          {previewStale ? (
            <div className="inline-banner warning">
              Unsaved local edits differ from the last preview result. Preview again before saving.
            </div>
          ) : null}
          <dl className="preview-grid">
            <div>
              <dt>Preview state</dt>
              <dd>{previewModel?.state ?? "Unavailable"}</dd>
            </div>
            <div>
              <dt>Decision</dt>
              <dd>{previewModel?.decisionLabel ?? "Unavailable"}</dd>
            </div>
            <div>
              <dt>Reason codes</dt>
              <dd>{previewModel?.reasonCodes.join(", ") || "None"}</dd>
            </div>
            <div>
              <dt>Current local time</dt>
              <dd>{previewModel?.currentLocalTimeLabel ?? "Unavailable"}</dd>
            </div>
            <div>
              <dt>Local weekday</dt>
              <dd>{previewModel?.localWeekdayLabel ?? "Unavailable"}</dd>
            </div>
            <div>
              <dt>Next allowed at</dt>
              <dd>{previewModel?.nextAllowedAtLabel ?? "Unavailable"}</dd>
            </div>
            <div className="span-all">
              <dt>Latest digest summary</dt>
              <dd>{previewModel?.latestDigestLabel ?? "Unavailable"}</dd>
            </div>
          </dl>
          <div>
            <p className="eyebrow">Normalized control policy</p>
            <pre className="json-block">
              {previewModel?.normalizedControlPolicyText ?? "{}"}
            </pre>
          </div>
        </div>
      )}

      <div className="divider" />

      <div>
        <p className="eyebrow">Save result</p>
        {saveModel === null ? (
          <div className="empty-state">
            Saved server state will appear here after a successful PATCH request.
          </div>
        ) : (
          <div className="save-result" data-testid="save-result-panel">
            {saveResultStale ? (
              <div className="inline-banner warning">
                Local edits now differ from the last saved server state.
              </div>
            ) : (
              <div className="inline-banner success">{saveModel.summary}</div>
            )}
            <dl className="preview-grid compact">
              <div>
                <dt>Changed fields</dt>
                <dd>{saveModel.changedFields.join(", ") || "None"}</dd>
              </div>
              <div>
                <dt>Timezone</dt>
                <dd>{saveModel.savedSettings.timezone}</dd>
              </div>
              <div>
                <dt>Allowed weekdays</dt>
                <dd>{saveModel.savedSettings.allowed_weekdays.join(", ") || "Any"}</dd>
              </div>
              <div>
                <dt>Minimum selected cards</dt>
                <dd>
                  {saveModel.savedSettings.minimum_selected_cards === null
                    ? "Not set"
                    : saveModel.savedSettings.minimum_selected_cards}
                </dd>
              </div>
            </dl>
          </div>
        )}
      </div>
    </section>
  );
}
