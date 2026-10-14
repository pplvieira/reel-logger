package dk.sdu.scrolllogger.a11y

/**
 * Detects Reels / For You surface and reel changes from node snapshots.
 *
 * Confidence rubric (see docs/android-detector.md):
 * - 0.3: scroll/window change only, weak identity
 * - 0.7: creator or caption found
 * - 0.9: creator and caption both found on a Reels-like surface
 */
class ReelDetector(
    private val minReelIntervalMs: Long = 400L,
) {
    private var sessionOpen = false
    private var reelOpen = false
    private var lastCreator: String? = null
    private var lastCaption: String? = null
    private var lastReelAt = 0L
    private var inReelsSurface = false

    fun onPackageLost(nowMs: Long = System.currentTimeMillis()): List<SemanticEvent> {
        val out = mutableListOf<SemanticEvent>()
        if (reelOpen) {
            out += SemanticEvent("reel_hidden", observedAtMs = nowMs)
            reelOpen = false
        }
        if (sessionOpen) {
            out += SemanticEvent(
                "session_end",
                payload = mapOf("end_reason" to "leave"),
                observedAtMs = nowMs,
            )
            sessionOpen = false
        }
        inReelsSurface = false
        lastCreator = null
        lastCaption = null
        return out
    }

    fun onScreenOff(nowMs: Long = System.currentTimeMillis()): List<SemanticEvent> {
        val out = mutableListOf<SemanticEvent>()
        if (reelOpen) {
            out += SemanticEvent("reel_hidden", observedAtMs = nowMs)
            reelOpen = false
        }
        if (sessionOpen) {
            out += SemanticEvent(
                "session_end",
                payload = mapOf("end_reason" to "screen_off"),
                observedAtMs = nowMs,
            )
            sessionOpen = false
        }
        return out
    }

    fun onTree(
        root: NodeSnapshot,
        eventKind: String,
        nowMs: Long = System.currentTimeMillis(),
    ): List<SemanticEvent> {
        val out = mutableListOf<SemanticEvent>()
        val texts = root.allTexts()
        val surface = detectReelsSurface(texts, root)
        val creator = extractCreator(texts)
        val caption = extractCaption(texts, creator)

        if (surface && !inReelsSurface) {
            inReelsSurface = true
            if (!sessionOpen) {
                sessionOpen = true
                out += SemanticEvent(
                    "session_start",
                    payload = mapOf("surface" to "for_you"),
                    observedAtMs = nowMs,
                )
            }
        }

        if (!surface && inReelsSurface && eventKind == "window") {
            // Left reels tab / surface
            inReelsSurface = false
            if (reelOpen) {
                out += SemanticEvent("reel_hidden", observedAtMs = nowMs)
                reelOpen = false
            }
            if (sessionOpen) {
                out += SemanticEvent(
                    "session_end",
                    payload = mapOf("end_reason" to "leave"),
                    observedAtMs = nowMs,
                )
                sessionOpen = false
            }
            lastCreator = null
            lastCaption = null
            return out
        }

        if (!sessionOpen && surface) {
            sessionOpen = true
            out += SemanticEvent(
                "session_start",
                payload = mapOf("surface" to "for_you"),
                observedAtMs = nowMs,
            )
        }

        val identityChanged =
            (creator != null && creator != lastCreator) ||
                (caption != null && caption != lastCaption && creator == lastCreator && creator != null)

        val scrollBoundary = eventKind == "scroll" || eventKind == "window"
        val shouldNewReel =
            sessionOpen &&
                surface &&
                (identityChanged || (scrollBoundary && (creator != null || caption != null))) &&
                (nowMs - lastReelAt >= minReelIntervalMs) &&
                (creator != lastCreator || caption != lastCaption || !reelOpen)

        if (shouldNewReel) {
            if (reelOpen) {
                out += SemanticEvent("reel_hidden", observedAtMs = nowMs)
            }
            val confidence = confidence(creator, caption, surface)
            out += SemanticEvent(
                "reel_shown",
                payload = mapOf(
                    "creator_handle" to creator,
                    "caption_excerpt" to caption?.take(240),
                    "confidence" to confidence,
                ),
                observedAtMs = nowMs,
            )
            reelOpen = true
            lastCreator = creator
            lastCaption = caption
            lastReelAt = nowMs
        }

        return out
    }

    companion object {
        fun detectReelsSurface(texts: List<String>, root: NodeSnapshot): Boolean {
            val joined = texts.joinToString(" ").lowercase()
            if (joined.contains("reels") || joined.contains("for you") || joined.contains("para ti")) {
                return true
            }
            // Like / comment / share cluster is a weak Reels chrome signal
            val hasLike = root.findByDescContains("like") != null
            val hasComment = root.findByDescContains("comment") != null
            val hasShare = root.findByDescContains("share", "send") != null
            return hasLike && hasComment && hasShare
        }

        fun extractCreator(texts: List<String>): String? {
            for (t in texts) {
                val s = t.trim()
                if (s.startsWith("@") && s.length in 2..64 && !s.contains(' ')) {
                    return s.removePrefix("@")
                }
            }
            // Instagram often shows username without @ near the bottom chrome
            for (t in texts) {
                val s = t.trim()
                if (s.matches(Regex("^[A-Za-z0-9._]{2,30}$")) &&
                    s !in setOf("Reels", "For", "You", "Like", "Comment", "Share", "Send", "Audio")
                ) {
                    // Prefer strings that look like handles (contain _ or .)
                    if (s.contains('_') || s.contains('.')) return s
                }
            }
            return null
        }

        fun extractCaption(texts: List<String>, creator: String?): String? {
            val candidates = texts.filter { t ->
                val s = t.trim()
                s.length >= 8 &&
                    s.length <= 400 &&
                    !s.equals(creator, ignoreCase = true) &&
                    !s.startsWith("http") &&
                    !s.equals("Like", true) &&
                    !s.equals("Comment", true) &&
                    !s.equals("Share", true) &&
                    !s.equals("Reels", true)
            }
            return candidates.maxByOrNull { it.length }
        }

        fun confidence(creator: String?, caption: String?, surface: Boolean): Double {
            if (!surface) return 0.3
            return when {
                creator != null && caption != null -> 0.9
                creator != null || caption != null -> 0.7
                else -> 0.3
            }
        }
    }
}
