package dk.sdu.scrolllogger.sync

import dk.sdu.scrolllogger.BuildConfig
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.util.concurrent.TimeUnit

class IngestClient(
    private val baseUrl: String,
    private val apiToken: String,
    private val userId: String,
    private val deviceId: String,
) {
    private val client = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .build()

    fun postEvents(events: List<JSONObject>): Result<JSONObject> {
        if (baseUrl.isBlank() || userId.isBlank() || deviceId.isBlank()) {
            return Result.failure(IllegalStateException("Sync config incomplete"))
        }
        val arr = JSONArray()
        for (e in events) {
            val item = JSONObject()
            item.put("type", e.getString("type"))
            item.put("observed_at", e.getString("observed_at"))
            item.put("payload", e.optJSONObject("payload") ?: JSONObject())
            if (e.has("event_id")) {
                // event_id is also mirrored into payload for older servers; server reads top-level when present
                item.put("event_id", e.getString("event_id"))
            }
            arr.put(item)
        }
        val body = JSONObject()
        body.put("schema_version", "1")
        body.put("device_id", deviceId)
        body.put("user_id", userId)
        body.put("platform", "instagram")
        body.put("capture_method", "accessibility")
        body.put("logger_version", BuildConfig.LOGGER_VERSION)
        body.put("events", arr)

        val reqBuilder = Request.Builder()
            .url("$baseUrl/ingest/events")
            .post(body.toString().toRequestBody(JSON_MEDIA))
        if (apiToken.isNotBlank()) {
            reqBuilder.header("Authorization", "Bearer $apiToken")
        }
        return try {
            client.newCall(reqBuilder.build()).execute().use { resp ->
                val text = resp.body?.string().orEmpty()
                if (!resp.isSuccessful) {
                    Result.failure(IllegalStateException("HTTP ${resp.code}: $text"))
                } else {
                    Result.success(JSONObject(text.ifBlank { "{}" }))
                }
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    companion object {
        private val JSON_MEDIA = "application/json; charset=utf-8".toMediaType()
    }
}
