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
    private var inOverlay = false

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
        inOverlay = false
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
        inOverlay = false
        return out
    }

    fun onTree(
        root: NodeSnapshot,
        eventKind: String,
        nowMs: Long = System.currentTimeMillis(),
    ): List<SemanticEvent> {
        val out = mutableListOf<SemanticEvent>()
        val texts = root.allTexts()
        val overlay = isShareOrSendOverlay(texts)
        val surface = detectReelsSurface(texts, root) && !isNonReelFeed(texts)
        val creator = extractCreator(texts)
        val caption = extractCaption(texts, creator)

        if (overlay) {
            // Share / send sheet: keep session + open reel; do not treat as leave.
            inOverlay = true
            return out
        }
        if (inOverlay && !overlay) {
            inOverlay = false
            // Returning from overlay — do not emit a new reel solely from chrome refresh.
        }

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
            // Left reels tab / surface (not share overlay — handled above)
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

        val meaningfulCreatorChange = creator != null && creator != lastCreator
        val meaningfulCaptionChange =
            caption != null &&
                caption != lastCaption &&
                !isChromeText(caption) &&
                (lastCaption == null || isChromeText(lastCaption) || creator == lastCreator)

        val identityChanged = meaningfulCreatorChange || meaningfulCaptionChange

        val scrollBoundary = eventKind == "scroll" || eventKind == "window"
        val hasContent = creator != null || (caption != null && !isChromeText(caption))
        val shouldNewReel =
            sessionOpen &&
                surface &&
                hasContent &&
                (identityChanged || (scrollBoundary && hasContent && !reelOpen)) &&
                (nowMs - lastReelAt >= minReelIntervalMs) &&
                (creator != lastCreator || caption != lastCaption || !reelOpen)

        // Ignore chrome-only caption churn on an open reel (same creator).
        val chromeChurnOnly =
            reelOpen &&
                creator != null &&
                creator == lastCreator &&
                caption != null &&
                isChromeText(caption) &&
                !meaningfulCreatorChange

        if (shouldNewReel && !chromeChurnOnly) {
            if (reelOpen) {
                out += SemanticEvent("reel_hidden", observedAtMs = nowMs)
            }
            val confidence = confidence(creator, caption, surface)
            out += SemanticEvent(
                "reel_shown",
                payload = buildMap {
                    if (creator != null) put("creator_handle", creator)
                    if (caption != null) put("caption_excerpt", caption.take(240))
                    put("confidence", confidence)
                    if (looksSponsored(caption, texts)) put("is_sponsored", true)
                    if (looksSuggested(caption, texts)) put("is_suggested", true)
                },
                observedAtMs = nowMs,
            )
            reelOpen = true
            // Prefer keeping a prior real caption over replacing with chrome.
            lastCreator = creator
            if (caption != null && !isChromeText(caption)) {
                lastCaption = caption
            } else if (lastCaption == null) {
                lastCaption = caption
            }
            lastReelAt = nowMs
        }

        return out
    }

    companion object {
        private val CHROME_SUBSTRINGS = listOf(
            "send post",
            "double-tap to choose who to send",
            "double-tap to play or pause",
            "double-tap to like",
            "button.",
            "like button",
            "comment button",
            "share button",
            "see translation",
            "original audio",
            "reels audio",
        )

        private val ENGAGEMENT_HANDLE = Regex(
            """^(\d+(\.\d+)?[KkMm]?|\d{5,})$""",
        )

        private val HANDLE_REGEX = Regex("""^[A-Za-z0-9._]{2,30}$""")

        fun isChromeText(text: String?): Boolean {
            if (text == null) return true
            val s = text.trim().lowercase()
            if (s.length < 8) return true
            return CHROME_SUBSTRINGS.any { s.contains(it) }
        }

        fun isShareOrSendOverlay(texts: List<String>): Boolean {
            val joined = texts.joinToString(" ").lowercase()
            return joined.contains("double-tap to choose who to send") ||
                joined.contains("send to") && joined.contains("search") ||
                (joined.contains("share to") && (joined.contains("story") || joined.contains("message")))
        }

        fun isNonReelFeed(texts: List<String>): Boolean {
            val joined = texts.joinToString(" ").lowercase()
            if (joined.contains("'s story") || joined.contains(" stories,")) return true
            if (joined.contains("posted a photo") || joined.contains("posted a reel")) return true
            // Home-feed photo cards often expose "Photo by …"
            if (joined.contains("photo by ") && !joined.contains("reels") && !joined.contains("for you")) {
                return true
            }
            return false
        }

        fun looksSponsored(caption: String?, texts: List<String>): Boolean {
            val joined = ((caption ?: "") + " " + texts.joinToString(" ")).lowercase()
            return joined.contains("sponsored")
        }

        fun looksSuggested(caption: String?, texts: List<String>): Boolean {
            val joined = ((caption ?: "") + " " + texts.joinToString(" ")).lowercase()
            return joined.contains("suggested reel") || joined.contains("suggested post")
        }

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
                    val handle = s.removePrefix("@")
                    if (!ENGAGEMENT_HANDLE.matches(handle)) return handle
                }
            }
            // Prefer handle-like tokens with _ or .
            var weak: String? = null
            for (t in texts) {
                val s = t.trim()
                if (!HANDLE_REGEX.matches(s)) continue
                if (s in setOf("Reels", "For", "You", "Like", "Comment", "Share", "Send", "Audio")) continue
                if (ENGAGEMENT_HANDLE.matches(s)) continue
                if (s.contains('_') || s.contains('.')) return s
                if (weak == null && s.any { it.isLetter() }) weak = s
            }
            return weak
        }

        fun extractCaption(texts: List<String>, creator: String?): String? {
            val candidates = texts.filter { t ->
                val s = t.trim()
                s.length >= 8 &&
                    s.length <= 400 &&
                    !s.equals(creator, ignoreCase = true) &&
                    !s.startsWith("http") &&
                    !isChromeText(s) &&
                    !s.equals("Like", true) &&
                    !s.equals("Comment", true) &&
                    !s.equals("Share", true) &&
                    !s.equals("Reels", true)
            }
            // Prefer longer non-chrome text; demote a11y "Reel by X" labels slightly
            return candidates.maxWithOrNull(
                compareBy<String> { !it.lowercase().startsWith("reel by ") }
                    .thenBy { !it.lowercase().startsWith("suggested reel") }
                    .thenBy { it.length },
            )
        }

        fun confidence(creator: String?, caption: String?, surface: Boolean): Double {
            if (!surface) return 0.3
            val realCaption = caption != null && !isChromeText(caption)
            return when {
                creator != null && realCaption -> 0.9
                creator != null || realCaption -> 0.7
                else -> 0.3
            }
        }
    }
}
