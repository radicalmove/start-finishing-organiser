const API_TOKEN_SERVICE: &str = "com.rcd58.sfo";
const API_TOKEN_ACCOUNT: &str = "rust-api-token";
const ERR_SEC_ITEM_NOT_FOUND: i32 = -25300;

#[cfg(any(target_os = "macos", target_os = "ios"))]
pub fn get_api_token() -> Result<Option<String>, String> {
    match security_framework::passwords::get_generic_password(API_TOKEN_SERVICE, API_TOKEN_ACCOUNT)
    {
        Ok(bytes) => token_from_bytes(bytes).map(Some),
        Err(err) if err.code() == ERR_SEC_ITEM_NOT_FOUND => Ok(None),
        Err(err) => Err(format!("Apple Keychain read failed: {err}")),
    }
}

#[cfg(any(target_os = "macos", target_os = "ios"))]
pub fn set_api_token(token: &str) -> Result<(), String> {
    let trimmed = token.trim();
    if trimmed.is_empty() {
        return clear_api_token();
    }

    security_framework::passwords::set_generic_password(
        API_TOKEN_SERVICE,
        API_TOKEN_ACCOUNT,
        trimmed.as_bytes(),
    )
    .map_err(|err| format!("Apple Keychain write failed: {err}"))
}

#[cfg(any(target_os = "macos", target_os = "ios"))]
pub fn clear_api_token() -> Result<(), String> {
    match security_framework::passwords::delete_generic_password(
        API_TOKEN_SERVICE,
        API_TOKEN_ACCOUNT,
    ) {
        Ok(()) => Ok(()),
        Err(err) if err.code() == ERR_SEC_ITEM_NOT_FOUND => Ok(()),
        Err(err) => Err(format!("Apple Keychain delete failed: {err}")),
    }
}

#[cfg(not(any(target_os = "macos", target_os = "ios")))]
pub fn get_api_token() -> Result<Option<String>, String> {
    Err("Apple Keychain token storage is only available on macOS and iOS.".to_string())
}

#[cfg(not(any(target_os = "macos", target_os = "ios")))]
pub fn set_api_token(_token: &str) -> Result<(), String> {
    Err("Apple Keychain token storage is only available on macOS and iOS.".to_string())
}

#[cfg(not(any(target_os = "macos", target_os = "ios")))]
pub fn clear_api_token() -> Result<(), String> {
    Err("Apple Keychain token storage is only available on macOS and iOS.".to_string())
}

fn token_from_bytes(bytes: Vec<u8>) -> Result<String, String> {
    String::from_utf8(bytes).map_err(|_| "Apple Keychain token is not valid UTF-8.".to_string())
}

#[cfg(test)]
mod tests {
    use super::token_from_bytes;

    #[test]
    fn token_bytes_must_be_valid_utf8() {
        assert_eq!(
            token_from_bytes(b" secret-token ".to_vec()).expect("valid token bytes"),
            " secret-token "
        );
        assert!(token_from_bytes(vec![0xff]).is_err());
    }
}
