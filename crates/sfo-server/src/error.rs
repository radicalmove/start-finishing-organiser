#[derive(Debug, thiserror::Error)]
pub enum ServerError {
    #[error(transparent)]
    Db(#[from] sfo_db::DbError),
    #[error("server io error: {0}")]
    Io(#[from] std::io::Error),
}
