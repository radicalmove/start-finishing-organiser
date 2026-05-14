use serde::{Deserialize, Serialize};

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum SearchResultKind {
    Project,
    Task,
    Waiting,
    RecycleBin,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct SearchResult {
    pub id: String,
    pub kind: SearchResultKind,
    pub title: String,
    #[serde(default)]
    pub description: Option<String>,
    pub location: String,
    #[serde(default)]
    pub recycled: bool,
    #[serde(default)]
    pub created_at: Option<String>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct GlobalSearchResults {
    pub query: String,
    pub include_recycle_bin: bool,
    pub items: Vec<SearchResult>,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn global_search_results_serialize_kind_and_recycle_flag() {
        let results = GlobalSearchResults {
            query: "passport".to_string(),
            include_recycle_bin: true,
            items: vec![SearchResult {
                id: "task-1".to_string(),
                kind: SearchResultKind::RecycleBin,
                title: "Passport duplicate".to_string(),
                description: None,
                location: "Recycle Bin".to_string(),
                recycled: true,
                created_at: None,
            }],
        };

        let json = serde_json::to_value(results).expect("serialize search results");

        assert_eq!(json["query"], "passport");
        assert_eq!(json["include_recycle_bin"], true);
        assert_eq!(json["items"][0]["kind"], "recycle_bin");
        assert_eq!(json["items"][0]["recycled"], true);
    }
}
