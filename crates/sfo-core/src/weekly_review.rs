use chrono::{DateTime, NaiveDate, Utc};
use serde::{Deserialize, Serialize};

use crate::{Project, ProjectCategory, ProjectId, TaskId, WhenBucket};

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct WeeklyReviewSummary {
    pub review_date: NaiveDate,
    pub week_starts_on: NaiveDate,
    pub focus_counts: WeeklyFocusCounts,
    pub weekly_projects: Vec<Project>,
    pub available_projects: Vec<Project>,
    pub resurface_due: Vec<WeeklyReviewTask>,
    pub completed_tasks: Vec<WeeklyReviewTask>,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct WeeklyFocusCounts {
    pub work: WeeklyFocusCount,
    pub personal: WeeklyFocusCount,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct WeeklyFocusCount {
    pub category: ProjectCategory,
    pub current: i64,
    pub cap: i64,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct WeeklyReviewTask {
    pub id: TaskId,
    pub title: String,
    pub description: Option<String>,
    pub when_bucket: WhenBucket,
    pub status: String,
    pub project_id: Option<ProjectId>,
    pub project_title: Option<String>,
    pub resurface_on: Option<NaiveDate>,
    pub completed_at: Option<DateTime<Utc>>,
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{ProjectCategory, TaskId, WhenBucket};
    use chrono::NaiveDate;

    #[test]
    fn weekly_review_summary_serializes_counts_and_rows() {
        let task_id = TaskId::new();
        let summary = WeeklyReviewSummary {
            review_date: NaiveDate::from_ymd_opt(2026, 5, 10).unwrap(),
            week_starts_on: NaiveDate::from_ymd_opt(2026, 5, 4).unwrap(),
            focus_counts: WeeklyFocusCounts {
                work: WeeklyFocusCount {
                    category: ProjectCategory::Work,
                    current: 3,
                    cap: 4,
                },
                personal: WeeklyFocusCount {
                    category: ProjectCategory::Personal,
                    current: 2,
                    cap: 3,
                },
            },
            weekly_projects: vec![],
            available_projects: vec![],
            resurface_due: vec![WeeklyReviewTask {
                id: task_id,
                title: "Write outline".to_string(),
                description: None,
                when_bucket: WhenBucket::Month,
                status: "pending".to_string(),
                project_id: None,
                project_title: None,
                resurface_on: Some(NaiveDate::from_ymd_opt(2026, 5, 10).unwrap()),
                completed_at: None,
            }],
            completed_tasks: vec![],
        };

        let json = serde_json::to_value(summary).expect("serialize weekly review");

        assert_eq!(json["review_date"], "2026-05-10");
        assert_eq!(json["week_starts_on"], "2026-05-04");
        assert_eq!(json["focus_counts"]["work"]["current"], 3);
        assert_eq!(json["focus_counts"]["personal"]["cap"], 3);
        assert_eq!(json["resurface_due"][0]["id"], task_id.to_string());
        assert_eq!(json["resurface_due"][0]["when_bucket"], "month");
    }
}
