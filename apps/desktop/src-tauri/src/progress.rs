pub fn derive_progress_percentage(paper_type: &str) -> i64 {
    match paper_type {
        "published" => 100,
        "revision" => 80,
        "under_review" => 65,
        "in_prep" => 35,
        "paused" => 0,
        _ => 0,
    }
}

#[cfg(test)]
mod tests {
    use super::derive_progress_percentage;

    #[test]
    fn mapping_matches_backend_read_model() {
        assert_eq!(derive_progress_percentage("published"), 100);
        assert_eq!(derive_progress_percentage("revision"), 80);
        assert_eq!(derive_progress_percentage("under_review"), 65);
        assert_eq!(derive_progress_percentage("in_prep"), 35);
        assert_eq!(derive_progress_percentage("paused"), 0);
    }
}
