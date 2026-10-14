package dk.sdu.scrolllogger.sync

import android.content.Context

class Prefs(context: Context) {
    private val sp = context.getSharedPreferences("scroll_logger", Context.MODE_PRIVATE)

    var loggingEnabled: Boolean
        get() = sp.getBoolean(KEY_LOGGING, false)
        set(value) = sp.edit().putBoolean(KEY_LOGGING, value).apply()

    var debugRawA11y: Boolean
        get() = sp.getBoolean(KEY_DEBUG_A11Y, false)
        set(value) = sp.edit().putBoolean(KEY_DEBUG_A11Y, value).apply()

    var baseUrl: String
        get() = sp.getString(KEY_BASE_URL, "") ?: ""
        set(value) = sp.edit().putString(KEY_BASE_URL, value.trim().trimEnd('/')).apply()

    var userId: String
        get() = sp.getString(KEY_USER_ID, "") ?: ""
        set(value) = sp.edit().putString(KEY_USER_ID, value.trim()).apply()

    var deviceId: String
        get() = sp.getString(KEY_DEVICE_ID, "") ?: ""
        set(value) = sp.edit().putString(KEY_DEVICE_ID, value.trim()).apply()

    var apiToken: String
        get() = sp.getString(KEY_API_TOKEN, "") ?: ""
        set(value) = sp.edit().putString(KEY_API_TOKEN, value.trim()).apply()

    companion object {
        private const val KEY_LOGGING = "logging_enabled"
        private const val KEY_DEBUG_A11Y = "debug_raw_a11y"
        private const val KEY_BASE_URL = "base_url"
        private const val KEY_USER_ID = "user_id"
        private const val KEY_DEVICE_ID = "device_id"
        private const val KEY_API_TOKEN = "api_token"
    }
}
