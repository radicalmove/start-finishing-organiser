use sfo_core::{GlobalSearchResults, SearchResult, SearchResultKind};
use sqlx::FromRow;

use crate::DbError;

const DEFAULT_SEARCH_LIMIT: i64 = 30;

pub async fn global_search(
    pool: &sqlx::SqlitePool,
    query: &str,
    include_recycle_bin: bool,
) -> Result<GlobalSearchResults, DbError> {
    let query = normalize_query(query);
    if query.is_empty() {
        return Ok(GlobalSearchResults {
            query,
            include_recycle_bin,
            items: vec![],
        });
    }

    let pattern = like_pattern(&query);
    let mut sql = String::from(
        r#"
        SELECT * FROM (
          SELECT
            id,
            'project' AS kind,
            title,
            COALESCE(description, why_link_text) AS description,
            'Project' AS location,
            0 AS recycled,
            created_at,
            10 AS rank
          FROM projects
          WHERE status != 'archived'
            AND (
              LOWER(title) LIKE ? ESCAPE '\'
              OR LOWER(COALESCE(description, '')) LIKE ? ESCAPE '\'
              OR LOWER(COALESCE(why_link_text, '')) LIKE ? ESCAPE '\'
            )

          UNION ALL

          SELECT
            id,
            'task' AS kind,
            verb_noun AS title,
            description,
            CASE
              WHEN in_inbox = 1 THEN 'Inbox'
              WHEN intake_container = 'learn_explore' THEN 'Learning'
              WHEN intake_container = 'enjoy_recover' THEN 'Enjoy'
              WHEN intake_container = 'park_let_go' AND parked_until IS NOT NULL THEN 'Parked until'
              WHEN intake_container = 'park_let_go' THEN 'Parked'
              WHEN status = 'done' THEN 'Completed Task'
              ELSE 'Task'
            END AS location,
            0 AS recycled,
            created_at,
            20 AS rank
          FROM tasks
          WHERE archived_from_inbox = 0
            AND status != 'archived'
            AND (
              LOWER(verb_noun) LIKE ? ESCAPE '\'
              OR LOWER(COALESCE(description, '')) LIKE ? ESCAPE '\'
            )

          UNION ALL

          SELECT
            id,
            'waiting' AS kind,
            description AS title,
            person AS description,
            'Waiting On' AS location,
            0 AS recycled,
            created_at,
            30 AS rank
          FROM waiting_on
          WHERE LOWER(description) LIKE ? ESCAPE '\'
            OR LOWER(COALESCE(person, '')) LIKE ? ESCAPE '\'
        "#,
    );

    if include_recycle_bin {
        sql.push_str(
            r#"
          UNION ALL

          SELECT
            id,
            'recycle_bin' AS kind,
            verb_noun AS title,
            description,
            'Recycle Bin' AS location,
            1 AS recycled,
            created_at,
            90 AS rank
          FROM tasks
          WHERE archived_from_inbox = 1
            AND status = 'archived'
            AND (
              LOWER(verb_noun) LIKE ? ESCAPE '\'
              OR LOWER(COALESCE(description, '')) LIKE ? ESCAPE '\'
            )
        "#,
        );
    }

    sql.push_str(
        r#"
        )
        ORDER BY rank ASC, created_at DESC
        LIMIT ?
        "#,
    );

    let mut query_builder = sqlx::query_as::<_, SearchResultRow>(&sql);
    for _ in 0..7 {
        query_builder = query_builder.bind(&pattern);
    }
    if include_recycle_bin {
        for _ in 0..2 {
            query_builder = query_builder.bind(&pattern);
        }
    }
    query_builder = query_builder.bind(DEFAULT_SEARCH_LIMIT);

    let rows = query_builder.fetch_all(pool).await?;
    let items = rows
        .into_iter()
        .map(SearchResult::try_from)
        .collect::<Result<Vec<_>, _>>()?;

    Ok(GlobalSearchResults {
        query,
        include_recycle_bin,
        items,
    })
}

#[derive(Debug, FromRow)]
struct SearchResultRow {
    id: String,
    kind: String,
    title: String,
    description: Option<String>,
    location: String,
    recycled: i64,
    created_at: Option<String>,
}

impl TryFrom<SearchResultRow> for SearchResult {
    type Error = DbError;

    fn try_from(row: SearchResultRow) -> Result<Self, Self::Error> {
        Ok(Self {
            id: row.id,
            kind: parse_kind(&row.kind)?,
            title: row.title,
            description: row.description,
            location: row.location,
            recycled: row.recycled != 0,
            created_at: row.created_at,
        })
    }
}

fn parse_kind(value: &str) -> Result<SearchResultKind, DbError> {
    match value {
        "project" => Ok(SearchResultKind::Project),
        "task" => Ok(SearchResultKind::Task),
        "waiting" => Ok(SearchResultKind::Waiting),
        "recycle_bin" => Ok(SearchResultKind::RecycleBin),
        _ => Err(DbError::InvalidData(format!(
            "invalid search result kind {value}"
        ))),
    }
}

fn normalize_query(value: &str) -> String {
    value.trim().to_lowercase()
}

fn like_pattern(value: &str) -> String {
    let mut escaped = String::with_capacity(value.len());
    for character in value.chars() {
        match character {
            '%' | '_' | '\\' => {
                escaped.push('\\');
                escaped.push(character);
            }
            _ => escaped.push(character),
        }
    }
    format!("%{escaped}%")
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::planning::{create_task, update_task};
    use crate::waiting::create_waiting_on;
    use crate::{connect, run_migrations, DbConfig};
    use sfo_core::{TaskCreate, TaskStatus, WaitingOnCreate, WhenBucket};

    async fn migrated_pool() -> sqlx::SqlitePool {
        let pool = connect(&DbConfig::new("sqlite::memory:"))
            .await
            .expect("connect");
        run_migrations(&pool).await.expect("migrate");
        pool
    }

    #[tokio::test]
    async fn search_excludes_recycle_bin_until_requested() {
        let pool = migrated_pool().await;
        create_task(
            &pool,
            TaskCreate {
                verb_noun: "Renew passport".to_string(),
                project_id: None,
                description: None,
                in_inbox: true,
                when_bucket: WhenBucket::Later,
                block_type: None,
                duration_minutes: None,
                priority: None,
                frog: false,
                alignment: None,
                first_action: None,
                scheduled_for: None,
                owner_type: Default::default(),
            },
        )
        .await
        .expect("active task");
        let mut recycled = create_task(
            &pool,
            TaskCreate {
                verb_noun: "Passport duplicate".to_string(),
                project_id: None,
                description: None,
                in_inbox: false,
                when_bucket: WhenBucket::Later,
                block_type: None,
                duration_minutes: None,
                priority: None,
                frog: false,
                alignment: None,
                first_action: None,
                scheduled_for: None,
                owner_type: Default::default(),
            },
        )
        .await
        .expect("recycled task");
        recycled.archived_from_inbox = true;
        recycled.status = TaskStatus::Archived;
        update_task(&pool, &recycled)
            .await
            .expect("update recycled task");
        create_waiting_on(
            &pool,
            WaitingOnCreate {
                description: "Passport office reply".to_string(),
                person: Some("Case officer".to_string()),
                project_id: None,
                last_followup: None,
            },
        )
        .await
        .expect("waiting item");

        let active = global_search(&pool, "passport", false)
            .await
            .expect("active search");
        assert!(active
            .items
            .iter()
            .any(|item| item.kind == SearchResultKind::Task && item.title == "Renew passport"));
        assert!(active
            .items
            .iter()
            .any(|item| item.kind == SearchResultKind::Waiting));
        assert!(!active.items.iter().any(|item| item.recycled));

        let with_recycle = global_search(&pool, "passport", true)
            .await
            .expect("recycle search");
        assert!(with_recycle.items.iter().any(|item| {
            item.kind == SearchResultKind::RecycleBin && item.title == "Passport duplicate"
        }));
    }
}
