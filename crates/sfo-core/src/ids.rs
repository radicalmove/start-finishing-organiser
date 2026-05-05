use serde::{Deserialize, Serialize};
use uuid::Uuid;

macro_rules! id_type {
    ($name:ident) => {
        #[derive(Clone, Copy, Debug, Eq, PartialEq, Hash, Serialize, Deserialize)]
        #[serde(transparent)]
        pub struct $name(Uuid);

        impl $name {
            #[must_use]
            pub fn new() -> Self {
                Self(Uuid::now_v7())
            }

            #[must_use]
            pub const fn from_uuid(uuid: Uuid) -> Self {
                Self(uuid)
            }

            #[must_use]
            pub const fn as_uuid(self) -> Uuid {
                self.0
            }
        }

        impl Default for $name {
            fn default() -> Self {
                Self::new()
            }
        }
    };
}

id_type!(ProjectId);
id_type!(TaskId);

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn project_ids_serialize_as_uuid_strings() {
        let id = ProjectId::from_uuid(Uuid::nil());
        let json = serde_json::to_string(&id).expect("serialize project id");
        assert_eq!(json, "\"00000000-0000-0000-0000-000000000000\"");
    }

    #[test]
    fn task_ids_round_trip_through_json() {
        let original = TaskId::new();
        let json = serde_json::to_string(&original).expect("serialize task id");
        let decoded: TaskId = serde_json::from_str(&json).expect("deserialize task id");
        assert_eq!(decoded, original);
    }
}
