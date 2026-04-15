use anyhow::Result;

use crate::{
    error::invalid_state,
    models::{ReviewCommentItemRead, ReviewRoundSummaryRead},
    notes::NoteTemplateContext,
};

#[derive(Debug, Clone)]
pub struct GeneratedReviewNoteContent {
    pub template_kind: String,
    pub title: String,
    pub content: String,
}

const REVIEW_ROUND_STATUSES: [&str; 2] = ["open", "archived"];
const REVIEW_DISPOSITIONS: [&str; 5] = ["todo", "accepted", "rebutted", "not_applicable", "done"];

pub fn validate_review_round_status(status: &str) -> Result<String> {
    validate_membership(status, &REVIEW_ROUND_STATUSES, "review round status")
}

pub fn validate_review_disposition(disposition: &str) -> Result<String> {
    validate_membership(
        disposition,
        &REVIEW_DISPOSITIONS,
        "review comment disposition",
    )
}

pub fn default_review_disposition() -> String {
    "todo".to_string()
}

pub fn render_reviewer_matrix_note(
    context: &NoteTemplateContext,
    round: &ReviewRoundSummaryRead,
    comments: &[ReviewCommentItemRead],
) -> GeneratedReviewNoteContent {
    let title = format!("Reviewer Matrix - {}", round.round_label);
    let mut output = String::new();
    output.push_str("# Reviewer Matrix\n\n");
    output.push_str(&render_header(context, round));
    output.push_str("\n## Reviewer Overview\n\n");
    if comments.is_empty() {
        output.push_str("- No reviewer comments have been recorded yet.\n");
    } else {
        for (reviewer_label, reviewer_comments) in grouped_comments(comments) {
            output.push_str(&format!("### {reviewer_label}\n\n"));
            for comment in reviewer_comments {
                output.push_str(&render_matrix_comment(comment));
            }
        }
    }

    GeneratedReviewNoteContent {
        template_kind: "reviewer_matrix".to_string(),
        title,
        content: output,
    }
}

pub fn render_response_letter_note(
    context: &NoteTemplateContext,
    round: &ReviewRoundSummaryRead,
    comments: &[ReviewCommentItemRead],
) -> GeneratedReviewNoteContent {
    let title = format!("Response Letter - {}", round.round_label);
    let venue = context.venue.as_deref().unwrap_or("-");
    let mut output = String::new();
    output.push_str("# Response Letter Draft\n\n");
    output.push_str(&format!(
        "Dear Editor,\n\nThank you for the opportunity to revise **{}** for **{}**. \
Below we provide a point-by-point response for review round **{}**.\n\n",
        context.paper_title, venue, round.round_label
    ));
    output.push_str(&render_header(context, round));
    output.push('\n');

    if comments.is_empty() {
        output.push_str(
            "## Reviewer Responses\n\n- No reviewer comments have been recorded yet.\n\n",
        );
    } else {
        for (reviewer_label, reviewer_comments) in grouped_comments(comments) {
            output.push_str(&format!("## {reviewer_label}\n\n"));
            for comment in reviewer_comments {
                output.push_str(&render_response_comment(comment));
            }
        }
    }

    output.push_str("Sincerely,\n\n- Corresponding author\n");

    GeneratedReviewNoteContent {
        template_kind: "response_letter".to_string(),
        title,
        content: output,
    }
}

fn render_header(context: &NoteTemplateContext, round: &ReviewRoundSummaryRead) -> String {
    let venue = round
        .venue
        .as_deref()
        .or(context.venue.as_deref())
        .unwrap_or("-");
    let decision = round.decision_label.as_deref().unwrap_or("-");
    let next_action = context.next_action.as_deref().unwrap_or("-");
    let blocker = context.blocker.as_deref().unwrap_or("-");
    format!(
        "- Paper: {}\n- Paper ID: {}\n- Stage: {}\n- Venue: {}\n- Review Round: {}\n- Decision: {}\n- Next Action: {}\n- Blocker: {}\n",
        context.paper_title,
        context.paper_id,
        context.stage,
        venue,
        round.round_label,
        decision,
        next_action,
        blocker
    )
}

fn render_matrix_comment(comment: &ReviewCommentItemRead) -> String {
    let code = comment.comment_code.as_deref().unwrap_or("-");
    let category = comment.category.as_deref().unwrap_or("-");
    let response_summary = non_empty_or_placeholder(
        comment.response_summary.as_deref(),
        "_Response summary pending._",
    );
    let action_note =
        non_empty_or_placeholder(comment.action_note.as_deref(), "_Action note pending._");
    format!(
        "#### {} ({})\n\n- Category: {}\n- Disposition: {}\n- Comment:\n\n{}\n\n- Response Summary:\n\n{}\n\n- Action Note:\n\n{}\n\n",
        comment.reviewer_label,
        code,
        category,
        comment.disposition,
        indent_markdown(comment.comment_text.trim()),
        response_summary,
        action_note
    )
}

fn render_response_comment(comment: &ReviewCommentItemRead) -> String {
    let code = comment.comment_code.as_deref().unwrap_or("-");
    let response_summary = non_empty_or_placeholder(
        comment.response_summary.as_deref(),
        "_Response summary placeholder: add the planned response here._",
    );
    let action_note =
        non_empty_or_placeholder(comment.action_note.as_deref(), "_Action note pending._");
    format!(
        "### Comment {} \n\n**Reviewer comment**\n\n{}\n\n**Disposition**: {}\n\n**Response**\n\n{}\n\n**Action note**\n\n{}\n\n",
        code,
        indent_markdown(comment.comment_text.trim()),
        comment.disposition,
        response_summary,
        action_note
    )
}

fn grouped_comments(
    comments: &[ReviewCommentItemRead],
) -> Vec<(&str, Vec<&ReviewCommentItemRead>)> {
    let mut groups: Vec<(&str, Vec<&ReviewCommentItemRead>)> = Vec::new();
    for comment in comments {
        if let Some((_, grouped)) = groups
            .iter_mut()
            .find(|(label, _)| label.eq_ignore_ascii_case(comment.reviewer_label.as_str()))
        {
            grouped.push(comment);
        } else {
            groups.push((comment.reviewer_label.as_str(), vec![comment]));
        }
    }
    groups
}

fn validate_membership(value: &str, allowed: &[&str], label: &str) -> Result<String> {
    let normalized = value.trim().to_string();
    if allowed.contains(&normalized.as_str()) {
        Ok(normalized)
    } else {
        Err(invalid_state(format!(
            "{label} must be one of: {}",
            allowed.join(", ")
        )))
    }
}

fn non_empty_or_placeholder(value: Option<&str>, placeholder: &str) -> String {
    value
        .map(str::trim)
        .filter(|text| !text.is_empty())
        .map(ToString::to_string)
        .unwrap_or_else(|| placeholder.to_string())
}

fn indent_markdown(value: &str) -> String {
    value
        .lines()
        .map(|line| format!("> {}", line.trim_end()))
        .collect::<Vec<_>>()
        .join("\n")
}

#[cfg(test)]
mod tests {
    use super::{
        render_response_letter_note, render_reviewer_matrix_note, validate_review_disposition,
        validate_review_round_status,
    };
    use crate::{
        models::{ReviewCommentItemRead, ReviewRoundSummaryRead},
        notes::NoteTemplateContext,
    };

    fn context() -> NoteTemplateContext {
        NoteTemplateContext {
            paper_id: "paper-1".to_string(),
            paper_title: "Structured Revision".to_string(),
            stage: "revision".to_string(),
            venue: Some("JOM".to_string()),
            next_action: Some("Prepare response package".to_string()),
            blocker: None,
        }
    }

    fn round() -> ReviewRoundSummaryRead {
        ReviewRoundSummaryRead {
            id: "round-1".to_string(),
            paper_id: "paper-1".to_string(),
            round_label: "Round 1".to_string(),
            venue: Some("JOM".to_string()),
            decision_label: Some("Major revision".to_string()),
            status: "open".to_string(),
            source_mode: "manual".to_string(),
            reviewer_count: 1,
            generated_response_note_id: None,
            generated_matrix_note_id: None,
            created_at: "2026-04-15T10:00:00Z".to_string(),
            updated_at: "2026-04-15T10:00:00Z".to_string(),
        }
    }

    fn comment() -> ReviewCommentItemRead {
        ReviewCommentItemRead {
            id: "comment-1".to_string(),
            review_round_id: "round-1".to_string(),
            paper_id: "paper-1".to_string(),
            reviewer_label: "Reviewer 1".to_string(),
            comment_code: Some("R1-1".to_string()),
            sort_order: 1,
            comment_text: "Please clarify the experiment setup.".to_string(),
            category: Some("method".to_string()),
            disposition: "todo".to_string(),
            response_summary: Some("We will clarify the setup in Section 2.".to_string()),
            action_note: Some("Add experimental setup paragraph.".to_string()),
            created_at: "2026-04-15T10:00:00Z".to_string(),
            updated_at: "2026-04-15T10:00:00Z".to_string(),
        }
    }

    #[test]
    fn validates_round_status_and_disposition() {
        assert_eq!(validate_review_round_status("open").unwrap(), "open");
        assert_eq!(validate_review_disposition("done").unwrap(), "done");
        assert!(validate_review_round_status("closed").is_err());
        assert!(validate_review_disposition("pending").is_err());
    }

    #[test]
    fn renders_reviewer_matrix_with_structured_sections() {
        let rendered = render_reviewer_matrix_note(&context(), &round(), &[comment()]);
        assert!(rendered.content.contains("# Reviewer Matrix"));
        assert!(rendered.content.contains("Reviewer 1"));
        assert!(rendered
            .content
            .contains("Please clarify the experiment setup."));
        assert!(rendered
            .content
            .contains("Add experimental setup paragraph."));
    }

    #[test]
    fn response_letter_uses_visible_placeholder_when_summary_missing() {
        let mut missing_summary = comment();
        missing_summary.response_summary = None;
        let rendered = render_response_letter_note(&context(), &round(), &[missing_summary]);
        assert!(rendered.content.contains("Response summary placeholder"));
        assert!(rendered.content.contains("Dear Editor"));
    }
}
