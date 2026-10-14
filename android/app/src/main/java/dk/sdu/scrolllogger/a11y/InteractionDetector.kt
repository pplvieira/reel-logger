package dk.sdu.scrolllogger.a11y

/**
 * Maps click announcements on Instagram controls to semantic interaction kinds.
 * Prefers labeled buttons (heart / comment / share) over double-tap.
 */
class InteractionDetector(
    private val debounceMs: Long = 600L,
) {
    private var lastKind: String? = null
    private var lastAt = 0L

    fun onClick(node: NodeSnapshot, nowMs: Long = System.currentTimeMillis()): SemanticEvent? {
        val hay = listOfNotNull(node.text, node.contentDescription, node.viewId)
            .joinToString(" ")
            .lowercase()

        val kind = when {
            hay.contains("unlike") || (hay.contains("liked") && hay.contains("button")) -> "unlike"
            hay.contains("like") && !hay.contains("likely") -> "like"
            hay.contains("comment") && (hay.contains("send") || hay.contains("post")) -> "comment_send"
            hay.contains("comment") -> "comment_open"
            hay.contains("send") && !hay.contains("sender") -> "send"
            hay.contains("share") -> "share_open"
            hay.contains("save") || hay.contains("bookmark") -> "save"
            hay.contains("profile") || hay.contains("user avatar") -> "profile_open"
            else -> null
        } ?: return null

        if (kind == lastKind && nowMs - lastAt < debounceMs) {
            return null
        }
        lastKind = kind
        lastAt = nowMs

        return SemanticEvent(
            type = "interaction",
            payload = mapOf("kind" to kind),
            observedAtMs = nowMs,
        )
    }
}
