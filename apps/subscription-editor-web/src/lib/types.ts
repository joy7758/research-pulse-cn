export type ChannelType = "official_account" | string;
export type GrantStatus = "active" | "revoked" | "expired" | string;
export type HandoffIssuedBy = "mini_handoff" | "admin" | string;
export type BindingState = "active" | "inactive" | "revoked" | string;
export type DeliveryDecisionStatus = "eligible" | "skipped" | string;
export type PreviewState = "ready" | "no_digest_context" | "invalid_input" | string;

export type EditorFieldId =
  | "channel"
  | "enabled"
  | "quiet_hours"
  | "timezone"
  | "allowed_weekdays"
  | "muted_until"
  | "minimum_selected_cards"
  | "skip_if_no_today_focus"
  | "official_account_binding_summary"
  | "latest_digest_summary"
  | "authoritative_preview_supported"
  | "self_service_grant_status";

export type SubscriptionEditorHandoffGrantRead = {
  id: string;
  user_id: string;
  channel: ChannelType;
  binding_id: string | null;
  mini_grant_id: string | null;
  self_service_grant_id: string;
  status: GrantStatus;
  display_label: string | null;
  issued_by: HandoffIssuedBy;
  expires_at: string | null;
  last_used_at: string | null;
  created_at: string;
  updated_at: string;
};

export type SubscriptionEditorLinkedSelfServiceGrantRead = {
  id: string;
  channel: ChannelType;
  binding_id: string | null;
  status: GrantStatus;
  display_label: string | null;
  expires_at: string | null;
  last_used_at: string | null;
  created_at: string;
};

export type SafeUserSummaryRead = {
  id: string;
  name: string;
  email: string | null;
  field: string | null;
};

export type SafeBindingSummaryRead = {
  id: string;
  channel_type: string;
  app_id: string;
  display_label: string | null;
  bind_state: BindingState;
  subscribed: boolean;
  digest_enabled: boolean;
  subscribed_at: string | null;
  unsubscribed_at: string | null;
  last_seen_at: string | null;
};

export type DigestSummaryRead = {
  id: string;
  issue_date: string;
  status: string;
  title: string;
  summary: string;
  selected_card_count: number;
  deep_link_path: string | null;
};

export type QuietHoursWindowRead = {
  start: string;
  end: string;
  timezone: string;
};

export type SubscriptionSettingsDraftRead = {
  subscription_policy_id: string | null;
  user_id: string | null;
  channel: ChannelType;
  enabled: boolean;
  quiet_hours: {
    timezone?: string;
    windows?: QuietHoursWindowRead[];
  } | null;
  timezone: string;
  allowed_weekdays: number[];
  muted_until: string | null;
  minimum_selected_cards: number | null;
  skip_if_no_today_focus: boolean;
  updated_at: string | null;
  self_service_grant_status: GrantStatus;
};

export type SubscriptionEditorFieldRead = {
  field_id: EditorFieldId;
  label: string;
  value_type: string;
  editable: boolean;
  required: boolean;
  nullable: boolean;
  description: string | null;
  validation_hints: Record<string, unknown>;
};

export type SubscriptionEditorSectionRead = {
  section_id: string;
  title: string;
  description: string | null;
  editable: boolean;
  field_ids: EditorFieldId[];
};

export type SubscriptionSelfServiceEditorContractRead = {
  contract_version: string;
  channel: ChannelType;
  editable_section_ids: string[];
  weekday_numbering_note: string;
  sections: SubscriptionEditorSectionRead[];
  fields: SubscriptionEditorFieldRead[];
};

export type SubscriptionSettingsValidationIssueRead = {
  field_id: string;
  code: string;
  message: string;
};

export type SubscriptionSettingsAuthoritativePreviewRead = {
  state: PreviewState;
  decision: DeliveryDecisionStatus | null;
  reason_codes: string[];
  normalized_control_policy: Record<string, unknown> | null;
  current_local_time: string | null;
  local_weekday: number | null;
  next_allowed_at: string | null;
  latest_digest_issue: DigestSummaryRead | null;
};

export type SubscriptionSettingsPreviewRead = {
  contract_version: string;
  normalized_draft: SubscriptionSettingsDraftRead;
  changed_fields: string[];
  validation_errors: SubscriptionSettingsValidationIssueRead[];
  validation_warnings: SubscriptionSettingsValidationIssueRead[];
  authoritative_preview: SubscriptionSettingsAuthoritativePreviewRead;
};

export type SubscriptionSettingsSaveResultRead = {
  contract_version: string;
  saved_settings: Omit<SubscriptionSettingsDraftRead, "self_service_grant_status">;
  changed_fields: string[];
  authoritative_preview: SubscriptionSettingsAuthoritativePreviewRead | null;
};

export type SubscriptionEditorBootstrapRead = {
  contract_version: string;
  handoff_grant: SubscriptionEditorHandoffGrantRead;
  linked_self_service_grant: SubscriptionEditorLinkedSelfServiceGrantRead | null;
  user: SafeUserSummaryRead;
  official_account_binding_summary: SafeBindingSummaryRead | null;
  current_settings_draft: SubscriptionSettingsDraftRead;
  latest_digest_summary: DigestSummaryRead | null;
  authoritative_preview_supported: boolean;
  supported_editor_endpoints: string[];
  notes: string[];
};

export type SubscriptionEditorSettingsPatchInput = {
  enabled?: unknown;
  quiet_hours?: unknown;
  timezone?: unknown;
  allowed_weekdays?: unknown;
  muted_until?: unknown;
  minimum_selected_cards?: unknown;
  skip_if_no_today_focus?: unknown;
};

export type ApiValidationErrorRead = {
  detail: string;
  errors?: SubscriptionSettingsValidationIssueRead[];
};

export type QuietHoursWindowDraft = {
  id: string;
  start: string;
  end: string;
};

export type EditorFormState = {
  enabled: boolean;
  timezone: string;
  quietHoursWindows: QuietHoursWindowDraft[];
  allowedWeekdays: number[];
  mutedUntil: string;
  minimumSelectedCards: string;
  skipIfNoTodayFocus: boolean;
};

export type PreviewDisplayModel = {
  state: PreviewState;
  decisionLabel: string;
  reasonCodes: string[];
  normalizedControlPolicyText: string;
  currentLocalTimeLabel: string;
  localWeekdayLabel: string;
  nextAllowedAtLabel: string;
  latestDigestLabel: string;
};

export type SaveDisplayModel = {
  summary: string;
  changedFields: string[];
  savedSettings: Omit<SubscriptionSettingsDraftRead, "self_service_grant_status">;
  authoritativePreview: SubscriptionSettingsAuthoritativePreviewRead | null;
};

export type SubscriptionEditorApiErrorShape = {
  status: number | null;
  detail: string;
  fieldErrors: SubscriptionSettingsValidationIssueRead[];
  body: unknown;
};
