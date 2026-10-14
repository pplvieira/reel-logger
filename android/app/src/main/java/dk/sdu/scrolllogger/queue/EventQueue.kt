package dk.sdu.scrolllogger.queue

import org.json.JSONObject
import java.io.File
import java.util.UUID
import java.util.concurrent.locks.ReentrantLock
import kotlin.concurrent.withLock

/**
 * Append-only JSONL queue. Each line is one semantic event with event_id.
 * Synced / exported offsets are tracked in a sidecar so clears are safe.
 */
class EventQueue(private val dir: File) {
    private val lock = ReentrantLock()
    private val queueFile = File(dir, "events.jsonl")
    private val metaFile = File(dir, "queue.meta.json")

    init {
        dir.mkdirs()
        if (!queueFile.exists()) queueFile.writeText("")
        if (!metaFile.exists()) writeMeta(0, 0)
    }

    fun path(): File = queueFile

    fun append(type: String, payload: Map<String, Any?> = emptyMap(), observedAtMs: Long = System.currentTimeMillis()) {
        val event = JSONObject()
        event.put("event_id", UUID.randomUUID().toString())
        event.put("type", type)
        event.put("observed_at", isoUtc(observedAtMs))
        event.put("payload", JSONObject(payload.filterValues { it != null }))
        lock.withLock {
            queueFile.appendText(event.toString() + "\n")
        }
    }

    fun lineCount(): Int = lock.withLock {
        if (!queueFile.exists() || queueFile.length() == 0L) 0
        else queueFile.bufferedReader().useLines { it.count() }
    }

    fun unreadEvents(limit: Int = 200): List<JSONObject> = lock.withLock {
        val (_, synced) = readMeta()
        val out = mutableListOf<JSONObject>()
        var index = 0
        queueFile.bufferedReader().useLines { lines ->
            for (line in lines) {
                if (index >= synced && line.isNotBlank()) {
                    out.add(JSONObject(line))
                    if (out.size >= limit) break
                }
                index++
            }
        }
        out
    }

    fun markSynced(count: Int) = lock.withLock {
        val (exported, synced) = readMeta()
        writeMeta(exported, synced + count)
    }

    fun markExported() = lock.withLock {
        val total = lineCountUnlocked()
        val (_, synced) = readMeta()
        writeMeta(total, synced)
    }

    /** Drop lines that have been both exported and synced (min of the two offsets). */
    fun clearAcknowledged() = lock.withLock {
        val (exported, synced) = readMeta()
        val cut = minOf(exported, synced)
        if (cut <= 0) return@withLock
        val remaining = mutableListOf<String>()
        var index = 0
        queueFile.bufferedReader().useLines { lines ->
            for (line in lines) {
                if (index >= cut) remaining.add(line)
                index++
            }
        }
        queueFile.writeText(remaining.joinToString("\n").let { if (it.isEmpty()) "" else "$it\n" })
        writeMeta(0, 0)
    }

    private fun lineCountUnlocked(): Int {
        if (!queueFile.exists() || queueFile.length() == 0L) return 0
        return queueFile.bufferedReader().useLines { it.count() }
    }

    private fun readMeta(): Pair<Int, Int> {
        val obj = JSONObject(metaFile.readText())
        return obj.optInt("exported", 0) to obj.optInt("synced", 0)
    }

    private fun writeMeta(exported: Int, synced: Int) {
        metaFile.writeText(JSONObject(mapOf("exported" to exported, "synced" to synced)).toString())
    }

    companion object {
        fun isoUtc(ms: Long): String {
            val sdf = java.text.SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSS'Z'", java.util.Locale.US)
            sdf.timeZone = java.util.TimeZone.getTimeZone("UTC")
            return sdf.format(java.util.Date(ms))
        }
    }
}
