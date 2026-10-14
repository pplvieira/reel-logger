package dk.sdu.scrolllogger.a11y

/** Pure semantic event produced by detectors (no Android view ids). */
data class SemanticEvent(
    val type: String,
    val payload: Map<String, Any?> = emptyMap(),
    val observedAtMs: Long = System.currentTimeMillis(),
)
