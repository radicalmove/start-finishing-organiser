use chrono::{DateTime, Utc};
use sfo_core::{
    PluginCapability, PluginCapabilityId, PluginCapabilityKind, PluginDetail, PluginId,
    PluginStatus, PluginSuggestion, PluginSuggestionCreate, PluginSuggestionId,
    PluginSuggestionStatus, PluginTrustLevel, PluginUpdate,
};
use sqlx::FromRow;
use std::str::FromStr;

use crate::DbError;

const BUILTIN_PLUGIN_VERSION: &str = "0.1.0";

pub async fn seed_builtin_plugins(pool: &sqlx::SqlitePool) -> Result<(), DbError> {
    seed_plugin(
        pool,
        BuiltinPlugin {
            id: "health",
            name: "Health",
            description: "Exercise, diet, training, supplements, metrics, and goals.",
            capabilities: &[
                PluginCapabilityKind::ReadSfoContext,
                PluginCapabilityKind::CreateSuggestions,
                PluginCapabilityKind::HealthRead,
                PluginCapabilityKind::HealthWrite,
            ],
        },
    )
    .await?;
    seed_plugin(
        pool,
        BuiltinPlugin {
            id: "communications",
            name: "Communications",
            description: "Outlook and Teams draft responses and follow-up suggestions.",
            capabilities: &[
                PluginCapabilityKind::ReadSfoContext,
                PluginCapabilityKind::CreateSuggestions,
                PluginCapabilityKind::CreateTasks,
                PluginCapabilityKind::CreateWaitingItems,
                PluginCapabilityKind::CommunicationsReadMetadata,
                PluginCapabilityKind::CommunicationsReadContent,
                PluginCapabilityKind::CommunicationsCreateDrafts,
                PluginCapabilityKind::CalendarRead,
                PluginCapabilityKind::CalendarSuggestBlocks,
            ],
        },
    )
    .await
}

pub async fn list_plugins(pool: &sqlx::SqlitePool) -> Result<Vec<PluginDetail>, DbError> {
    let rows = sqlx::query_as::<_, PluginRow>(
        r#"
        SELECT * FROM plugins
        ORDER BY name COLLATE NOCASE ASC
        "#,
    )
    .fetch_all(pool)
    .await?;

    let mut plugins = Vec::with_capacity(rows.len());
    for row in rows {
        plugins.push(plugin_from_row(pool, row).await?);
    }
    Ok(plugins)
}

pub async fn get_plugin(
    pool: &sqlx::SqlitePool,
    plugin_id: &PluginId,
) -> Result<Option<PluginDetail>, DbError> {
    let row = sqlx::query_as::<_, PluginRow>("SELECT * FROM plugins WHERE id = ?")
        .bind(plugin_id.as_str())
        .fetch_optional(pool)
        .await?;

    match row {
        Some(row) => Ok(Some(plugin_from_row(pool, row).await?)),
        None => Ok(None),
    }
}

pub async fn update_plugin(
    pool: &sqlx::SqlitePool,
    plugin_id: &PluginId,
    payload: PluginUpdate,
) -> Result<PluginDetail, DbError> {
    let current = get_plugin(pool, plugin_id)
        .await?
        .ok_or_else(|| DbError::InvalidData("plugin not found".to_string()))?;
    let enabled = payload.enabled.unwrap_or(current.enabled);
    let status = payload.status.unwrap_or(if enabled {
        PluginStatus::Ready
    } else {
        PluginStatus::Disabled
    });
    let status_detail = payload.status_detail.or(current.status_detail);

    sqlx::query(
        r#"
        UPDATE plugins
        SET enabled = ?, status = ?, status_detail = ?, updated_at = ?
        WHERE id = ?
        "#,
    )
    .bind(bool_to_i64(enabled))
    .bind(status.as_str())
    .bind(status_detail)
    .bind(now_text())
    .bind(plugin_id.as_str())
    .execute(pool)
    .await?;

    get_plugin(pool, plugin_id)
        .await?
        .ok_or_else(|| DbError::InvalidData("updated plugin could not be loaded".to_string()))
}

pub async fn set_capability_enabled(
    pool: &sqlx::SqlitePool,
    plugin_id: &PluginId,
    capability: PluginCapabilityKind,
    enabled: bool,
) -> Result<(), DbError> {
    sqlx::query(
        r#"
        UPDATE plugin_capabilities
        SET enabled = ?, updated_at = ?
        WHERE plugin_id = ? AND capability = ?
        "#,
    )
    .bind(bool_to_i64(enabled))
    .bind(now_text())
    .bind(plugin_id.as_str())
    .bind(capability.as_str())
    .execute(pool)
    .await?;

    Ok(())
}

pub async fn create_suggestion(
    pool: &sqlx::SqlitePool,
    payload: PluginSuggestionCreate,
) -> Result<PluginSuggestion, DbError> {
    let id = PluginSuggestionId::new(format!(
        "suggestion-{}",
        Utc::now().timestamp_nanos_opt().unwrap_or_default()
    ));
    sqlx::query(
        r#"
        INSERT INTO plugin_suggestions (
          id, plugin_id, kind, title, summary, detail, payload_json, source_label,
          source_uri, confidence, priority, status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        "#,
    )
    .bind(id.as_str())
    .bind(payload.plugin_id.as_str())
    .bind(payload.kind.as_str())
    .bind(payload.title)
    .bind(payload.summary)
    .bind(payload.detail)
    .bind(if payload.payload_json.trim().is_empty() {
        "{}".to_string()
    } else {
        payload.payload_json
    })
    .bind(payload.source_label)
    .bind(payload.source_uri)
    .bind(payload.confidence)
    .bind(payload.priority.as_str())
    .bind(PluginSuggestionStatus::Pending.as_str())
    .execute(pool)
    .await?;

    get_suggestion(pool, &id).await?.ok_or_else(|| {
        DbError::InvalidData("created plugin suggestion could not be loaded".to_string())
    })
}

pub async fn list_suggestions(
    pool: &sqlx::SqlitePool,
    statuses: &[PluginSuggestionStatus],
) -> Result<Vec<PluginSuggestion>, DbError> {
    if statuses.is_empty() {
        return suggestion_rows(
            pool,
            r#"
            SELECT * FROM plugin_suggestions
            ORDER BY created_at DESC
            "#,
            &[],
        )
        .await;
    }

    let placeholders = vec!["?"; statuses.len()].join(", ");
    let sql = format!(
        r#"
        SELECT * FROM plugin_suggestions
        WHERE status IN ({placeholders})
        ORDER BY created_at DESC
        "#
    );
    let status_values = statuses
        .iter()
        .map(|status| status.as_str().to_string())
        .collect::<Vec<_>>();
    suggestion_rows(pool, &sql, &status_values).await
}

pub async fn get_suggestion(
    pool: &sqlx::SqlitePool,
    suggestion_id: &PluginSuggestionId,
) -> Result<Option<PluginSuggestion>, DbError> {
    let row =
        sqlx::query_as::<_, PluginSuggestionRow>("SELECT * FROM plugin_suggestions WHERE id = ?")
            .bind(suggestion_id.as_str())
            .fetch_optional(pool)
            .await?;

    row.map(PluginSuggestion::try_from).transpose()
}

pub async fn mark_suggestion_approved(
    pool: &sqlx::SqlitePool,
    suggestion_id: &PluginSuggestionId,
    created_core_kind: Option<&str>,
    created_core_id: Option<&str>,
) -> Result<PluginSuggestion, DbError> {
    update_suggestion_resolution(
        pool,
        suggestion_id,
        PluginSuggestionStatus::Approved,
        None,
        created_core_kind,
        created_core_id,
    )
    .await
}

pub async fn mark_suggestion_dismissed(
    pool: &sqlx::SqlitePool,
    suggestion_id: &PluginSuggestionId,
) -> Result<PluginSuggestion, DbError> {
    update_suggestion_resolution(
        pool,
        suggestion_id,
        PluginSuggestionStatus::Dismissed,
        None,
        None,
        None,
    )
    .await
}

pub async fn mark_suggestion_failed(
    pool: &sqlx::SqlitePool,
    suggestion_id: &PluginSuggestionId,
    detail: &str,
) -> Result<PluginSuggestion, DbError> {
    update_suggestion_resolution(
        pool,
        suggestion_id,
        PluginSuggestionStatus::Failed,
        Some(detail),
        None,
        None,
    )
    .await
}

struct BuiltinPlugin {
    id: &'static str,
    name: &'static str,
    description: &'static str,
    capabilities: &'static [PluginCapabilityKind],
}

async fn seed_plugin(pool: &sqlx::SqlitePool, plugin: BuiltinPlugin) -> Result<(), DbError> {
    let now = now_text();
    sqlx::query(
        r#"
        INSERT INTO plugins (
          id, name, description, version, enabled, trust_level, status, status_detail,
          created_at, updated_at
        )
        VALUES (?, ?, ?, ?, 0, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
          name = excluded.name,
          description = excluded.description,
          version = excluded.version,
          updated_at = excluded.updated_at
        "#,
    )
    .bind(plugin.id)
    .bind(plugin.name)
    .bind(plugin.description)
    .bind(BUILTIN_PLUGIN_VERSION)
    .bind(PluginTrustLevel::FirstParty.as_str())
    .bind(PluginStatus::Disabled.as_str())
    .bind("Disabled until configured.")
    .bind(&now)
    .bind(&now)
    .execute(pool)
    .await?;

    for capability in plugin.capabilities {
        let id = format!("{}:{}", plugin.id, capability.as_str());
        sqlx::query(
            r#"
            INSERT INTO plugin_capabilities (
              id, plugin_id, capability, enabled, created_at, updated_at
            )
            VALUES (?, ?, ?, 0, ?, ?)
            ON CONFLICT(plugin_id, capability) DO UPDATE SET
              updated_at = excluded.updated_at
            "#,
        )
        .bind(id)
        .bind(plugin.id)
        .bind(capability.as_str())
        .bind(&now)
        .bind(&now)
        .execute(pool)
        .await?;
    }

    Ok(())
}

async fn plugin_from_row(pool: &sqlx::SqlitePool, row: PluginRow) -> Result<PluginDetail, DbError> {
    let capabilities = capabilities_for_plugin(pool, &row.id).await?;
    Ok(PluginDetail {
        id: PluginId::from(row.id),
        name: row.name,
        description: row.description,
        version: row.version,
        enabled: i64_to_bool(row.enabled),
        trust_level: parse_enum(&row.trust_level)?,
        status: parse_enum(&row.status)?,
        status_detail: row.status_detail,
        capabilities,
    })
}

async fn capabilities_for_plugin(
    pool: &sqlx::SqlitePool,
    plugin_id: &str,
) -> Result<Vec<PluginCapability>, DbError> {
    let rows = sqlx::query_as::<_, PluginCapabilityRow>(
        r#"
        SELECT * FROM plugin_capabilities
        WHERE plugin_id = ?
        ORDER BY capability ASC
        "#,
    )
    .bind(plugin_id)
    .fetch_all(pool)
    .await?;

    rows.into_iter().map(PluginCapability::try_from).collect()
}

async fn suggestion_rows(
    pool: &sqlx::SqlitePool,
    sql: &str,
    statuses: &[String],
) -> Result<Vec<PluginSuggestion>, DbError> {
    let mut query = sqlx::query_as::<_, PluginSuggestionRow>(sql);
    for status in statuses {
        query = query.bind(status);
    }
    let rows = query.fetch_all(pool).await?;
    rows.into_iter().map(PluginSuggestion::try_from).collect()
}

async fn update_suggestion_resolution(
    pool: &sqlx::SqlitePool,
    suggestion_id: &PluginSuggestionId,
    status: PluginSuggestionStatus,
    detail: Option<&str>,
    created_core_kind: Option<&str>,
    created_core_id: Option<&str>,
) -> Result<PluginSuggestion, DbError> {
    let now = now_text();
    sqlx::query(
        r#"
        UPDATE plugin_suggestions
        SET status = ?, detail = COALESCE(?, detail), created_core_kind = ?,
            created_core_id = ?, updated_at = ?, resolved_at = ?
        WHERE id = ?
        "#,
    )
    .bind(status.as_str())
    .bind(detail)
    .bind(created_core_kind)
    .bind(created_core_id)
    .bind(&now)
    .bind(&now)
    .bind(suggestion_id.as_str())
    .execute(pool)
    .await?;

    get_suggestion(pool, suggestion_id)
        .await?
        .ok_or_else(|| DbError::InvalidData("plugin suggestion could not be loaded".to_string()))
}

#[derive(Debug, FromRow)]
struct PluginRow {
    id: String,
    name: String,
    description: Option<String>,
    version: String,
    enabled: i64,
    trust_level: String,
    status: String,
    status_detail: Option<String>,
}

#[derive(Debug, FromRow)]
struct PluginCapabilityRow {
    id: String,
    plugin_id: String,
    capability: String,
    enabled: i64,
}

impl TryFrom<PluginCapabilityRow> for PluginCapability {
    type Error = DbError;

    fn try_from(row: PluginCapabilityRow) -> Result<Self, Self::Error> {
        Ok(Self {
            id: PluginCapabilityId::from(row.id),
            plugin_id: PluginId::from(row.plugin_id),
            capability: parse_enum(&row.capability)?,
            enabled: i64_to_bool(row.enabled),
        })
    }
}

#[derive(Debug, FromRow)]
struct PluginSuggestionRow {
    id: String,
    plugin_id: String,
    kind: String,
    title: String,
    summary: Option<String>,
    detail: Option<String>,
    payload_json: String,
    source_label: Option<String>,
    source_uri: Option<String>,
    confidence: Option<f64>,
    priority: String,
    status: String,
    created_core_kind: Option<String>,
    created_core_id: Option<String>,
    created_at: String,
    updated_at: String,
    resolved_at: Option<String>,
}

impl TryFrom<PluginSuggestionRow> for PluginSuggestion {
    type Error = DbError;

    fn try_from(row: PluginSuggestionRow) -> Result<Self, Self::Error> {
        Ok(Self {
            id: PluginSuggestionId::from(row.id),
            plugin_id: PluginId::from(row.plugin_id),
            kind: parse_enum(&row.kind)?,
            title: row.title,
            summary: row.summary,
            detail: row.detail,
            payload_json: row.payload_json,
            source_label: row.source_label,
            source_uri: row.source_uri,
            confidence: row.confidence,
            priority: parse_enum(&row.priority)?,
            status: parse_enum(&row.status)?,
            created_core_kind: row.created_core_kind,
            created_core_id: row.created_core_id,
            created_at: parse_datetime(&row.created_at)?,
            updated_at: parse_datetime(&row.updated_at)?,
            resolved_at: parse_optional_datetime(row.resolved_at)?,
        })
    }
}

fn parse_enum<T>(value: &str) -> Result<T, DbError>
where
    T: FromStr,
    T::Err: std::fmt::Display,
{
    value
        .parse::<T>()
        .map_err(|error| DbError::InvalidData(error.to_string()))
}

fn parse_datetime(value: &str) -> Result<DateTime<Utc>, DbError> {
    DateTime::parse_from_rfc3339(value)
        .map(|date_time| date_time.with_timezone(&Utc))
        .map_err(|error| DbError::InvalidData(error.to_string()))
}

fn parse_optional_datetime(value: Option<String>) -> Result<Option<DateTime<Utc>>, DbError> {
    value.as_deref().map(parse_datetime).transpose()
}

fn bool_to_i64(value: bool) -> i64 {
    i64::from(value)
}

fn i64_to_bool(value: i64) -> bool {
    value != 0
}

fn now_text() -> String {
    Utc::now().to_rfc3339()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{connect, run_migrations, DbConfig};
    use sfo_core::{
        PluginCapabilityKind, PluginId, PluginSuggestionCreate, PluginSuggestionKind,
        PluginSuggestionPriority, PluginSuggestionStatus,
    };

    async fn test_pool() -> sqlx::SqlitePool {
        let pool = connect(&DbConfig::new("sqlite::memory:"))
            .await
            .expect("connect");
        run_migrations(&pool).await.expect("migrate");
        pool
    }

    #[tokio::test]
    async fn seed_plugins_registers_disabled_first_party_plugins() {
        let pool = test_pool().await;
        seed_builtin_plugins(&pool).await.expect("seed plugins");

        let plugins = list_plugins(&pool).await.expect("plugins");
        assert!(plugins.iter().any(|plugin| plugin.id.as_str() == "health"));
        assert!(plugins
            .iter()
            .any(|plugin| plugin.id.as_str() == "communications"));
        assert!(plugins.iter().all(|plugin| !plugin.enabled));
    }

    #[tokio::test]
    async fn capability_enablement_persists() {
        let pool = test_pool().await;
        seed_builtin_plugins(&pool).await.expect("seed plugins");

        set_capability_enabled(
            &pool,
            &PluginId::from("health"),
            PluginCapabilityKind::HealthWrite,
            true,
        )
        .await
        .expect("enable capability");

        let health = get_plugin(&pool, &PluginId::from("health"))
            .await
            .expect("load plugin")
            .expect("health plugin");
        let capability = health
            .capabilities
            .iter()
            .find(|capability| capability.capability == PluginCapabilityKind::HealthWrite)
            .expect("health write capability");
        assert!(capability.enabled);
    }

    #[tokio::test]
    async fn suggestion_lifecycle_persists() {
        let pool = test_pool().await;
        seed_builtin_plugins(&pool).await.expect("seed plugins");

        let suggestion = create_suggestion(
            &pool,
            PluginSuggestionCreate {
                plugin_id: PluginId::from("health"),
                kind: PluginSuggestionKind::HealthPrompt,
                title: "Log breakfast".to_string(),
                summary: Some("Diet log is empty today".to_string()),
                detail: None,
                payload_json: "{}".to_string(),
                source_label: Some("Health".to_string()),
                source_uri: None,
                confidence: Some(0.7),
                priority: PluginSuggestionPriority::Normal,
            },
        )
        .await
        .expect("create suggestion");

        assert_eq!(suggestion.status, PluginSuggestionStatus::Pending);

        let pending = list_suggestions(&pool, &[PluginSuggestionStatus::Pending])
            .await
            .expect("pending suggestions");
        assert_eq!(pending.len(), 1);

        mark_suggestion_dismissed(&pool, &suggestion.id)
            .await
            .expect("dismiss suggestion");
        let dismissed = get_suggestion(&pool, &suggestion.id)
            .await
            .expect("load suggestion")
            .expect("suggestion");
        assert_eq!(dismissed.status, PluginSuggestionStatus::Dismissed);
        assert!(dismissed.resolved_at.is_some());
    }
}
